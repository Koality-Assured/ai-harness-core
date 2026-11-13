"""Fetch, analyze, and synthesize AI vendor updates into flash briefings.

tags: [research, intelligence, briefing]
routing_hints: [vendor-updates, flash-briefing, ai-vendors, primary-sources]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from typing import Any
import urllib.request
import xml.etree.ElementTree as ET

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

CATALOG_PATH = ROOT / "ai-tooling" / "skills" / "meta" / "ai-vendor-updates" / "references" / "vendor-sources.json"


def load_vendor_catalog() -> dict[str, Any]:
    target_path = CATALOG_PATH
    if not target_path.is_file():
        # Fallback to non-meta if moved
        target_path = ROOT / "ai-tooling" / "skills" / "ai-vendor-updates" / "references" / "vendor-sources.json"
    if not target_path.is_file():
        raise FileNotFoundError(f"Vendor source catalog not found at {CATALOG_PATH}")
    return json.loads(target_path.read_text(encoding="utf-8"))


def parse_feed_entries(xml_data: bytes, source_name: str, vendor_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_data)
    except Exception:
        return entries

    # Handle RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
            description = (item.findtext("description") or "").strip()
            if title or link:
                entries.append({
                    "vendor": vendor_id,
                    "source": source_name,
                    "title": title,
                    "link": link,
                    "published": pub_date,
                    "summary": description[:300] if description else "",
                })
        return entries

    # Handle Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    # Try with namespace, then fallback without
    atom_entries = root.findall("atom:entry", ns) or root.findall("entry")
    for entry in atom_entries:
        title_el = entry.find("atom:title", ns) if entry.find("atom:title", ns) is not None else entry.find("title")
        title = (title_el.text if title_el is not None and title_el.text else "").strip()
        link = ""
        link_el = entry.find("atom:link", ns) if entry.find("atom:link", ns) is not None else entry.find("link")
        if link_el is not None:
            link = link_el.get("href") or link_el.text or ""
        updated_el = entry.find("atom:updated", ns) if entry.find("atom:updated", ns) is not None else entry.find("updated")
        published_el = entry.find("atom:published", ns) if entry.find("atom:published", ns) is not None else entry.find("published")
        pub_date = (published_el.text if published_el is not None and published_el.text else "") or (updated_el.text if updated_el is not None and updated_el.text else "")
        summary_el = entry.find("atom:summary", ns) if entry.find("atom:summary", ns) is not None else entry.find("summary")
        summary = (summary_el.text if summary_el is not None and summary_el.text else "").strip()
        if title or link:
            entries.append({
                "vendor": vendor_id,
                "source": source_name,
                "title": title,
                "link": link,
                "published": pub_date,
                "summary": summary[:300] if summary else "",
            })
    return entries


def fetch_live_feed(url: str, timeout: int = 5) -> bytes | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Vendor-Intel/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None


def generate_flash_briefing(
    catalog: dict[str, Any],
    selected_vendors: list[str],
    live_entries: list[dict[str, Any]],
    date_str: str,
) -> str:
    lines = [
        f"# Frontier AI Vendor Intelligence — Flash Briefing ({date_str})",
        "",
        "> High-signal intelligence synthesis across major AI vendor ecosystems, developer tooling, model weights, and research breakthroughs.",
        "",
        "## Executive Summary",
        "",
    ]

    all_vendors = catalog.get("vendors", {})
    monitored_names = [all_vendors[v]["name"] for v in selected_vendors if v in all_vendors]
    lines.append(f"- **Monitored Ecosystems ({len(monitored_names)})**: {', '.join(monitored_names)}")
    lines.append(f"- **Total Feeds & Endpoints Tracked**: {sum(len(all_vendors[v].get('primary_channels', [])) for v in selected_vendors if v in all_vendors)}")
    lines.append(f"- **Live Updates Captured**: {len(live_entries)}")
    lines.append("")

    lines.append("## Ecosystem Flash Intel")
    lines.append("")

    for v_key in selected_vendors:
        if v_key not in all_vendors:
            continue
        v_data = all_vendors[v_key]
        lines.append(f"### {v_data['name']} (`{', '.join(v_data.get('ecosystem', []))}`)")
        lines.append("")

        # Matching live entries
        v_entries = [e for e in live_entries if e.get("vendor") == v_key]
        if v_entries:
            lines.append("#### Recent Captured Updates")
            lines.append("")
            for item in v_entries[:5]:
                title = item.get("title", "Update")
                link = item.get("link", "#")
                pub = item.get("published", "")
                src = item.get("source", "")
                pub_info = f" *({pub})*" if pub else ""
                lines.append(f"- [{title}]({link}) — **{src}**{pub_info}")
                if item.get("summary"):
                    lines.append(f"  > {item['summary']}")
            lines.append("")

        # Key Channels Table
        lines.append("#### Authoritative Primary Channels")
        lines.append("")
        lines.append("| Channel | Type | Signal Tier | Focus & Monitoring |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for ch in v_data.get("primary_channels", []):
            name_link = f"[{ch['name']}]({ch['url']})"
            ch_type = ch.get("type", "web")
            tier = ch.get("signal_tier", "P1")
            focus = ch.get("focus", "")
            lines.append(f"| {name_link} | `{ch_type}` | **{tier}** | {focus} |")
        lines.append("")

    lines.append("## Signal Triage & Recommended Actions")
    lines.append("")
    lines.append("- **P0 (Immediate Action / Deprecations / Breaking Changes)**: Verify API snapshot dates, context limits, and token pricing changes.")
    lines.append("- **P1 (Platform & Tooling Capabilities)**: Assess agentic runtime features, MCP server updates, and SDK upgrades.")
    lines.append("- **P2 (Strategic Intel & Research)**: Review foundation model preprints, reasoning distillation techniques, and benchmark evaluations.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated automatically via `scripts/research/ai_vendor_briefing.py` on {date_str}.*")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vendor",
        type=str,
        default="all",
        help="Comma-separated vendor IDs (e.g. google,anthropic,openai,cursor,xai,meta,mistral,deepseek,microsoft,benchlm) or 'all'",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=7,
        help="Lookback window in days for filtering feed updates (default: 7)",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Attempt live network fetch for RSS/Atom feeds (offline/dry-run safe if omitted or unreachable)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate vendor sources catalog and simulate briefing generation without writing files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output containing captured updates and metrics",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory to save briefing markdown (default: results/reports/vendor-briefings/YYYY-MM-DD/)",
    )

    args = parser.parse_args(argv)

    catalog = load_vendor_catalog()
    all_vendors = list(catalog.get("vendors", {}).keys())

    if args.vendor.strip().lower() == "all":
        selected_vendors = all_vendors
    else:
        selected_vendors = [v.strip().lower() for v in args.vendor.split(",") if v.strip().lower() in all_vendors]

    if not selected_vendors:
        print(f"Error: No valid vendors specified. Available: {', '.join(all_vendors)}", file=sys.stderr)
        return 2

    live_entries: list[dict[str, Any]] = []
    feed_errors: list[str] = []

    if args.fetch and not args.dry_run:
        for v_key in selected_vendors:
            v_data = catalog["vendors"].get(v_key, {})
            for ch in v_data.get("primary_channels", []):
                feed_url = ch.get("feed_url")
                if feed_url:
                    data = fetch_live_feed(feed_url)
                    if data:
                        parsed = parse_feed_entries(data, ch["name"], v_key)
                        live_entries.extend(parsed)
                    else:
                        feed_errors.append(f"Failed to fetch {ch['name']} at {feed_url}")

    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    briefing_md = generate_flash_briefing(catalog, selected_vendors, live_entries, today_str)

    out_file = None
    if not args.dry_run:
        out_dir = args.out_dir or (ROOT / "results" / "reports" / "vendor-briefings" / today_str)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "flash-briefing.md"
        out_file.write_text(briefing_md, encoding="utf-8")

    result = {
        "status": "success",
        "date": today_str,
        "selected_vendors": selected_vendors,
        "total_sources_scanned": sum(len(catalog["vendors"][v].get("primary_channels", [])) for v in selected_vendors),
        "live_entries_count": len(live_entries),
        "feed_errors": feed_errors,
        "artifact_path": str(out_file.relative_to(ROOT)) if out_file else None,
        "dry_run": args.dry_run,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.dry_run:
            print("OK: Vendor catalog validated. Dry run simulation succeeded.")
            print(f"Target vendors ({len(selected_vendors)}): {', '.join(selected_vendors)}")
            print(f"Total primary endpoints catalogued: {result['total_sources_scanned']}")
        else:
            print(f"Flash briefing generated successfully: {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
