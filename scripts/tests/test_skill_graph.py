"""Unit tests for skill dependency DAG resolution, topological ordering, and Schema V2 conventions.

tags: [tests, routing, skills, dag]
routing_hints: [tests, dag, topological-sort, dependencies, prerequisites]

Run: python -m unittest scripts/tests/test_skill_graph.py -v
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Setup paths
_ROUTING = Path(__file__).resolve().parents[1] / "routing"
_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_ROUTING) not in sys.path:
    sys.path.insert(0, str(_ROUTING))
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from resolve_skill_graph import (  # noqa: E402
    ALLOWED_FAILURE_POLICIES,
    DEFAULT_FAILURE_POLICY,
    ExecutionPlan,
    InvalidLifecyclePolicyError,
    InvalidSkillSchemaError,
    MissingSkillDependencyError,
    SkillDefinition,
    SkillGraph,
    SkillGraphCycleError,
    SkillNotFoundError,
    load_skill_from_file,
    main,
    parse_skill_frontmatter,
)


class TestLinearDAGResolution(unittest.TestCase):
    """Tests for linear dependency chains."""

    def test_single_isolated_skill(self) -> None:
        graph = SkillGraph()
        skill_a = SkillDefinition(name="skill-a")
        graph.add_skill(skill_a)

        plan = graph.resolve_plan(target="skill-a")
        self.assertEqual(plan.target, "skill-a")
        self.assertEqual(plan.topological_order, ["skill-a"])
        self.assertEqual(plan.stages, [["skill-a"]])

    def test_linear_required_dependencies(self) -> None:
        """skill-c -> requires skill-b -> requires skill-a."""
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-a"))
        graph.add_skill(SkillDefinition(name="skill-b", required_skills=["skill-a"]))
        graph.add_skill(SkillDefinition(name="skill-c", required_skills=["skill-b"]))

        plan = graph.resolve_plan(target="skill-c")
        self.assertEqual(plan.topological_order, ["skill-a", "skill-b", "skill-c"])
        self.assertEqual(plan.stages, [["skill-a"], ["skill-b"], ["skill-c"]])

    def test_linear_delegated_dependencies(self) -> None:
        """skill-a delegates to skill-b, skill-b delegates to skill-c."""
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-a", delegated_skills=["skill-b"]))
        graph.add_skill(SkillDefinition(name="skill-b", delegated_skills=["skill-c"]))
        graph.add_skill(SkillDefinition(name="skill-c"))

        plan = graph.resolve_plan(target="skill-a")
        self.assertEqual(plan.topological_order, ["skill-a", "skill-b", "skill-c"])
        self.assertEqual(plan.stages, [["skill-a"], ["skill-b"], ["skill-c"]])


class TestBranchingDAGTopologicalOrder(unittest.TestCase):
    """Tests for branching, diamond, and multi-stage DAGs."""

    def test_diamond_dag_resolution(self) -> None:
        """Diamond DAG:

             skill-a
             /     \\
        skill-b   skill-c
             \\     /
             skill-d
        """
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-a"))
        graph.add_skill(SkillDefinition(name="skill-b", required_skills=["skill-a"]))
        graph.add_skill(SkillDefinition(name="skill-c", required_skills=["skill-a"]))
        graph.add_skill(SkillDefinition(name="skill-d", required_skills=["skill-b", "skill-c"]))

        plan = graph.resolve_plan(target="skill-d")
        self.assertEqual(len(plan.stages), 3)
        self.assertEqual(plan.stages[0], ["skill-a"])
        self.assertEqual(sorted(plan.stages[1]), ["skill-b", "skill-c"])
        self.assertEqual(plan.stages[2], ["skill-d"])

        # Topological order check: skill-a must come before b and c; b and c before d
        order = plan.topological_order
        self.assertEqual(order[0], "skill-a")
        self.assertIn("skill-b", order[1:3])
        self.assertIn("skill-c", order[1:3])
        self.assertEqual(order[3], "skill-d")

    def test_concurrent_delegations_with_shared_prerequisite(self) -> None:
        """Parent skill delegates to worker-1 and worker-2 concurrently, both requiring common-setup."""
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="common-setup"))
        graph.add_skill(
            SkillDefinition(
                name="orchestrator",
                delegated_skills=["worker-1", "worker-2"],
            )
        )
        graph.add_skill(
            SkillDefinition(
                name="worker-1",
                required_skills=["common-setup"],
            )
        )
        graph.add_skill(
            SkillDefinition(
                name="worker-2",
                required_skills=["common-setup"],
            )
        )

        plan = graph.resolve_plan(target="orchestrator")
        # Stage 0: orchestrator and common-setup (both independent)
        self.assertEqual(sorted(plan.stages[0]), ["common-setup", "orchestrator"])
        # Stage 1: worker-1 and worker-2 (both prerequisites satisfied)
        self.assertEqual(sorted(plan.stages[1]), ["worker-1", "worker-2"])

    def test_complex_multi_branch_dag(self) -> None:
        """Multi-layer DAG with disjoint prerequisites and chained delegates."""
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="isolate-work"))
        graph.add_skill(SkillDefinition(name="qmd-index"))
        graph.add_skill(
            SkillDefinition(
                name="feature-builder",
                required_skills=["isolate-work", "qmd-index"],
                delegated_skills=["code-review", "threat-model"],
            )
        )
        graph.add_skill(SkillDefinition(name="code-review"))
        graph.add_skill(
            SkillDefinition(
                name="threat-model",
                delegated_skills=["security-report"],
            )
        )
        graph.add_skill(SkillDefinition(name="security-report"))

        plan = graph.resolve_plan(target="feature-builder")
        self.assertEqual(sorted(plan.stages[0]), ["isolate-work", "qmd-index"])
        self.assertEqual(plan.stages[1], ["feature-builder"])
        self.assertEqual(sorted(plan.stages[2]), ["code-review", "threat-model"])
        self.assertEqual(plan.stages[3], ["security-report"])


class TestCyclicDependencyDetection(unittest.TestCase):
    """Tests for cycle detection in required and delegated edges."""

    def test_direct_two_node_cycle(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-a", required_skills=["skill-b"]))
        graph.add_skill(SkillDefinition(name="skill-b", required_skills=["skill-a"]))

        with self.assertRaises(SkillGraphCycleError) as ctx:
            graph.resolve_plan(target="skill-a")
        self.assertIn("Cyclic dependency detected", str(ctx.exception))

    def test_three_node_cycle(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-a", required_skills=["skill-c"]))
        graph.add_skill(SkillDefinition(name="skill-b", required_skills=["skill-a"]))
        graph.add_skill(SkillDefinition(name="skill-c", required_skills=["skill-b"]))

        with self.assertRaises(SkillGraphCycleError) as ctx:
            graph.resolve_plan(target="skill-a")
        self.assertIn("Cyclic dependency detected", str(ctx.exception))

    def test_self_loop_cycle(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="self-skill", required_skills=["self-skill"]))

        with self.assertRaises(SkillGraphCycleError) as ctx:
            graph.resolve_plan(target="self-skill")
        self.assertIn("Cyclic dependency detected", str(ctx.exception))

    def test_delegation_and_requirement_mixed_cycle(self) -> None:
        graph = SkillGraph()
        graph.add_skill(
            SkillDefinition(
                name="parent",
                delegated_skills=["child"],
                required_skills=["grandchild"],
            )
        )
        graph.add_skill(SkillDefinition(name="child", delegated_skills=["grandchild"]))
        graph.add_skill(SkillDefinition(name="grandchild"))

        with self.assertRaises(SkillGraphCycleError) as ctx:
            graph.resolve_plan(target="parent")
        self.assertIn("Cyclic dependency detected", str(ctx.exception))


class TestPrerequisiteCheckLogic(unittest.TestCase):
    """Tests for pre-flight binary tool checking."""

    def test_prerequisite_binary_check_available(self) -> None:
        graph = SkillGraph()
        graph.add_skill(
            SkillDefinition(
                name="git-ops",
                prerequisites=["python"],
            )
        )

        res = graph.check_prerequisites(["git-ops"])
        self.assertIn("python", res)
        self.assertTrue(res["python"]["available"])
        self.assertIsNotNone(res["python"]["path"])
        self.assertEqual(res["python"]["required_by"], ["git-ops"])

    def test_prerequisite_binary_check_missing(self) -> None:
        graph = SkillGraph()
        graph.add_skill(
            SkillDefinition(
                name="custom-skill",
                prerequisites=["non_existent_tool_xyz_999"],
            )
        )

        res = graph.check_prerequisites(["custom-skill"])
        self.assertIn("non_existent_tool_xyz_999", res)
        self.assertFalse(res["non_existent_tool_xyz_999"]["available"])
        self.assertIsNone(res["non_existent_tool_xyz_999"]["path"])

    @patch("shutil.which")
    def test_plan_with_check_prereqs_flag(self, mock_which: Any) -> None:
        mock_which.side_effect = lambda tool: f"/usr/bin/{tool}" if tool == "git" else None

        graph = SkillGraph()
        graph.add_skill(
            SkillDefinition(
                name="skill-git",
                prerequisites=["git", "custom-missing-tool"],
            )
        )

        plan = graph.resolve_plan(target="skill-git", check_prereqs=True)
        self.assertIsNotNone(plan.prerequisites_check)
        self.assertTrue(plan.prerequisites_check["git"]["available"])
        self.assertFalse(plan.prerequisites_check["custom-missing-tool"]["available"])


class TestOnFailureLifecycleHandling(unittest.TestCase):
    """Tests for on_failure lifecycle policies and failure impact evaluation."""

    def test_default_failure_policy(self) -> None:
        skill = SkillDefinition(name="test-skill")
        self.assertEqual(skill.on_failure, "abort_and_rollback")

    def test_abort_and_rollback_simulation(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="step-1", on_failure="abort_and_rollback"))
        graph.add_skill(SkillDefinition(name="step-2", required_skills=["step-1"]))
        graph.add_skill(SkillDefinition(name="step-3", required_skills=["step-2"]))

        plan = graph.resolve_plan(target="step-3")
        forward_adj, _ = graph.build_adjacency(set(plan.topological_order))

        sim = plan.simulate_failure("step-1", adj=forward_adj)
        self.assertEqual(sim["action"], "abort_and_rollback")
        self.assertEqual(sim["status"], "failed_aborted")
        self.assertEqual(sorted(sim["aborted_skills"]), ["step-2", "step-3"])

    def test_fallback_degrade_simulation(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="diagram-render", on_failure="fallback_degrade"))
        graph.add_skill(SkillDefinition(name="report-assembly", required_skills=["diagram-render"]))

        plan = graph.resolve_plan(target="report-assembly")
        forward_adj, _ = graph.build_adjacency(set(plan.topological_order))

        sim = plan.simulate_failure("diagram-render", adj=forward_adj)
        self.assertEqual(sim["action"], "fallback_degrade")
        self.assertEqual(sim["status"], "degraded_continue")
        self.assertIn("report-assembly", sim["degraded_skills"])

    def test_continue_with_partial_simulation(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="telemetry-scan", on_failure="continue_with_partial"))
        graph.add_skill(SkillDefinition(name="main-workflow"))

        plan = graph.resolve_plan()
        sim = plan.simulate_failure("telemetry-scan")
        self.assertEqual(sim["action"], "continue_with_partial")
        self.assertEqual(sim["status"], "partial_continue")
        self.assertEqual(sim["partial_skills"], ["telemetry-scan"])

    def test_invalid_lifecycle_policy_error(self) -> None:
        yaml_content = """---
name: bad-policy-skill
description: Use when testing invalid policies.
owner_agent: router-maintenance
rank: high
isolation: mutate
on_failure: unsupported_policy
---
# Bad Policy
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "bad-policy-skill" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(yaml_content, encoding="utf-8")

            with self.assertRaises(InvalidLifecyclePolicyError):
                load_skill_from_file(skill_path)


class TestFrontmatterParsingAndValidation(unittest.TestCase):
    """Tests for Schema V2 frontmatter parsing, contracts, and error handling."""

    def test_schema_v2_full_frontmatter_parse(self) -> None:
        yaml_content = """---
schema_version: "2.0.0"
name: advanced-skill
description: Perform advanced task. Use when needed.
owner_agent: specialist-ops
rank: critical
isolation: mutate
on_failure: fallback_degrade
prerequisites:
  - git
  - ast-grep
dependencies:
  required_skills:
    - isolate-work
  delegated_skills:
    - code-review-report
  in_session_skills:
    - git-basics
contracts:
  inputs:
    type: object
    properties:
      branch: {type: string}
  outputs:
    task_id: string
    status: string
    artifacts: list
    handoff_requests: list
    metrics: dict
---
# Advanced Skill
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "advanced-skill" / "SKILL.md"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text(yaml_content, encoding="utf-8")

            skill = load_skill_from_file(skill_path)
            self.assertEqual(skill.name, "advanced-skill")
            self.assertEqual(skill.schema_version, "2.0.0")
            self.assertEqual(skill.rank, "critical")
            self.assertEqual(skill.isolation, "mutate")
            self.assertEqual(skill.on_failure, "fallback_degrade")
            self.assertEqual(skill.prerequisites, ["git", "ast-grep"])
            self.assertEqual(skill.required_skills, ["isolate-work"])
            self.assertEqual(skill.delegated_skills, ["code-review-report"])
            self.assertEqual(skill.in_session_skills, ["git-basics"])
            self.assertIn("inputs", skill.contracts)
            self.assertIn("outputs", skill.contracts)

    def test_missing_skill_dependency_error(self) -> None:
        graph = SkillGraph()
        graph.add_skill(
            SkillDefinition(
                name="broken-skill",
                required_skills=["non-existent-skill-xyz"],
            )
        )

        with self.assertRaises(MissingSkillDependencyError):
            graph.resolve_plan(target="broken-skill")

    def test_target_skill_not_found_error(self) -> None:
        graph = SkillGraph()
        with self.assertRaises(SkillNotFoundError):
            graph.resolve_plan(target="ghost-skill")

    def test_validate_catalog_clean(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="skill-1"))
        graph.add_skill(SkillDefinition(name="skill-2", required_skills=["skill-1"]))

        report = graph.validate_catalog(check_prereqs=False)
        self.assertTrue(report["ok"])
        self.assertEqual(len(report["errors"]), 0)

    def test_validate_catalog_with_broken_deps_and_cycle(self) -> None:
        graph = SkillGraph()
        graph.add_skill(SkillDefinition(name="a", required_skills=["b", "missing-target"]))
        graph.add_skill(SkillDefinition(name="b", required_skills=["a"]))

        report = graph.validate_catalog(check_prereqs=False)
        self.assertFalse(report["ok"])
        self.assertGreaterEqual(len(report["errors"]), 2)
        self.assertEqual(len(report["missing_dependencies"]), 1)
        self.assertGreaterEqual(len(report["cycles_detected"]), 1)


class TestRealRepoCatalogIntegrity(unittest.TestCase):
    """Verify that all skills in the actual repository catalog are valid and form a valid DAG."""

    def test_real_skills_catalog_validation(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        skills_dir = repo_root / "ai-tooling" / "skills"
        self.assertTrue(skills_dir.exists(), f"Skills directory not found at {skills_dir}")

        graph = SkillGraph.from_directory(skills_dir)
        self.assertGreater(len(graph.skills), 0, "Expected skills in repository")

        report = graph.validate_catalog(check_prereqs=False)
        self.assertTrue(
            report["ok"],
            f"Repository skills catalog validation failed: {report['errors']}",
        )

    def test_real_skills_all_plan_resolves(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        skills_dir = repo_root / "ai-tooling" / "skills"

        graph = SkillGraph.from_directory(skills_dir)
        plan = graph.resolve_plan(target="all")
        self.assertEqual(len(plan.topological_order), len(graph.skills))
        self.assertGreaterEqual(len(plan.stages), 1)


class TestCLIExecution(unittest.TestCase):
    """Test CLI main() entrypoint."""

    def test_cli_single_skill_json(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            ret = main(["--skill", "isolate-work", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(stdout.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["plan"]["target"], "isolate-work")

    def test_cli_validate_all_json(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            ret = main(["--validate-all", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(stdout.getvalue())
        self.assertTrue(data["ok"])
        self.assertGreater(data["total_skills"], 0)

    def test_cli_missing_args(self) -> None:
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            ret = main([])
        self.assertEqual(ret, 2)


if __name__ == "__main__":
    unittest.main()
