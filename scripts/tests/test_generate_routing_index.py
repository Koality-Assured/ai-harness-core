"""Unit tests for generate_routing_index.py.

tags: [tests, routing, index]
routing_hints: [tests, generate_routing_index, agent-dispatch, skill-dispatch, area-map]

Run: python -m unittest scripts.tests.test_generate_routing_index -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "routing"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from generate_routing_index import (  # noqa: E402
    collect_agent_rows,
    collect_skill_rows,
    render_area_map,
    write_agent_dispatch,
    write_area_map,
    write_skill_dispatch,
)
from paths import REPO_ROOT  # noqa: E402


class GenerateRoutingIndexTests(unittest.TestCase):
    def test_collect_agent_rows(self) -> None:
        rows = collect_agent_rows()
        self.assertGreaterEqual(len(rows), 20)
        agent_ids = {r["agent_id"] for r in rows}
        self.assertIn("router", agent_ids)
        self.assertIn("ai-tooling-ops", agent_ids)
        self.assertIn("detailed-activity", agent_ids)
        self.assertIn("documentation-ops", agent_ids)
        self.assertIn("git-fast-operator", agent_ids)
        self.assertIn("github-ops", agent_ids)

    def test_collect_skill_rows(self) -> None:
        rows = collect_skill_rows()
        self.assertGreaterEqual(len(rows), 60)
        skill_names = {r["name"] for r in rows}
        self.assertIn("isolate-work", skill_names)
        self.assertIn("antagonistic-review", skill_names)
        self.assertIn("git-basics", skill_names)

    def test_render_area_map(self) -> None:
        rendered = render_area_map(REPO_ROOT, now="2026-08-25T00:00:00Z")
        self.assertIn("# Area map", rendered)
        self.assertIn("docs/", rendered)
        self.assertIn("routing/", rendered)
        self.assertIn("ai-tooling/", rendered)

    def test_agent_dispatch_file_exists_and_valid(self) -> None:
        dispatch_file = REPO_ROOT / "routing" / "agent-dispatch.md"
        self.assertTrue(dispatch_file.exists(), "routing/agent-dispatch.md should exist")
        content = dispatch_file.read_text(encoding="utf-8")
        self.assertIn("# Agent dispatch (specialist catalogue)", content)
        self.assertIn("## Specialist agents", content)
        self.assertIn("## Capabilities and tool access", content)
        self.assertIn("`router`", content)


if __name__ == "__main__":
    unittest.main()
