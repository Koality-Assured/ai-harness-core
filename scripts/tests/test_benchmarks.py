"""Unit tests for empirical benchmarking and cost estimation tooling.

tags: [tests, benchmarks, cost-layers, agents, retrieval, fleet]
routing_hints: [tests, test-benchmarks, cost-estimator, fleet-benchmark, mrr]

Run: python -m unittest scripts.tests.test_benchmarks -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "benchmarks"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from paths import REPO_ROOT as ROOT  # noqa: E402
from estimate_agent_costs import (  # noqa: E402
    DEFAULT_PRICING_TABLE,
    compute_trajectory_cost,
    estimate_agent_and_skill,
    estimate_tokens,
    inspect_agent_tokens,
)
from benchmark_agent_fleet import benchmark_single_agent  # noqa: E402
from benchmark_retrieval import evaluate_retrieval, fallback_search  # noqa: E402
from benchmark_tool_efficiency import benchmark_fixture, TOOL_FIXTURES  # noqa: E402
from benchmark_task_eval import evaluate_task, load_task_suite  # noqa: E402
from run_benchmark_suite import run_benchmark_script  # noqa: E402


class BenchmarkSuiteUnitTests(unittest.TestCase):
    def test_token_estimation_formula(self) -> None:
        text = "Hello world! This is a test prompt for estimating tokens."
        tokens = estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertLessEqual(tokens, len(text))

    def test_trajectory_cost_and_kv_caching_savings(self) -> None:
        traj = compute_trajectory_cost(
            static_prefix_tokens=2000,
            turns=5,
            pricing=DEFAULT_PRICING_TABLE["standard"],
        )
        self.assertEqual(traj["turns"], 5)
        self.assertGreater(traj["total_cached_tokens"], 0)
        self.assertGreater(traj["kv_cache_savings_pct"], 0.0)
        self.assertLess(traj["cost_with_cache_usd"], traj["cost_without_cache_usd"])

    def test_estimate_agent_and_skill_pairing(self) -> None:
        est = estimate_agent_and_skill(
            agent_id="benchmark-agent",
            skill_name="agent-cost-estimator",
            tier="standard",
            turns=5,
        )
        self.assertEqual(est["agent"]["agent_id"], "benchmark-agent")
        self.assertEqual(est["skill"]["skill_name"], "agent-cost-estimator")
        self.assertIn("fast", est["tier_comparisons"])
        self.assertIn("standard", est["tier_comparisons"])
        self.assertIn("high", est["tier_comparisons"])
        self.assertIn("max", est["tier_comparisons"])
        self.assertGreater(est["headroom_pct"], 80.0)

    def test_benchmark_single_agent_fleet_validation(self) -> None:
        agent_path = ROOT / "ai-tooling" / "agents" / "benchmark-agent" / "AGENT.md"
        all_skills = list((ROOT / "ai-tooling" / "skills").rglob("SKILL.md"))
        res = benchmark_single_agent(
            agent_path=agent_path,
            known_agent_ids={"benchmark-agent", "router", "script-ops", "artifact-agent", "router-maintenance"},
            all_skills=all_skills,
            turns_to_simulate=5,
        )
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["prompt_cache_invariant"])
        self.assertTrue(res["delegation_targets_valid"])
        self.assertGreaterEqual(res["owned_skills_count"], 1)

    def test_retrieval_benchmark_precision_and_mrr(self) -> None:
        queries = [
            {
                "query": "isolate work git worktree",
                "expected_paths": ["ai-tooling/skills/meta/isolate-work/SKILL.md"],
                "category": "routing",
            }
        ]
        res = evaluate_retrieval(queries)
        self.assertEqual(res["total_queries"], 1)
        self.assertGreaterEqual(res["mrr"], 0.5)
        self.assertIn("p@1", res["precisions"])

    def test_tool_efficiency_fixture_compression(self) -> None:
        fixture = TOOL_FIXTURES[0]
        res = benchmark_fixture(fixture)
        self.assertEqual(res["name"], fixture["name"])
        self.assertEqual(res["fact_accuracy_pct"], 100.0)
        self.assertGreaterEqual(res["raw_tokens"], res["compressed_tokens"])

    def test_task_eval_suite_scoring(self) -> None:
        suite = load_task_suite()
        self.assertIn("tasks", suite)
        self.assertGreater(len(suite["tasks"]), 0)
        eval_res = evaluate_task(suite["tasks"][0])
        self.assertEqual(eval_res["status"], "PASS")
        self.assertTrue(eval_res["passed"])
        self.assertGreaterEqual(eval_res["score_pct"], 90.0)


if __name__ == "__main__":
    unittest.main()
