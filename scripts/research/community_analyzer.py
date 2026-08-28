"""Community analyzer utility for querying, scoring, and synthesizing developer communities.

tags: [research, communities, socials, analysis, osint]
routing_hints: [community-analyzer, subreddits, forums, sentiment, troubleshooting, osint]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

CATALOG_PATH = ROOT / "references" / "socials" / "catalogs" / "ranked-communities.json"


def load_communities_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Communities catalog not found at {CATALOG_PATH}")
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def filter_communities(
    communities: list[dict[str, Any]],
    platform: str | None = None,
    topic: str | None = None,
    min_score: int | None = None,
    min_tier: str | None = None,
) -> list[dict[str, Any]]:
    tier_ranks = {"Tier 0": 0, "Tier 1": 1, "Tier 2": 2, "Tier 3": 3}
    filtered = []
    
    target_tier_max = tier_ranks.get(min_tier, 3) if min_tier else 3

    for c in communities:
        if platform and c.get("platform", "").lower() != platform.lower():
            continue
        if topic:
            c_topics = [t.lower() for t in c.get("topics", [])]
            if not any(topic.lower() in t for t in c_topics):
                continue
        if min_score is not None and c.get("reliability_score", 0) < min_score:
            continue
        if min_tier:
            c_tier = c.get("signal_tier", "Tier 3")
            if tier_ranks.get(c_tier, 3) > target_tier_max:
                continue
        filtered.append(c)

    filtered.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
    return filtered


def get_community_by_slug_or_id(communities: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    q = query.strip().lower()
    for c in communities:
        if c.get("id", "").lower() == q or c.get("slug", "").lower() == q or c.get("name", "").lower() == q:
            return c
    return None


def format_communities_table(communities: list[dict[str, Any]], title: str = "Ranked Communities") -> str:
    lines = [
        f"### {title} ({len(communities)})",
        "",
        "| Score | Tier | Platform | Community | Topics | Receipts Req | Risk | Query Hints |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for c in communities:
        score = c.get("reliability_score", 0)
        tier = c.get("signal_tier", "Tier 3")
        plat = c.get("platform", "")
        name_link = f"[{c.get('slug', c.get('name'))}]({c.get('url')})"
        topics = ", ".join(c.get("topics", [])[:3])
        receipts = "Yes" if c.get("receipts_required") else "No"
        risk = c.get("astroturfing_risk", "low")
        hints = ", ".join(c.get("query_hints", [])[:2])
        lines.append(f"| **{score}** | `{tier}` | `{plat}` | {name_link} | {topics} | {receipts} | `{risk}` | {hints} |")
    lines.append("")
    lines.append("*Evaluated per [Community Reliability Rubric](file:///[REPO_ROOT]/references/socials/community-reliability-rubric.md).*")
    return "\n".join(lines)


def format_community_dossier(c: dict[str, Any]) -> str:
    lines = [
        f"# Community Dossier: {c.get('name')} (`{c.get('slug')}`)",
        "",
        f"- **Platform**: `{c.get('platform')}`",
        f"- **Reliability Score**: **{c.get('reliability_score')} / 100** (`{c.get('signal_tier')}`)",
        f"- **URL**: {c.get('url')}",
        f"- **Moderation Standard**: `{c.get('moderation_standard')}`",
        f"- **Receipts / Reproducer Required**: {'Yes' if c.get('receipts_required') else 'No'}",
        f"- **Astroturfing / Shilling Risk**: `{c.get('astroturfing_risk')}`",
        f"- **Covered Topics**: {', '.join(c.get('topics', []))}",
        "",
        "## Recommended Query Patterns",
        "",
    ]
    for hint in c.get("query_hints", []):
        lines.append(f"- `\"{hint}\"`")
    lines.append("")
    lines.append("## Triage & Verification Rules")
    lines.append("")
    if c.get("reliability_score", 0) >= 85:
        lines.append("- High-signal primary source. Technical assertions can be rapidly prototyped or tested.")
    elif c.get("reliability_score", 0) >= 70:
        lines.append("- Practitioner community. Verify reproduction steps against official documentation before implementation.")
    else:
        lines.append("- Filter for technical tags/flairs only. Discard general commentary and hype without code receipts.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        type=str,
        default=None,
        choices=["reddit", "hacker_news", "github", "stackoverflow", "x", "discourse", "quora"],
        help="Filter by platform",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Filter by topic tag (e.g. ai, security, rust, devops, compilers)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Minimum reliability score threshold (0-100)",
    )
    parser.add_argument(
        "--min-tier",
        type=str,
        default=None,
        choices=["Tier 0", "Tier 1", "Tier 2", "Tier 3"],
        help="Minimum signal tier",
    )
    parser.add_argument(
        "--check-reliability",
        type=str,
        default=None,
        help="Lookup detailed dossier for a specific community slug or ID (e.g. r/LocalLLaMA, r/netsec)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate community catalog and test filtering logic",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output",
    )

    args = parser.parse_args(argv)

    catalog = load_communities_catalog()
    all_communities = catalog.get("communities", [])

    if args.check_reliability:
        c = get_community_by_slug_or_id(all_communities, args.check_reliability)
        if not c:
            print(f"Error: Community '{args.check_reliability}' not found in catalog.", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(c, indent=2))
        else:
            print(format_community_dossier(c))
        return 0

    filtered = filter_communities(
        communities=all_communities,
        platform=args.platform,
        topic=args.topic,
        min_score=args.min_score,
        min_tier=args.min_tier,
    )

    if args.json:
        result = {
            "status": "success",
            "total_catalogued": len(all_communities),
            "matched_count": len(filtered),
            "communities": filtered,
        }
        print(json.dumps(result, indent=2))
    else:
        title = f"Community Intelligence Ranking (Filtered: {len(filtered)})"
        print(format_communities_table(filtered, title))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
