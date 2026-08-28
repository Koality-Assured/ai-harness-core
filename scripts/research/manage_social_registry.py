"""Manage, score, and validate the community reliability catalog.

tags: [research, communities, socials, registry, maintenance]
routing_hints: [social-registry, manage-communities, rubric-scoring, validate]
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

REQUIRED_FIELDS = [
    "id",
    "platform",
    "slug",
    "name",
    "reliability_score",
    "signal_tier",
    "topics",
    "moderation_standard",
    "receipts_required",
    "astroturfing_risk",
    "url",
    "query_hints",
]

VALID_PLATFORMS = {"reddit", "hacker_news", "github", "stackoverflow", "x", "discourse", "quora", "discord", "matrix"}
VALID_TIERS = {"Tier 0", "Tier 1", "Tier 2", "Tier 3"}
VALID_MODERATION = {"strict", "moderate", "permissive", "unmoderated"}
VALID_RISKS = {"low", "medium", "high"}


def compute_rubric_score(
    technical_depth: int,  # 0-20
    moderation_rigor: int,  # 0-20
    citation_standard: int,  # 0-20
    vendor_resistance: int,  # 0-15
    signal_to_noise: int,  # 0-15
    reproducibility: int,  # 0-10
) -> tuple[int, str]:
    """Calculate total score (0-100) and assigned Signal Tier."""
    total = (
        max(0, min(20, technical_depth))
        + max(0, min(20, moderation_rigor))
        + max(0, min(20, citation_standard))
        + max(0, min(15, vendor_resistance))
        + max(0, min(15, signal_to_noise))
        + max(0, min(10, reproducibility))
    )
    if total >= 85:
        tier = "Tier 0"
    elif total >= 70:
        tier = "Tier 1"
    elif total >= 50:
        tier = "Tier 2"
    else:
        tier = "Tier 3"
    return total, tier


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    """Validate catalog against Schema and Rubric integrity."""
    errors: list[str] = []
    if "communities" not in catalog or not isinstance(catalog["communities"], list):
        return ["Catalog missing 'communities' list."]

    seen_ids = set()
    for idx, c in enumerate(catalog["communities"]):
        cid = c.get("id", f"index_{idx}")
        if cid in seen_ids:
            errors.append(f"Duplicate community ID '{cid}'.")
        seen_ids.add(cid)

        for field in REQUIRED_FIELDS:
            if field not in c:
                errors.append(f"Community '{cid}' missing required field '{field}'.")

        plat = c.get("platform")
        if plat not in VALID_PLATFORMS:
            errors.append(f"Community '{cid}' invalid platform '{plat}'.")

        tier = c.get("signal_tier")
        if tier not in VALID_TIERS:
            errors.append(f"Community '{cid}' invalid signal_tier '{tier}'.")

        score = c.get("reliability_score")
        if not isinstance(score, int) or score < 0 or score > 100:
            errors.append(f"Community '{cid}' score must be integer between 0 and 100.")

        # Check tier alignment with score
        if score is not None and tier is not None:
            expected_tier = "Tier 0" if score >= 85 else "Tier 1" if score >= 70 else "Tier 2" if score >= 50 else "Tier 3"
            if tier != expected_tier:
                errors.append(f"Community '{cid}' score {score} does not match tier '{tier}' (expected '{expected_tier}').")

        mod = c.get("moderation_standard")
        if mod not in VALID_MODERATION:
            errors.append(f"Community '{cid}' invalid moderation_standard '{mod}'.")

        risk = c.get("astroturfing_risk")
        if risk not in VALID_RISKS:
            errors.append(f"Community '{cid}' invalid astroturfing_risk '{risk}'.")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true", help="Validate catalog integrity and tier alignment")
    parser.add_argument("--score", nargs=6, type=int, metavar=("DEPTH", "MOD", "CITE", "VENDOR", "SIGNAL", "REPRO"),
                        help="Calculate score & tier for 6 rubric dimensions: depth(0-20) mod(0-20) cite(0-20) vendor(0-15) signal(0-15) repro(0-10)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")

    args = parser.parse_args(argv)

    if args.score:
        d, m, c, v, s, r = args.score
        score, tier = compute_rubric_score(d, m, c, v, s, r)
        result = {
            "score": score,
            "signal_tier": tier,
            "inputs": {
                "technical_depth": d,
                "moderation_rigor": m,
                "citation_standard": c,
                "vendor_resistance": v,
                "signal_to_noise": s,
                "reproducibility": r,
            },
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Calculated Score: {score}/100 -> Signal Tier: {tier}")
        return 0

    if not CATALOG_PATH.is_file():
        print(f"Error: Catalog file not found at {CATALOG_PATH}", file=sys.stderr)
        return 1

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    errors = validate_catalog(catalog)

    if args.json:
        result = {
            "status": "valid" if not errors else "invalid",
            "total_communities": len(catalog.get("communities", [])),
            "errors": errors,
        }
        print(json.dumps(result, indent=2))
    else:
        if errors:
            print(f"FAILED: Found {len(errors)} validation errors in catalog:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            return 1
        else:
            print(f"OK: Community catalog valid ({len(catalog.get('communities', []))} communities checked).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
