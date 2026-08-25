"""Refresh an existing local qmd index after explicit user approval.

tags: [qmd]
routing_hints: [index, embed, session-end, completion-gate]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from qmd_preflight import build_report  # noqa: E402


def resolve_qmd() -> str | None:
    if sys.platform == "win32":
        return shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    return shutil.which("qmd")


def run(qmd: str, args: list[str], *, dry_run: bool) -> None:
    cmd = [qmd, *args]
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True, cwd=ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    parser.add_argument(
        "--approved-by-user",
        action="store_true",
        help="Confirm the human explicitly approved this index mutation",
    )
    parser.add_argument(
        "--allow-detected-hooks",
        action="store_true",
        help="Acknowledge inspected qmd configuration hook directives",
    )
    args = parser.parse_args(argv)
    if not args.dry_run:
        if not args.approved_by_user:
            print(
                "error: qmd refresh mutates an index; use --dry-run or supply --approved-by-user "
                "after qmd_preflight inspection",
                file=sys.stderr,
            )
            return 1
        preflight = build_report(probe_cli=False, inspect_hooks=True, timeout=15)
        if preflight["state"] == "missing":
            print(
                "error: qmd index is missing; do not let refresh initialize it. Use the explicit setup "
                "flow only after user approval.",
                file=sys.stderr,
            )
            return 1
        hooks = preflight["hook_inspection"]["potential_hooks"]
        errors = preflight["hook_inspection"]["inspection_errors"]
        if errors:
            print(
                "error: unable to inspect qmd config for hooks: "
                + ", ".join(errors)
                + ". Preserve existing state and resolve host access before refresh.",
                file=sys.stderr,
            )
            return 1
        if hooks and not args.allow_detected_hooks:
            print(
                "error: potential qmd config hook directives found in "
                + ", ".join(hooks)
                + "; inspect them and pass --allow-detected-hooks only with explicit user approval",
                file=sys.stderr,
            )
            return 1
    qmd = resolve_qmd()
    if qmd is None:
        print(
            "error: `qmd` not found on PATH; install with: npm i -g @tobilu/qmd",
            file=sys.stderr,
        )
        return 1
    try:
        run(qmd, ["update"], dry_run=args.dry_run)
        run(qmd, ["embed"], dry_run=args.dry_run)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
