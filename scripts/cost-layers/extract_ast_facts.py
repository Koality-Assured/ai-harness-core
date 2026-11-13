"""Extract structural facts via ast-grep outline/kind JSON (not full files).

tags: [qmd, headroom, ast-grep]
routing_hints: [structural-facts, outline, cost-layers]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from ast_grep import AstGrepError, run_ast_grep  # noqa: E402
from md import agent_paths, skill_paths  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

FACTS_PER_FILE = 40
SKIP_DIR_NAMES = {
    ".git",
    "change-history",
    "scratch",
    "results",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}
PYTHON_SYMBOL_TYPES = {"function", "class"}
JSON_PAIR_KEYS = {"id", "name"}
AGENT_YAML_KEYS = {"schema_version", "agent_id", "name", "model_tier"}
SKILL_YAML_KEYS = {"name", "owner_agent", "rank"}
DOCS_YAML_KEYS = {"canonical_id", "doc_kind"}
ROUTING_YAML_KEYS = {"canonical_id"}
JSON_PAIR_RE = re.compile(r'^"([^"]+)"\s*:\s*(.*)$', re.DOTALL)

AREA_IDS = (
    "scripts",
    "agent-cards",
    "skills-frontmatter",
    "docs-frontmatter",
    "routing-frontmatter",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel_posix(path: Path, root: Path = ROOT) -> str:
    raw = Path(str(path).replace("\\", "/"))
    try:
        resolved = Path(path).resolve()
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return raw.as_posix().lstrip("./")


def skipped_path(path: Path, root: Path = ROOT) -> bool:
    try:
        parts = set(Path(path).resolve().relative_to(root.resolve()).parts)
    except ValueError:
        parts = set(Path(path).parts)
    return bool(parts & SKIP_DIR_NAMES)


def snippet_from_bytes(path: Path, start: int, end: int, max_len: int = 80) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    chunk = data[start : min(end, start + 400)]
    text = chunk.decode("utf-8", errors="replace").splitlines()[0].strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def parse_json_pair(text: str) -> tuple[str, str] | None:
    match = JSON_PAIR_RE.match(text.strip())
    if not match:
        return None
    key, raw_val = match.group(1), match.group(2).strip().rstrip(",")
    if raw_val.startswith("["):
        return None
    if raw_val.startswith("{"):
        return None
    if (raw_val.startswith('"') and raw_val.endswith('"')) or (
        raw_val.startswith("'") and raw_val.endswith("'")
    ):
        try:
            raw_val = json.loads(raw_val.replace("'", '"') if raw_val.startswith("'") else raw_val)
        except json.JSONDecodeError:
            raw_val = raw_val[1:-1]
    if not isinstance(raw_val, str):
        return None
    return key, raw_val


def parse_yaml_pair(text: str) -> tuple[str, str] | None:
    line = text.strip()
    if ":" not in line or "\n" in line:
        return None
    key, _, val = line.partition(":")
    key, val = key.strip().strip("\"'"), val.strip().strip("\"'")
    if not key or not val or val in {">", ">-", "|", "|-", "[", "{"}:
        return None
    return key, val


def extract_frontmatter_raw(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end == -1:
        return None
    return rest[:end]


def _cap(facts: list[dict], limit: int = FACTS_PER_FILE) -> list[dict]:
    by_file: dict[str, list[dict]] = {}
    order: list[str] = []
    for fact in facts:
        key = fact["file"]
        if key not in by_file:
            by_file[key] = []
            order.append(key)
        if len(by_file[key]) < limit:
            by_file[key].append(fact)
    out: list[dict] = []
    for key in order:
        out.extend(by_file[key])
    return out


def extract_scripts(root: Path = ROOT) -> list[dict]:
    target = root / "scripts"
    data = run_ast_grep(
        ["outline", str(target), "-l", "python", "--json=compact"],
        cwd=root,
    )
    facts: list[dict] = []
    if not isinstance(data, list):
        return facts
    for entry in data:
        path = root / str(entry.get("path") or "")
        if skipped_path(path, root) or not path.is_file():
            continue
        rel = rel_posix(path, root)
        for item in entry.get("items") or []:
            if item.get("symbolType") not in PYTHON_SYMBOL_TYPES:
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            rng = (item.get("range") or {}).get("byteOffset") or {}
            start, end = int(rng.get("start") or 0), int(rng.get("end") or 0)
            facts.append(
                {
                    "area": "scripts",
                    "file": rel,
                    "kind": str(item.get("symbolType")),
                    "name": name,
                    "value": None,
                    "snippet": snippet_from_bytes(path, start, end),
                }
            )
    return _cap(facts)


def extract_agent_cards(root: Path = ROOT) -> list[dict]:
    facts: list[dict] = []
    for path in agent_paths(root):
        if skipped_path(path, root):
            continue
        facts.extend(_yaml_pairs_from_markdown(path, root, "agent-cards", AGENT_YAML_KEYS))
    return _cap(facts)


def _yaml_pairs_from_markdown(path: Path, root: Path, area: str, keep_keys: set[str]) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    raw = extract_frontmatter_raw(text)
    if not raw or not raw.strip():
        return []
    data = run_ast_grep(
        ["run", "--stdin", "-l", "yaml", "-k", "block_mapping_pair", "--json=compact"],
        cwd=root,
        stdin=raw,
    )
    facts: list[dict] = []
    if not isinstance(data, list):
        return facts
    rel = rel_posix(path, root)
    for match in data:
        parsed = parse_yaml_pair(str(match.get("text") or ""))
        if not parsed or parsed[0] not in keep_keys:
            continue
        key, value = parsed
        facts.append(
            {
                "area": area,
                "file": rel,
                "kind": "yaml-pair",
                "name": key,
                "value": value,
                "snippet": str(match.get("text") or "")[:80],
            }
        )
    return facts


def extract_skills_frontmatter(root: Path = ROOT) -> list[dict]:
    facts: list[dict] = []
    for path in skill_paths(root):
        if skipped_path(path, root):
            continue
        facts.extend(_yaml_pairs_from_markdown(path, root, "skills-frontmatter", SKILL_YAML_KEYS))
    return _cap(facts)


def extract_docs_frontmatter(root: Path = ROOT) -> list[dict]:
    facts: list[dict] = []
    docs = root / "docs"
    if not docs.is_dir():
        return facts
    for path in sorted(docs.rglob("*.md")):
        if skipped_path(path, root):
            continue
        facts.extend(_yaml_pairs_from_markdown(path, root, "docs-frontmatter", DOCS_YAML_KEYS))
    return _cap(facts)


def extract_routing_frontmatter(root: Path = ROOT) -> list[dict]:
    facts: list[dict] = []
    routing = root / "routing"
    if not routing.is_dir():
        return facts
    for path in sorted(routing.glob("*.md")):
        if skipped_path(path, root):
            continue
        facts.extend(_yaml_pairs_from_markdown(path, root, "routing-frontmatter", ROUTING_YAML_KEYS))
    return _cap(facts)


EXTRACTORS = {
    "scripts": extract_scripts,
    "agent-cards": extract_agent_cards,
    "skills-frontmatter": extract_skills_frontmatter,
    "docs-frontmatter": extract_docs_frontmatter,
    "routing-frontmatter": extract_routing_frontmatter,
}


def extract_areas(root: Path, areas: list[str]) -> list[dict]:
    facts: list[dict] = []
    for area in areas:
        if area not in EXTRACTORS:
            raise SystemExit(
                f"error: unknown area {area!r}; choose from {', '.join(AREA_IDS)}"
            )
        facts.extend(EXTRACTORS[area](root))
    return facts


def counts_for(facts: list[dict], areas: list[str]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for area in areas:
        subset = [f for f in facts if f["area"] == area]
        files = {f["file"] for f in subset}
        counts[area] = {"files": len(files), "facts": len(subset)}
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--areas",
        default=",".join(AREA_IDS),
        help="Comma-separated area ids to extract",
    )
    parser.add_argument("--out", help="Optional JSON output path (under repo or absolute)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print per-area file/fact counts only",
    )
    args = parser.parse_args(argv)

    areas = [a.strip() for a in args.areas.split(",") if a.strip()]
    if not areas:
        print("error: --areas must list at least one area", file=sys.stderr)
        return 2
    try:
        facts = extract_areas(ROOT, areas)
    except AstGrepError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    counts = counts_for(facts, areas)
    payload: dict = {
        "generated_at_utc": utc_now(),
        "areas": areas,
        "counts": counts,
        "facts_per_file_cap": FACTS_PER_FILE,
    }
    if not args.dry_run:
        payload["facts"] = facts

    text = json.dumps(payload, indent=2)
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
