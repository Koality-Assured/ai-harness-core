"""Orchestrate dry-run validation sweeps and simulated multi-agent fleet benchmarks.

tags: [benchmarks, agents, fleet, simulation, dry-run]
routing_hints: [fleet-benchmark, agent-dry-run, headroom, cache-invariance, isolation]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from md import (  # noqa: E402
    agent_ids,
    agent_paths,
    load_agent_record,
    load_skill_record,
    parse_frontmatter,
    skill_paths,
)
from paths import REPO_ROOT as ROOT  # noqa: E402

# Import local cost calculation helpers
from estimate_agent_costs import (  # noqa: E402
    compute_trajectory_cost,
    inspect_agent_tokens,
    inspect_skill_tokens,
)


def benchmark_single_agent(
    agent_path: Path,
    known_agent_ids: set[str],
    all_skills: list[Path],
    turns_to_simulate: int = 5,
) -> dict[str, Any]:
    """Run simulated benchmark for a single agent."""
    start_time = time.perf_counter()
    agent_info = inspect_agent_tokens(agent_path.parent)
    agent_id = agent_info["agent_id"]

    # Parse full frontmatter for contracts and assertions
    text = agent_path.read_text(encoding="utf-8")
    fields, _ = parse_frontmatter(text)

    # 1. Delegation targets verification
    delegations = fields.get("delegation_targets", [])
    invalid_delegations = [d for d in delegations if d not in known_agent_ids and d != "router"]

    # 2. Owned skills mapping
    owned_skills = []
    for sp in all_skills:
        s_info = inspect_skill_tokens(sp)
        if s_info["owner_agent"] == agent_id:
            owned_skills.append(s_info)

    # 3. Prompt cache invariance check (static prefix byte stability)
    prefix_violations = []
    first_lines = text[:500].splitlines()
    for idx, line in enumerate(first_lines):
        lower = line.lower()
        if "last_verified" in lower:
            continue
        if any(keyword in lower for keyword in ("current_time", "random_seed", "temp_path", "runtime_id")):
            prefix_violations.append(f"Line {idx+1}: contains dynamic token ({line.strip()})")

    # 4. Trajectory and headroom simulation
    trajectory = compute_trajectory_cost(
        static_prefix_tokens=agent_info["static_prefix_tokens"],
        turns=turns_to_simulate,
    )

    headroom_remaining = max(0, agent_info["token_ceiling"] - trajectory["final_context_tokens"])
    headroom_pct = round((headroom_remaining / agent_info["token_ceiling"]) * 100, 1)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "agent_id": agent_id,
        "model_tier": agent_info["model_tier"],
        "token_ceiling": agent_info["token_ceiling"],
        "static_prefix_tokens": agent_info["static_prefix_tokens"],
        "tool_count": agent_info["tool_count"],
        "owned_skills_count": len(owned_skills),
        "owned_skills": [s["skill_name"] for s in owned_skills],
        "delegation_targets_valid": len(invalid_delegations) == 0,
        "invalid_delegations": invalid_delegations,
        "prompt_cache_invariant": len(prefix_violations) == 0,
        "prefix_violations": prefix_violations,
        "simulated_turns": turns_to_simulate,
        "final_context_tokens": trajectory["final_context_tokens"],
        "headroom_pct": headroom_pct,
        "cost_5_turns_usd": trajectory["cost_with_cache_usd"],
        "elapsed_ms": elapsed_ms,
        "status": "PASS" if len(invalid_delegations) == 0 and len(prefix_violations) == 0 else "FAIL",
    }


if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def render_fleet_report(
    fleet_results: list[dict[str, Any]],
    summary_stats: dict[str, Any],
) -> str:
    """Render comprehensive Markdown fleet report."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: agent-fleet-benchmark",
        "purpose: [process]",
        "topics: [benchmarks, fleet, dry-run, headroom, cache-invariance]",
        f"generated_at_utc: {now_utc}",
        "---",
        "",
        "# Agent Fleet Benchmark & Dry-Run Simulation",
        "",
        "Empirical dry-run validation and simulation sweep across all registered agents and skills, auditing prompt cache invariance, delegation graphs, tool schema footprints, and context ceiling headroom.",
        "",
        "## Fleet Summary",
        "",
        f"- Total Agents Audited: **{summary_stats['total_agents']}**",
        f"- Total Skills Mapped: **{summary_stats['total_skills']}**",
        f"- Fleet Pass Rate: **{summary_stats['pass_rate']}%** ({summary_stats['passed_agents']}/{summary_stats['total_agents']})",
        f"- Median Static Prefix: **{summary_stats['median_static_prefix']} tokens**",
        f"- Average Headroom Remaining: **{summary_stats['avg_headroom_pct']}%**",
        f"- Total Benchmark Wall Time: **{summary_stats['total_elapsed_ms']} ms**",
        "",
        "## Agent Breakdown",
        "",
        "| Agent | Tier | Tools | Owned Skills | Static Prefix | 5-Turn Context | Headroom | Cache Invariant | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item in fleet_results:
        status_badge = f"**{item['status']}**" if item['status'] == "PASS" else f"**FAIL**"
        cache_badge = "Yes" if item['prompt_cache_invariant'] else "No"
        lines.append(
            f"| [`{item['agent_id']}`](../../../ai-tooling/agents/{item['agent_id']}/AGENT.md) | "
            f"`{item['model_tier']}` | {item['tool_count']} | {item['owned_skills_count']} | "
            f"{item['static_prefix_tokens']:,} | {item['final_context_tokens']:,} | "
            f"{item['headroom_pct']}% | {cache_badge} | {status_badge} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Run benchmark on entire agent fleet (default)")
    parser.add_argument("--agents", help="Comma-separated agent IDs to benchmark")
    parser.add_argument("--turns", type=int, default=5, help="Number of turns to simulate (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--out", help="Output directory under repo root")
    parser.add_argument("--dry-run", action="store_true", help="Run dry run without writing files")
    args = parser.parse_args(argv)

    all_agent_paths = agent_paths(ROOT)
    known_agents = agent_ids(ROOT)
    all_skills = skill_paths(ROOT)

    if args.agents:
        selected_ids = {a.strip() for a in args.agents.split(",") if a.strip()}
        target_paths = [p for p in all_agent_paths if p.parent.name in selected_ids]
    else:
        target_paths = all_agent_paths

    start_fleet = time.perf_counter()
    fleet_results: list[dict[str, Any]] = []

    for p in target_paths:
        res = benchmark_single_agent(
            agent_path=p,
            known_agent_ids=known_agents,
            all_skills=all_skills,
            turns_to_simulate=args.turns,
        )
        fleet_results.append(res)

    total_elapsed_ms = round((time.perf_counter() - start_fleet) * 1000, 2)
    passed_count = sum(1 for r in fleet_results if r["status"] == "PASS")
    total_count = len(fleet_results)

    static_prefixes = [r["static_prefix_tokens"] for r in fleet_results]
    median_prefix = sorted(static_prefixes)[len(static_prefixes) // 2] if static_prefixes else 0
    avg_headroom = round(sum(r["headroom_pct"] for r in fleet_results) / max(1, total_count), 1)

    summary_stats = {
        "total_agents": total_count,
        "total_skills": len(all_skills),
        "passed_agents": passed_count,
        "pass_rate": round((passed_count / max(1, total_count)) * 100, 1),
        "median_static_prefix": median_prefix,
        "avg_headroom_pct": avg_headroom,
        "total_elapsed_ms": total_elapsed_ms,
    }

    report_md = render_fleet_report(fleet_results, summary_stats)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/benchmarks/fleet/{today}"
    out_dir = ROOT / out_rel

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.md").write_text(report_md, encoding="utf-8")
        (out_dir / "summary.json").write_text(
            json.dumps({"summary": summary_stats, "agents": fleet_results}, indent=2),
            encoding="utf-8",
        )

    if args.json:
        print(json.dumps({"summary": summary_stats, "agents": fleet_results}, indent=2))
    else:
        print(report_md)

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
