"""Refresh the local qmd index after indexed Markdown changes (update then embed).

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
    args = parser.parse_args(argv)
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