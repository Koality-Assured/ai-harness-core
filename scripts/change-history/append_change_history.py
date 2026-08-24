"""Append a change-history entry for the active year/quarter.

tags: [change-history]
routing_hints: [provenance, session-end, completion-gate]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

CH_ROOT = ROOT / "change-history"


def current_quarter(now: dt.date | None = None) -> tuple[int, int]:
    now = now or dt.date.today()
    return now.year, (now.month - 1) // 3 + 1


def entries_path(year: int, quarter: int) -> Path:
    return CH_ROOT / str(year) / f"Q{quarter}" / "entries.md"


def ensure_quarter_file(year: int, quarter: int) -> Path:
    path = entries_path(year, quarter)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            f"# Change history — {year} Q{quarter}\n\n"
            "Entries newest first. Append via "
            "`python scripts/change-history/append_change_history.py` only.\n\n"
            "## Entries\n",
            encoding="utf-8",
        )
    return path


def build_entry(
    *,
    date: str,
    title: str,
    user: str,
    agent: str,
    request: str,
    summary_lines: list[str],
) -> str:
    bullets = "\n".join(f"  - {line.lstrip('- ').strip()}" for line in summary_lines if line.strip())
    return (
        f"### {date} — {title}\n\n"
        f"- **Requesting user:** {user}\n"
        f"- **AI agent:** {agent}\n"
        f"- **User request:** {request}\n"
        f"- **Summary:**\n{bullets}\n"
    )


def insert_newest_first(text: str, entry: str) -> str:
    marker = "## Entries"
    idx = text.find(marker)
    if idx == -1:
        return text.rstrip() + "\n\n## Entries\n\n" + entry + "\n"
    insert_at = idx + len(marker)
    # Skip blank lines after heading
    rest = text[insert_at:]
    m = re.match(r"\n*", rest)
    skip = m.end() if m else 0
    return text[: insert_at + skip] + "\n" + entry + "\n" + rest[skip:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="Short entry title")
    parser.add_argument("--user", required=True, help="Requesting user")
    parser.add_argument("--agent", default="Cursor agent", help="AI agent identity")
    parser.add_argument("--request", required=True, help="Short paraphrase of user request")
    parser.add_argument(
        "--summary",
        action="append",
        default=[],
        help="Summary bullet (repeatable)",
    )
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--year", type=int, help="Override year")
    parser.add_argument("--quarter", type=int, choices=[1, 2, 3, 4], help="Override quarter")
    args = parser.parse_args(argv)

    if not args.summary:
        print("error: provide at least one --summary bullet", file=sys.stderr)
        return 2

    year, quarter = current_quarter()
    if args.year:
        year = args.year
    if args.quarter:
        quarter = args.quarter

    path = ensure_quarter_file(year, quarter)
    entry = build_entry(
        date=args.date,
        title=args.title,
        user=args.user,
        agent=args.agent,
        request=args.request,
        summary_lines=args.summary,
    )
    updated = insert_newest_first(path.read_text(encoding="utf-8"), entry)
    path.write_text(updated, encoding="utf-8")
    print(f"appended entry -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
