"""Generate scripts/script-index.md from Python docstring tags.

tags: [routing]
routing_hints: [script-discovery, index]
"""

from __future__ import annotations

import ast
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from paths import SCRIPTS_ROOT  # noqa: E402

ROOT = SCRIPTS_ROOT.parent
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
        summary = r["summary"].replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()
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


def _normalize_for_diff(content: str) -> str:
    return re.sub(r"^generated_at_utc:\s*.*$", "", content, flags=re.MULTILINE)


def _write_idempotent(path: Path, new_content: str, dry_run: bool = False) -> tuple[bool, str]:
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if _normalize_for_diff(existing) == _normalize_for_diff(new_content):
            m = re.search(r"^generated_at_utc:\s*(.+)$", existing, re.MULTILINE)
            if m:
                existing_utc = m.group(1).strip()
                preserved = re.sub(
                    r"^generated_at_utc:\s*.*$",
                    f"generated_at_utc: {existing_utc}",
                    new_content,
                    flags=re.MULTILINE,
                )
                if preserved == existing:
                    return False, f"unchanged {path.relative_to(ROOT).as_posix()}"
                new_content = preserved
        action = f"would update {path.relative_to(ROOT).as_posix()}" if dry_run else f"wrote {path.relative_to(ROOT).as_posix()}"
        if not dry_run:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)
        return True, action

    action = f"would create {path.relative_to(ROOT).as_posix()}" if dry_run else f"wrote {path.relative_to(ROOT).as_posix()}"
    if not dry_run:
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
    return True, action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Exit 1 if on-disk files differ from generated content (ignoring generated_at_utc)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation and report differences without writing files")
    args = parser.parse_args(argv)

    content = render_script_index(SCRIPTS_ROOT)

    if args.check:
        if not OUT.is_file():
            print(f"CHECK FAILED: {OUT.relative_to(ROOT).as_posix()} is missing", file=sys.stderr)
            return 1
        existing = OUT.read_text(encoding="utf-8")
        if _normalize_for_diff(existing) != _normalize_for_diff(content):
            print(f"CHECK FAILED: {OUT.relative_to(ROOT).as_posix()} differs from generated content", file=sys.stderr)
            return 1
        print(f"OK: {OUT.relative_to(ROOT).as_posix()} is up to date.")
        return 0

    changed, msg = _write_idempotent(OUT, content, dry_run=args.dry_run)
    print(msg)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
