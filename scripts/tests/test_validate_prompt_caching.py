"""Unit tests for validate_prompt_caching.py prompt KV-cache invariance linter.

tags: [tests, cost-layers, prompt-caching]
routing_hints: [tests, prompt-caching, invariance]
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "cost-layers"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from validate_prompt_caching import check_prompt_head, validate_all_prompts  # noqa: E402


class TestValidatePromptCaching(unittest.TestCase):
    def test_clean_prompt_passes(self) -> None:
        clean_text = """---
name: sample-agent
description: Sample agent definition.
last_verified: '2026-08-25'
---

# Sample Agent

You are a deterministic coding assistant. Follow strict repository guidelines.
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "AGENT.md"
            f.write_text(clean_text, encoding="utf-8")
            violations = check_prompt_head(f, clean_text)
            self.assertEqual(len(violations), 0)

    def test_volatile_timestamp_detected(self) -> None:
        dirty_text = """---
name: sample-agent
---

# Dynamic Agent
Current time: 2026-08-31T10:49:12Z
You are an assistant.
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "AGENT.md"
            f.write_text(dirty_text, encoding="utf-8")
            violations = check_prompt_head(f, dirty_text)
            self.assertTrue(len(violations) >= 1)
            violation_types = [v["violation"] for v in violations]
            self.assertTrue(any("timestamp" in vt.lower() for vt in violation_types))

    def test_user_path_detected(self) -> None:
        dirty_text = """---
name: sample-agent
---

System working directory: C:\\Users\\developer\\code\\repo
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "AGENT.md"
            f.write_text(dirty_text, encoding="utf-8")
            violations = check_prompt_head(f, dirty_text)
            self.assertTrue(len(violations) >= 1)
            violation_types = [v["violation"] for v in violations]
            self.assertTrue(any("user-specific" in vt.lower() for vt in violation_types))


if __name__ == "__main__":
    unittest.main()
