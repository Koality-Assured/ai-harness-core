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

from validate_agent import check_agent, extract_frontmatter_and_body  # noqa: E402


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

    def test_extract_frontmatter_missing(self) -> None:
        raw = "# No frontmatter"
        data, body, err = extract_frontmatter_and_body(raw)
        self.assertIsNotNone(err)
        self.assertIsNone(data)

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


if __name__ == "__main__":
    unittest.main()
