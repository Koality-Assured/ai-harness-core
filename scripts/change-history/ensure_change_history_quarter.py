"""Ensure change-history year/quarter entries file exists.

tags: [change-history]
routing_hints: [provenance, scaffold]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

# Reuse helpers from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from append_change_history import current_quarter, ensure_quarter_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int)
    parser.add_argument("--quarter", type=int, choices=[1, 2, 3, 4])
    args = parser.parse_args(argv)

    year, quarter = current_quarter()
    if args.year:
        year = args.year
    if args.quarter:
        quarter = args.quarter

    path = ensure_quarter_file(year, quarter)
    print(f"ready -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
