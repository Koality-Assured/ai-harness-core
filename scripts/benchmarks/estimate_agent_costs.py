"""Estimate token consumption, KV cache savings, and monetary costs for agents and paired skills.

tags: [benchmarks, cost-layers, agents, pricing, tokens]
routing_hints: [cost-estimator, agent-cost, token-budget, kv-cache, model-tiers]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from md import agent_paths, load_agent_record, load_skill_record, parse_frontmatter, skill_paths  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

# Standard pricing models per 1M tokens (USD)
DEFAULT_PRICING_TABLE: dict[str, dict[str, Any]] = {
    "fast": {
        "description": "Cheapest fastest model tier (Gemini 3.7 Flash / Claude 3.5 Haiku / GPT-4o mini)",
        "input_per_m": 0.15,
        "cached_input_per_m": 0.0375,
        "output_per_m": 0.60,
    },
    "standard": {
        "description": "Standard tier (Gemini 3.7 Flash / GPT Luna / Grok 4.5)",
        "input_per_m": 1.25,
        "cached_input_per_m": 0.30,
        "output_per_m": 5.00,
    },
    "high": {
        "description": "High reasoning tier (Claude 3.7 Sonnet / GPT Terra / Grok 4.6)",
        "input_per_m": 3.00,
        "cached_input_per_m": 0.30,
        "output_per_m": 15.00,
    },
    "max": {
        "description": "Max capability tier (Gemini 3.1 Pro / GPT Sol / Claude Extended Thinking)",
        "input_per_m": 5.00,
        "cached_input_per_m": 1.25,
        "output_per_m": 25.00,
    },
}

# Provider-specific pricing presets
PROVIDER_PRICING: dict[str, dict[str, dict[str, float]]] = {
    "google": {
        "gemini-3-7-flash": {"input_per_m": 0.15, "cached_input_per_m": 0.0375, "output_per_m": 0.60},
        "gemini-3-1-pro": {"input_per_m": 1.25, "cached_input_per_m": 0.3125, "output_per_m": 5.00},
    },
    "anthropic": {
        "claude-3-5-haiku": {"input_per_m": 0.80, "cached_input_per_m": 0.08, "output_per_m": 4.00},
        "claude-3-7-sonnet": {"input_per_m": 3.00, "cached_input_per_m": 0.30, "output_per_m": 15.00},
    },
    "openai": {
        "gpt-4o-mini": {"input_per_m": 0.15, "cached_input_per_m": 0.075, "output_per_m": 0.60},
        "gpt-5-4-turbo": {"input_per_m": 2.50, "cached_input_per_m": 1.25, "output_per_m": 10.00},
    },
}

TOOL_SCHEMA_TOKEN_ESTIMATE = 160  # Average token footprint per allowed tool schema definition


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count (~4 chars per token for English text/markdown)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 3.8))


def inspect_agent_tokens(agent_folder: Path) -> dict[str, Any]:
    """Calculate token footprint for an agent definition."""
    agent_file = agent_folder / "AGENT.md"
    if not agent_file.is_file():
        raise FileNotFoundError(f"Agent definition not found: {agent_file}")

    text = agent_file.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)

    agent_id = fields.get("agent_id", agent_folder.name)
    model_tier = fields.get("model_tier", "standard")
    token_ceiling = fields.get("token_ceiling", 100000)
    allowed_tools = fields.get("allowed_tools", [])

    prompt_tokens = estimate_tokens(text)
    body_tokens = estimate_tokens(body)
    tool_tokens = len(allowed_tools) * TOOL_SCHEMA_TOKEN_ESTIMATE

    # Static prefix includes agent prompt + tools schemas
    static_prefix_tokens = prompt_tokens + tool_tokens

    return {
        "agent_id": agent_id,
        "model_tier": model_tier,
        "token_ceiling": token_ceiling,
        "allowed_tools": allowed_tools,
        "tool_count": len(allowed_tools),
        "prompt_tokens": prompt_tokens,
        "body_tokens": body_tokens,
        "tool_tokens": tool_tokens,
        "static_prefix_tokens": static_prefix_tokens,
    }


def inspect_skill_tokens(skill_path: Path) -> dict[str, Any]:
    """Calculate token footprint for a skill definition."""
    if not skill_path.is_file():
        raise FileNotFoundError(f"Skill definition not found: {skill_path}")

    text = skill_path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)

    skill_name = fields.get("name", skill_path.parent.name)
    owner_agent = fields.get("owner_agent", "")
    rank = fields.get("rank", "medium")
    isolation = fields.get("isolation", "read-only")

    skill_tokens = estimate_tokens(text)
    body_tokens = estimate_tokens(body)

    return {
        "skill_name": skill_name,
        "owner_agent": owner_agent,
        "rank": rank,
        "isolation": isolation,
        "skill_tokens": skill_tokens,
        "body_tokens": body_tokens,
    }


def compute_trajectory_cost(
    static_prefix_tokens: int,
    turns: int = 5,
    avg_user_turn_tokens: int = 250,
    avg_tool_output_tokens: int = 600,
    avg_assistant_turn_tokens: int = 350,
    pricing: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Model multi-turn token accumulation, KV cache hits, and financial cost."""
    if pricing is None:
        pricing = DEFAULT_PRICING_TABLE["standard"]

    in_price = pricing["input_per_m"]
    cached_in_price = pricing["cached_input_per_m"]
    out_price = pricing["output_per_m"]

    total_input_tokens = 0
    total_cached_tokens = 0
    total_uncached_tokens = 0
    total_output_tokens = 0

    accumulated_context = static_prefix_tokens

    turn_details = []

    for turn in range(1, turns + 1):
        # User input or tool feedback in this turn
        turn_new_input = avg_user_turn_tokens if turn == 1 else avg_tool_output_tokens

        # In turn 1: static prefix + user prompt are full uncached inputs
        # In turn 2+: static prefix + prior turns are cached in KV cache
        if turn == 1:
            cached_turn_in = 0
            uncached_turn_in = accumulated_context + turn_new_input
        else:
            cached_turn_in = accumulated_context
            uncached_turn_in = turn_new_input

        accumulated_context += turn_new_input + avg_assistant_turn_tokens
        turn_out = avg_assistant_turn_tokens

        total_cached_tokens += cached_turn_in
        total_uncached_tokens += uncached_turn_in
        total_input_tokens += cached_turn_in + uncached_turn_in
        total_output_tokens += turn_out

        turn_cost = (
            (cached_turn_in / 1_000_000 * cached_in_price)
            + (uncached_turn_in / 1_000_000 * in_price)
            + (turn_out / 1_000_000 * out_price)
        )

        turn_details.append({
            "turn": turn,
            "cached_input_tokens": cached_turn_in,
            "uncached_input_tokens": uncached_turn_in,
            "output_tokens": turn_out,
            "context_tokens_end": accumulated_context,
            "turn_cost_usd": round(turn_cost, 6),
        })

    # Cost with KV Caching
    cost_with_cache = (
        (total_cached_tokens / 1_000_000 * cached_in_price)
        + (total_uncached_tokens / 1_000_000 * in_price)
        + (total_output_tokens / 1_000_000 * out_price)
    )

    # Cost without KV Caching (if every turn paid full input price)
    cost_without_cache = (
        (total_input_tokens / 1_000_000 * in_price)
        + (total_output_tokens / 1_000_000 * out_price)
    )

    savings_usd = max(0.0, cost_without_cache - cost_with_cache)
    savings_pct = round((savings_usd / cost_without_cache * 100) if cost_without_cache > 0 else 0, 1)

    return {
        "turns": turns,
        "final_context_tokens": accumulated_context,
        "total_input_tokens": total_input_tokens,
        "total_cached_tokens": total_cached_tokens,
        "total_uncached_tokens": total_uncached_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_with_cache_usd": round(cost_with_cache, 6),
        "cost_without_cache_usd": round(cost_without_cache, 6),
        "kv_cache_savings_usd": round(savings_usd, 6),
        "kv_cache_savings_pct": savings_pct,
        "cost_per_1k_runs_usd": round(cost_with_cache * 1000, 2),
        "turn_details": turn_details,
    }


def estimate_agent_and_skill(
    agent_id: str,
    skill_name: str | None = None,
    tier: str | None = None,
    turns: int = 5,
) -> dict[str, Any]:
    """Perform comprehensive cost estimation for an agent and optional skill."""
    agent_dir = ROOT / "ai-tooling" / "agents" / agent_id
    agent_info = inspect_agent_tokens(agent_dir)

    skill_info = None
    skill_tokens = 0
    if skill_name:
        all_skills = skill_paths(ROOT)
        matched = [p for p in all_skills if p.parent.name == skill_name]
        if not matched:
            raise FileNotFoundError(f"Skill not found: {skill_name}")
        skill_info = inspect_skill_tokens(matched[0])
        skill_tokens = skill_info["skill_tokens"]

    effective_tier = tier or agent_info["model_tier"]
    pricing = DEFAULT_PRICING_TABLE.get(effective_tier, DEFAULT_PRICING_TABLE["standard"])

    static_prefix = agent_info["static_prefix_tokens"] + skill_tokens

    trajectory = compute_trajectory_cost(
        static_prefix_tokens=static_prefix,
        turns=turns,
        pricing=pricing,
    )

    # Multi-tier comparative matrix
    tier_comparisons = {}
    for t_name, t_pricing in DEFAULT_PRICING_TABLE.items():
        t_traj = compute_trajectory_cost(
            static_prefix_tokens=static_prefix,
            turns=turns,
            pricing=t_pricing,
        )
        tier_comparisons[t_name] = {
            "cost_per_run_usd": t_traj["cost_with_cache_usd"],
            "cost_per_1k_runs_usd": t_traj["cost_per_1k_runs_usd"],
            "savings_pct": t_traj["kv_cache_savings_pct"],
        }

    headroom_remaining = max(0, agent_info["token_ceiling"] - trajectory["final_context_tokens"])
    headroom_pct = round((headroom_remaining / agent_info["token_ceiling"]) * 100, 1)

    return {
        "agent": agent_info,
        "skill": skill_info,
        "effective_tier": effective_tier,
        "static_prefix_tokens": static_prefix,
        "trajectory": trajectory,
        "tier_comparisons": tier_comparisons,
        "token_ceiling": agent_info["token_ceiling"],
        "headroom_remaining_tokens": headroom_remaining,
        "headroom_pct": headroom_pct,
    }


def render_markdown_report(estimates: list[dict[str, Any]], title: str = "Agent & Paired Skill Cost Estimation") -> str:
    """Render a structured Markdown report."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: agent-cost-estimates",
        "purpose: [process]",
        "topics: [benchmarks, cost-layers, tokens, pricing, kv-cache]",
        f"generated_at_utc: {now_utc}",
        "---",
        "",
        f"# {title}",
        "",
        "Empirical token and financial cost estimation modeling system prompt footprints, tool schemas, KV cache hit rates, and multi-turn trajectories across model tiers (`fast`, `standard`, `high`, `max`).",
        "",
        "## Summary Matrix",
        "",
        "| Agent | Paired Skill | Tier | Static Prefix (Tokens) | 5-Turn Cost (USD) | 1K Runs (USD) | Cache Savings | Ceiling Headroom |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for est in estimates:
        ag = est["agent"]
        sk = est.get("skill")
        sk_label = f"`{sk['skill_name']}`" if sk else "—"
        traj = est["trajectory"]
        lines.append(
            f"| [`{ag['agent_id']}`](../../../ai-tooling/agents/{ag['agent_id']}/AGENT.md) | "
            f"{sk_label} | `{est['effective_tier']}` | {est['static_prefix_tokens']:,} | "
            f"${traj['cost_with_cache_usd']:.5f} | ${traj['cost_per_1k_runs_usd']:.2f} | "
            f"{traj['kv_cache_savings_pct']}% | {est['headroom_pct']}% |"
        )

    lines.extend([
        "",
        "## Model Tier Pricing Reference",
        "",
        "| Tier | Input / 1M | Cached Input / 1M | Output / 1M | Example Host Models |",
        "| --- | --- | --- | --- | --- |",
    ])
    for tier_name, tier_info in DEFAULT_PRICING_TABLE.items():
        lines.append(
            f"| `{tier_name}` | ${tier_info['input_per_m']:.2f} | ${tier_info['cached_input_per_m']:.4f} | "
            f"${tier_info['output_per_m']:.2f} | {tier_info['description']} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", help="Agent ID to evaluate (e.g. benchmark-agent, router)")
    parser.add_argument("--skill", help="Optional paired skill name to evaluate together")
    parser.add_argument("--all", action="store_true", help="Evaluate all registered agents")
    parser.add_argument("--tier", choices=list(DEFAULT_PRICING_TABLE.keys()), help="Override model tier")
    parser.add_argument("--turns", type=int, default=5, help="Number of turns to simulate (default: 5)")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    parser.add_argument("--out", help="Output directory under repo root")
    parser.add_argument("--dry-run", action="store_true", help="Run estimation without writing reports")
    args = parser.parse_args(argv)

    if not args.agent and not args.all:
        print("error: specify --agent <ID> or --all", file=sys.stderr)
        return 2

    agent_files = agent_paths(ROOT)
    results: list[dict[str, Any]] = []

    if args.agent:
        matched = [f for f in agent_files if f.parent.name == args.agent]
        if not matched:
            print(f"error: agent '{args.agent}' not found under ai-tooling/agents/", file=sys.stderr)
            return 2
        target_files = matched
    else:
        target_files = agent_files

    for ag_file in target_files:
        try:
            est = estimate_agent_and_skill(
                agent_id=ag_file.parent.name,
                skill_name=args.skill if args.agent else None,
                tier=args.tier,
                turns=args.turns,
            )
            results.append(est)
        except Exception as e:
            print(f"error analyzing agent {ag_file.parent.name}: {e}", file=sys.stderr)
            return 1

    report_md = render_markdown_report(results)

    if args.out and not args.dry_run:
        out_path = ROOT / args.out
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "report.md").write_text(report_md, encoding="utf-8")
        (out_path / "estimates.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote report and estimates to {out_path}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(report_md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
