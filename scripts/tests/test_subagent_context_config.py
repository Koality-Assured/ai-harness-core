"""Unit tests for cross-host subagent context isolation and project-level settings.

tags: [tests, subagents, context, config]
routing_hints: [tests, subagents, context-isolation, host-config]

Run: python -m unittest scripts.tests.test_subagent_context_config -v
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


class TestSubagentContextConfig(unittest.TestCase):
    """Tests validating multi-host context isolation settings and project files."""

    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_harness_config_subagents(self) -> None:
        """Verify config/harness.config.json contains valid subagent settings."""
        config_path = self.repo_root / "config" / "harness.config.json"
        self.assertTrue(config_path.is_file(), "config/harness.config.json must exist")

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.assertIn("subagents", cfg, "harness.config.json must have 'subagents' section")
        subagents = cfg["subagents"]
        self.assertTrue(subagents.get("isolate_parent_context"), "isolate_parent_context must be True")
        self.assertTrue(subagents.get("clean_slate_required"), "clean_slate_required must be True")
        self.assertTrue(
            subagents.get("prohibit_transcript_forwarding"), "prohibit_transcript_forwarding must be True"
        )
        self.assertTrue(
            subagents.get("enforce_selective_retrieval"), "enforce_selective_retrieval must be True"
        )

        host_adapters = subagents.get("host_adapters", {})
        self.assertIn("claude", host_adapters)
        self.assertIn("cursor", host_adapters)
        self.assertIn("openai_copilot", host_adapters)
        self.assertIn("antigravity", host_adapters)

    def test_cursor_config(self) -> None:
        """Verify .cursorignore and .cursor/rules/context-boundaries.mdc exist and enforce boundaries."""
        cursorignore_path = self.repo_root / ".cursorignore"
        self.assertTrue(cursorignore_path.is_file(), ".cursorignore must exist")
        cursorignore_content = cursorignore_path.read_text(encoding="utf-8")
        self.assertIn("scratch/**", cursorignore_content)
        self.assertIn(".cache/", cursorignore_content)

        rule_path = self.repo_root / ".cursor" / "rules" / "context-boundaries.mdc"
        self.assertTrue(rule_path.is_file(), ".cursor/rules/context-boundaries.mdc must exist")
        rule_content = rule_path.read_text(encoding="utf-8")
        self.assertIn("alwaysApply: true", rule_content)
        self.assertIn("Clean-Slate Subagent Execution", rule_content)
        self.assertIn("No Conversation History Carryover", rule_content)

    def test_claude_config(self) -> None:
        """Verify CLAUDE.md and .claude/settings.json exist and configure isolation."""
        claude_md_path = self.repo_root / "CLAUDE.md"
        self.assertTrue(claude_md_path.is_file(), "CLAUDE.md must exist")
        claude_md_content = claude_md_path.read_text(encoding="utf-8")
        self.assertIn("Clean-Slate Subagent Spawning", claude_md_content)
        self.assertIn("Prompt Caching Compliance", claude_md_content)

        settings_path = self.repo_root / ".claude" / "settings.json"
        self.assertTrue(settings_path.is_file(), ".claude/settings.json must exist")
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        subagents_cfg = settings.get("subagents", {})
        self.assertTrue(subagents_cfg.get("isolated_context"))
        self.assertFalse(subagents_cfg.get("inherit_conversation_history"))
        self.assertTrue(subagents_cfg.get("enforce_clean_slate"))

    def test_openai_copilot_config(self) -> None:
        """Verify .github/copilot-instructions.md and path instructions exist."""
        copilot_path = self.repo_root / ".github" / "copilot-instructions.md"
        self.assertTrue(copilot_path.is_file(), ".github/copilot-instructions.md must exist")
        copilot_content = copilot_path.read_text(encoding="utf-8")
        self.assertIn("Subagent Context Isolation", copilot_content)
        self.assertIn("No Transcript Bleed", copilot_content)

        instructions_path = self.repo_root / ".github" / "instructions" / "subagents.instructions.md"
        self.assertTrue(instructions_path.is_file(), "subagents.instructions.md must exist")
        instructions_content = instructions_path.read_text(encoding="utf-8")
        self.assertIn("clean-slate context", instructions_content)

    def test_gemini_antigravity_config(self) -> None:
        """Verify GEMINI.md exists and sets subagent directives."""
        gemini_path = self.repo_root / "GEMINI.md"
        self.assertTrue(gemini_path.is_file(), "GEMINI.md must exist")
        gemini_content = gemini_path.read_text(encoding="utf-8")
        self.assertIn("invoke_subagent", gemini_content)
        self.assertIn("isolated context windows with clean state", gemini_content)
        self.assertIn("Progressive Disclosure", gemini_content)


if __name__ == "__main__":
    unittest.main()
