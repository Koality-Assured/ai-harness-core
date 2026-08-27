"""Validate context budget ceilings and ingestibility rules across repository entry files.

Enforces character and token budget ceilings on root AGENTS.md, routing files,
and nested AGENTS.md deltas to prevent silent token creep and preserve context windows.

tags: [docs, validation, cost-layers]
routing_hints: [context-budget, tokens, agents-md, ingestibility, ceiling]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from tool_output import estimate_tokens  # noqa: E402

# Budget ceilings in characters (chars / 4 ~= tokens)
BUDGET_CEILINGS: dict[str, int] = {
    "AGENTS.md": 14500,           # Root AGENTS.md ceiling (~3,625 tokens)
    "routing/AGENTS.md": 4500,     # Next-step routing index (~1,125 tokens)
    "routing/by-task.md": 10000,   # Intent pattern matrix (~2,500 tokens)
    "routing/area-map.md": 5000,   # Area map (~1,250 tokens)
}

# Maximum allowed size for any nested AGENTS.md file (~1,125 tokens)
NESTED_AGENTS_MAX_CHARS = 4500

EXCLUDE_DIRS = frozenset({"scratch", ".git", "node_modules", ".venv", "venv"})


def check_context_budgets(repo_root: Path) -> tuple[bool, list[dict[str, Any]], list[str]]:
    """Check that repository entry files stay within token and character budget ceilings."""
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    # 1. Check fixed-path budget ceilings
    for rel_path_str, max_chars in BUDGET_CEILINGS.items():
        file_path = repo_root / rel_path_str
        if not file_path.is_file():
            errors.append(f"Missing required context file: {rel_path_str}")
            results.append({
                "file": rel_path_str,
                "exists": False,
                "ok": False,
                "error": "missing",
            })
            continue

        text = file_path.read_text(encoding="utf-8", errors="replace")
        chars = len(text)
        tokens = estimate_tokens(text)
        max_tokens = max_chars // 4
        ok = chars <= max_chars
        if not ok:
            errors.append(
                f"{rel_path_str} exceeded budget: {chars} chars (~{tokens} tokens), "
                f"ceiling is {max_chars} chars (~{max_tokens} tokens)"
            )
        results.append({
            "file": rel_path_str,
            "exists": True,
            "chars": chars,
            "tokens": tokens,
            "max_chars": max_chars,
            "max_tokens": max_tokens,
            "ok": ok,
        })

    # 2. Check all nested AGENTS.md files
    for path in sorted(repo_root.rglob("AGENTS.md")):
        rel_parts = path.relative_to(repo_root).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        rel_str = path.relative_to(repo_root).as_posix()
        if rel_str in BUDGET_CEILINGS:
            continue  # Already checked above

        text = path.read_text(encoding="utf-8", errors="replace")
        chars = len(text)
        tokens = estimate_tokens(text)
        ok = True

        # Check size ceiling for nested delta
        if chars > NESTED_AGENTS_MAX_CHARS:
            errors.append(
                f"Nested {rel_str} exceeded delta budget: {chars} chars (~{tokens} tokens), "
                f"max allowed is {NESTED_AGENTS_MAX_CHARS} chars"
            )
            ok = False

        # Anti-pattern: Copying root header into nested delta
        if "# Repository AGENTS" in text:
            errors.append(f"Nested {rel_str} improperly duplicates root '# Repository AGENTS' header")
            ok = False

        results.append({
            "file": rel_str,
            "chars": chars,
            "tokens": tokens,
            "max_chars": NESTED_AGENTS_MAX_CHARS,
            "ok": ok,
        })

    return len(errors) == 0, results, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root path")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args(argv)

    ok, results, errors = check_context_budgets(args.root)

    if args.json:
        payload = {
            "ok": ok,
            "results": results,
            "errors": errors,
        }
        print(json.dumps(payload, indent=2))
    else:
        if ok:
            print(f"OK: All {len(results)} context files within budget ceilings.")
        else:
            print("ERROR: Context budget violations detected:")
            for err in errors:
                print(f"  - {err}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
