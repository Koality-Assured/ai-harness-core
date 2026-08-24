"""Generate scripts/script-index.md from Python docstring tags.

tags: [routing]
routing_hints: [script-discovery, index]
"""

from __future__ import annotations

import ast
import datetime as dt
import re
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from paths import SCRIPTS_ROOT  # noqa: E402

OUT = SCRIPTS_ROOT / "script-index.md"

TAG_RE = re.compile(r"tags:\s*\[([^\]]*)\]", re.IGNORECASE)
HINT_RE = re.compile(r"routing_hints:\s*\[([^\]]*)\]", re.IGNORECASE)


def parse_list(blob: str) -> list[str]:
    return [p.strip().strip("'\"") for p in blob.split(",") if p.strip()]


def skip_script(path: Path, scripts_root: Path | None = None) -> bool:
    root = scripts_root if scripts_root is not None else SCRIPTS_ROOT
    rel_parts = path.relative_to(root).parts
    return rel_parts[0] == "_lib" or path.name.startswith("_")


def extract_meta(path: Path, scripts_root: Path | None = None) -> dict:
    root = scripts_root if scripts_root is not None else SCRIPTS_ROOT
    text = path.read_text(encoding="utf-8")
    try:
        mod = ast.parse(text)
        doc = ast.get_docstring(mod) or ""
    except SyntaxError:
        doc = ""

    tags = parse_list(m.group(1)) if (m := TAG_RE.search(doc)) else []
    hints = parse_list(m.group(1)) if (m := HINT_RE.search(doc)) else []
    summary = next(
        (
            ln.strip()
            for ln in doc.splitlines()
            if ln.strip()
            and not ln.strip().lower().startswith("tags:")
            and not ln.strip().lower().startswith("routing_hints:")
        ),
        "",
    )
    rel = path.relative_to(root).as_posix()
    return {
        "file": rel,
        "summary": summary,
        "tags": tags,
        "hints": hints,
    }


def render_script_index(scripts_root: Path, *, now: str | None = None) -> str:
    """Return script-index.md for the Python files under ``scripts_root``."""
    stamp = now or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    if scripts_root.is_dir():
        for path in sorted(scripts_root.rglob("*.py")):
            if skip_script(path, scripts_root):
                continue
            rows.append(extract_meta(path, scripts_root))

    lines = [
        "---",
        "doc_kind: routing_map",
        "canonical_id: script-index",
        "topics: [scripts, routing]",
        f"generated_at_utc: {stamp}",
        "generator: scripts/routing/generate_script_index.py",
        "---",
        "",
        "# Script index",
        "",
        "Generated from Python docstring `tags:` / `routing_hints:`. Do not hand-edit — run `python scripts/routing/generate_script_index.py`.",
        "",
        "| Script | Tags | Hints | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for r in rows:
        tags = ", ".join(f"`{t}`" for t in r["tags"]) or "—"
        hints = ", ".join(r["hints"]) or "—"
        summary = r["summary"].replace("|", "\\|")
        lines.append(f"| [`{r['file']}`](./{r['file']}) | {tags} | {hints} | {summary} |")

    by_tag: dict[str, list[str]] = {}
    for r in rows:
        for t in r["tags"]:
            by_tag.setdefault(t, []).append(r["file"])

    lines.extend(["", "## By tag", ""])
    for tag in sorted(by_tag):
        files = ", ".join(f"`{f}`" for f in by_tag[tag])
        lines.append(f"- **{tag}:** {files}")

    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.write_text(render_script_index(SCRIPTS_ROOT), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
