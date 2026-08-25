"""Unit tests for Schema V2 agent validation.

tags: [tests, ai-tooling, agents, schema-v2]
routing_hints: [tests, validate-agent, agents]

Run: python -m unittest scripts.tests.test_validate_agent -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "ai-tooling"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from md import agent_ids, agent_paths  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402
from validate_agent import check_agent, extract_frontmatter_and_body, main  # noqa: E402


class ValidateAgentUnitTests(unittest.TestCase):
    def test_extract_frontmatter_valid(self) -> None:
        raw = """---
schema_version: "2.0.0"
agent_id: test-agent
name: Test Agent
---
# Title
Body text.
"""
        data, body, err = extract_frontmatter_and_body(raw)
        self.assertIsNone(err)
        self.assertIsNotNone(data)
        self.assertEqual(data.get("schema_version"), "2.0.0")
        self.assertEqual(data.get("agent_id"), "test-agent")
        self.assertIn("# Title", body)

    def test_extract_frontmatter_preserves_nested_schema_without_pyyaml(self) -> None:
        raw = """---
schema_version: 2.0.0
description: >-
  First line.
  Second line.
contracts:
  inputs:
    properties:
      request:
        description: Nested description must not replace the skill description
  outputs:
    result: string
---
# Title
"""
        data, _, err = extract_frontmatter_and_body(raw)
        self.assertIsNone(err)
        self.assertEqual(data.get("description"), "First line. Second line.")
        self.assertEqual(data["contracts"]["inputs"]["properties"]["request"]["description"], "Nested description must not replace the skill description")

    def test_extract_frontmatter_missing(self) -> None:
        raw = "# No frontmatter"
        data, body, err = extract_frontmatter_and_body(raw)
        self.assertIsNotNone(err)
        self.assertIsNone(data)

    def test_check_agent_passes_all_repo_agents(self) -> None:
        known = agent_ids(ROOT)
        self.assertGreater(len(known), 0, f"expected agents, got {len(known)}")
        fed = (ROOT / "ai-tooling" / "agents" / "cloud-operator" / "AGENT.md").is_file()
        if fed:
            self.assertGreaterEqual(
                len(known), 14, f"expected at least 14 agents in fed catalog, got {len(known)}"
            )
        for path in agent_paths(ROOT):
            errs = check_agent(path, known)
            self.assertEqual(errs, [], f"Agent {path.parent.name} failed: {errs}")

    def test_check_agent_catches_invalid_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_dir = Path(tmp) / "bad-agent"
            agent_dir.mkdir()
            agent_file = agent_dir / "AGENT.md"

            # Missing required fields
            bad_content = """---
schema_version: "1.0.0"
agent_id: wrong-id
---
# Bad Agent
Missing required headings.
"""
            agent_file.write_text(bad_content, encoding="utf-8")
            errs = check_agent(agent_file, {"bad-agent"})
            self.assertTrue(any("schema_version" in e for e in errs))
            self.assertTrue(any("agent_id" in e for e in errs))
            self.assertTrue(any("token_ceiling" in e for e in errs))
            self.assertTrue(any("capabilities" in e for e in errs))
            self.assertTrue(any("contracts" in e for e in errs))
            self.assertTrue(any("Critical cost layers" in e for e in errs))

    def test_cli_all_and_json(self) -> None:
        ret = main(["--all", "--json"])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
