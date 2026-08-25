"""Unit tests for 3-Tier Hybrid Dispatch Pipeline and Schema V2 Indexing.

tags: [tests, routing, ai-tooling]
routing_hints: [tests, hybrid-dispatch, bm25, ambiguity-gate, schema-v2]

Run: python -m unittest scripts/tests/test_hybrid_dispatch.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
_ROUTING = Path(__file__).resolve().parents[1] / "routing"
sys.path.insert(0, str(_LIB))
sys.path.insert(0, str(_ROUTING))

from hybrid_dispatch import (  # noqa: E402
    BM25Candidate,
    HybridDispatcher,
    Tier1FastPath,
    Tier2BM25,
    Tier3AmbiguityGate,
    dispatch_query,
    tokenize,
)
from md import load_skill_record, parse_frontmatter  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402


def _skill_md(name: str) -> Path:
    skills_dir = ROOT / "ai-tooling" / "skills"
    for p in skills_dir.rglob("SKILL.md"):
        if p.parent.name == name:
            return p
    return skills_dir / name / "SKILL.md"


class TestTier1FastPath(unittest.TestCase):
    """Unit tests for Tier 1 Fast-Path Regex & Keyword Matching (<1ms, 0 tokens)."""

    def setUp(self) -> None:
        self.tier1 = Tier1FastPath()

    def test_single_exact_matches(self) -> None:
        test_cases = [
            ("git status", "git-basics", "git-fast-operator"),
            ("git fetch and diff", "git-basics", "git-fast-operator"),
            ("spawn git worktree", "isolate-work", "router"),
            ("isolate-work", "isolate-work", "router"),
            ("isolate this mutating work in a worktree", "isolate-work", "router"),
            ("isolate the worktree", "isolate-work", "router"),
            ("qmd search docs", "qmd-usage", "qmd-ops"),
            ("qmd commands and retrieval", "qmd-usage", "qmd-ops"),
            ("run noir scan on api", "noir-scan", "artifact-agent"),
            ("render mermaid diagram", "mermaid-diagram", "artifact-agent"),
            ("ast-grep precision retrieval", "ast-grep", "router-maintenance"),
            ("headroom context compression", "headroom", "router-maintenance"),
            ("markdownlint fix md001", "markdownlint", "documentation-ops"),
            ("deep research into cloud models", "deep-research", "detailed-activity"),
            ("create memory checkpoint", "memory-create", "ai-tooling-ops"),
        ]
        for query, expected_skill, expected_owner in test_cases:
            res = self.tier1.evaluate(query)
            self.assertTrue(res.matched, f"Query '{query}' should match Tier 1")
            self.assertEqual(res.skill, expected_skill)
            self.assertEqual(res.owner_agent, expected_owner)
            self.assertEqual(res.confidence, 1.0)
            self.assertEqual(res.tier, 1)

    def test_no_match_returns_cleanly(self) -> None:
        res = self.tier1.evaluate("What is the capital of France and how is the weather?")
        self.assertFalse(res.matched)
        self.assertIsNone(res.skill)
        self.assertEqual(res.reason, "no_match")

    def test_isolate_work_fast_path_does_not_match_ordinary_english(self) -> None:
        for query in (
            "isolate this work item",
            "isolating work from the rest",
        ):
            res = self.tier1.evaluate(query)
            self.assertFalse(res.matched, f"Query '{query}' must not hit isolate-work Fast-Path")
            self.assertEqual(res.reason, "no_match")

    def test_med02_multi_intent_collision_avoids_overtriggering(self) -> None:
        """MED-02: Multi-intent requests spanning multiple skills must NOT over-trigger."""
        # Query matching both antagonistic review and anti-slop
        query = "Antagonistic review of the anti-slop report in docs/"
        res = self.tier1.evaluate(query)
        self.assertFalse(res.matched, "Multi-intent query must not match single skill in Tier 1")
        self.assertEqual(res.reason, "multi_intent_conflict")
        self.assertGreaterEqual(len(res.conflicting_skills), 2)
        self.assertIn("anti-slop", res.conflicting_skills)
        self.assertIn("antagonistic-review", res.conflicting_skills)

        # Another multi-intent query
        query2 = "Run noir scan and create mermaid diagram"
        res2 = self.tier1.evaluate(query2)
        self.assertFalse(res2.matched)
        self.assertEqual(res2.reason, "multi_intent_conflict")
        self.assertIn("noir-scan", res2.conflicting_skills)
        self.assertIn("mermaid-diagram", res2.conflicting_skills)


class TestTier2BM25(unittest.TestCase):
    """Unit tests for Tier 2 In-Memory BM25 Lexical / Semantic Index (~5ms, 0 tokens)."""

    def setUp(self) -> None:
        self.bm25 = Tier2BM25(root=ROOT)

    def test_tokenize_preserves_technical_terms(self) -> None:
        tokens = tokenize("Run git-basics and qmd search on docs/standards")
        self.assertIn("git-basics", tokens)
        self.assertIn("git", tokens)
        self.assertIn("basics", tokens)
        self.assertIn("qmd", tokens)
        self.assertIn("search", tokens)
        self.assertIn("docs", tokens)
        self.assertIn("standards", tokens)
        self.assertNotIn("and", tokens)
        self.assertNotIn("on", tokens)

    def test_bm25_semantic_ranking_skills(self) -> None:
        if not _skill_md("noir-scan").is_file():
            self.skipTest("noir-scan is instance-only; omitted from wiki template")
        # Query without exact fast-path keywords but matching skill purpose
        query = "discover shadow routes and attack surface parameters"
        res = self.bm25.search(query, top_k=3)
        self.assertTrue(len(res.candidates) > 0)
        top = res.candidates[0]
        self.assertEqual(top.name, "noir-scan")
        self.assertEqual(top.owner_agent, "artifact-agent")
        self.assertGreater(top.score, 0.0)
        self.assertGreater(top.confidence, 0.5)

    def test_bm25_ranking_cloud_logs(self) -> None:
        if not (_skill_md("aws-logs").is_file() or _skill_md("aws-read").is_file()):
            self.skipTest("aws-logs/aws-read are instance-only; omitted from wiki template")
        query = "inspect amazon cloudwatch log streams via oauth"
        res = self.bm25.search(query, top_k=3)
        self.assertTrue(len(res.candidates) > 0)
        top_names = [c.name for c in res.candidates]
        self.assertTrue("aws-logs" in top_names or "aws-read" in top_names)

    def test_bm25_empty_query(self) -> None:
        res = self.bm25.search("", top_k=3)
        self.assertFalse(res.matched)
        self.assertEqual(len(res.candidates), 0)


class TestTier3AmbiguityGate(unittest.TestCase):
    """Unit tests for Tier 3 Structured LLM Ambiguity Gate."""

    def setUp(self) -> None:
        self.gate = Tier3AmbiguityGate()

    def test_structured_payload_generation(self) -> None:
        candidates = [
            BM25Candidate(
                name="anti-slop",
                type="skill",
                owner_agent="artifact-agent",
                rank="high",
                isolation="mutate",
                score=18.5,
                confidence=1.0,
                matched_terms=["anti-slop", "slop"],
                description="Strips AI wording and design/UI slop from human-readable deliverables.",
            ),
            BM25Candidate(
                name="antagonistic-review",
                type="skill",
                owner_agent="detailed-activity",
                rank="high",
                isolation="mutate",
                score=12.3,
                confidence=0.66,
                matched_terms=["review"],
                description="Antagonistic review that ranks holes in plans, PRs, docs, commits, or designs.",
            ),
        ]
        res = self.gate.evaluate(
            query="Review the anti-slop report in docs/",
            candidates=candidates,
            conflicting_skills=["anti-slop", "antagonistic-review"],
        )
        self.assertEqual(res.tier, 3)
        self.assertEqual(res.status, "multi_intent")
        self.assertEqual(len(res.candidates), 2)
        self.assertEqual(len(res.disambiguation_questions), 2)
        self.assertIn("anti-slop", res.disambiguation_questions[0])
        self.assertIn("antagonistic-review", res.disambiguation_questions[1])
        self.assertEqual(res.recommended_action, "clarify_with_user")
        self.assertIn("User Query: Review the anti-slop report in docs/", res.llm_triage_prompt)


class TestHybridDispatcher(unittest.TestCase):
    """Unit tests for the integrated 3-tier hybrid dispatch pipeline."""

    def setUp(self) -> None:
        self.dispatcher = HybridDispatcher(root=ROOT)

    def test_dispatch_tier1_fast_path(self) -> None:
        res = self.dispatcher.dispatch("git status", tier="all")
        self.assertEqual(res.selected_tier, 1)
        self.assertEqual(res.final_target, "git-basics")
        self.assertEqual(res.owner_agent, "git-fast-operator")
        self.assertEqual(res.status, "dispatched")
        self.assertEqual(res.confidence, 1.0)

    def test_dispatch_tier2_bm25(self) -> None:
        # Tier 2 specific invocation
        res = self.dispatcher.dispatch("finding shadow endpoints and routes", tier="2")
        self.assertEqual(res.selected_tier, 2)
        self.assertIsNotNone(res.final_target)
        self.assertIsNotNone(res.tier2)

    def test_dispatch_tier3_multi_intent(self) -> None:
        # Multi-intent triggers Tier 3 ambiguity gate
        res = self.dispatcher.dispatch("Antagonistic review of the anti-slop report in docs/", tier="all")
        self.assertEqual(res.selected_tier, 3)
        self.assertIn(res.status, {"multi_intent", "ambiguous"})
        self.assertIsNotNone(res.tier3)
        self.assertGreater(len(res.tier3.disambiguation_questions), 0)

    def test_convenience_function(self) -> None:
        res_dict = dispatch_query("qmd search docs", tier="all", root=ROOT)
        self.assertIsInstance(res_dict, dict)
        self.assertEqual(res_dict["selected_tier"], 1)
        self.assertEqual(res_dict["final_target"], "qmd-usage")


class TestSchemaV2SkillParsing(unittest.TestCase):
    """Unit tests for Schema V2 metadata parsing and indexing."""

    def test_load_skill_record_v2_fields(self) -> None:
        threat_model_path = _skill_md("threat-model")
        skill_path = threat_model_path if threat_model_path.is_file() else _skill_md("isolate-work")
        rec = load_skill_record(skill_path)
        self.assertEqual(rec["name"], skill_path.parent.name)
        self.assertTrue(rec.get("owner_agent"))
        self.assertIn(rec.get("rank"), {"critical", "high", "medium", "low"})
        self.assertIn(rec.get("isolation"), {"mutate", "read-only", "none"})
        self.assertIn("on_failure", rec)
        self.assertIn("prerequisites", rec)
        self.assertIn("dependencies", rec)
        self.assertIn("contracts", rec)

    def test_parse_v2_frontmatter_synthetic(self) -> None:
        v2_raw = """---
schema_version: "2.0.0"
name: custom-composite
description: Third person WHAT. Use when testing DAGs.
owner_agent: router-maintenance
rank: high
isolation: mutate
on_failure: fallback_degrade
prerequisites:
  - git
  - python
  - qmd
dependencies:
  required_skills:
    - isolate-work
  delegated_skills:
    - code-review-report
  in_session_skills:
    - git-basics
contracts:
  inputs:
    target: string
  outputs:
    task_id: string
---

# Custom composite
## When to use
Testing DAGs.
"""
        fields, body = parse_frontmatter(v2_raw)
        self.assertEqual(fields.get("schema_version"), "2.0.0")
        self.assertEqual(fields.get("name"), "custom-composite")
        self.assertEqual(fields.get("on_failure"), "fallback_degrade")
        self.assertEqual(fields.get("prerequisites"), ["git", "python", "qmd"])
        self.assertEqual(
            fields.get("dependencies"),
            {
                "required_skills": ["isolate-work"],
                "delegated_skills": ["code-review-report"],
                "in_session_skills": ["git-basics"],
            },
        )


class TestCLIExecution(unittest.TestCase):
    """Unit tests for hybrid_dispatch CLI execution."""

    def test_cli_json_output(self) -> None:
        script = ROOT / "scripts" / "routing" / "hybrid_dispatch.py"
        proc = subprocess.run(
            [sys.executable, str(script), "--query", "git status", "--json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["selected_tier"], 1)
        self.assertEqual(data["final_target"], "git-basics")
        self.assertEqual(data["owner_agent"], "git-fast-operator")
        self.assertEqual(data["status"], "dispatched")

    def test_cli_multi_intent_json(self) -> None:
        script = ROOT / "scripts" / "routing" / "hybrid_dispatch.py"
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--query",
                "Antagonistic review of the anti-slop report in docs/",
                "--json",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertEqual(data["selected_tier"], 3)
        self.assertIn("tier3", data)
        self.assertGreater(len(data["tier3"]["disambiguation_questions"]), 0)


if __name__ == "__main__":
    unittest.main()
