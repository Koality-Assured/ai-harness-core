"""Unit tests for validate_context_budget.py.

tags: [tests, docs, validation, cost-layers]
routing_hints: [tests, validate_context_budget, context-budget, tokens]

Run: python -m unittest scripts.tests.test_validate_context_budget -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "docs"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from paths import REPO_ROOT  # noqa: E402
from validate_context_budget import (  # noqa: E402
    BUDGET_CEILINGS,
    NESTED_AGENTS_MAX_CHARS,
    check_context_budgets,
)


class ContextBudgetValidatorTests(unittest.TestCase):
    def test_repo_root_passes_all_budgets(self) -> None:
        ok, results, errors = check_context_budgets(REPO_ROOT)
        self.assertTrue(ok, f"Context budget checks failed with errors: {errors}")
        self.assertEqual(len(errors), 0)
        self.assertGreaterEqual(len(results), 20)

    def test_exceeded_root_budget_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create root AGENTS.md exceeding ceiling
            (root / "AGENTS.md").write_text("x" * (BUDGET_CEILINGS["AGENTS.md"] + 500), encoding="utf-8")
            (root / "routing").mkdir()
            (root / "routing" / "AGENTS.md").write_text("small", encoding="utf-8")
            (root / "routing" / "by-task.md").write_text("small", encoding="utf-8")
            (root / "routing" / "area-map.md").write_text("small", encoding="utf-8")

            ok, results, errors = check_context_budgets(root)
            self.assertFalse(ok)
            self.assertTrue(any("AGENTS.md exceeded budget" in e for e in errors))

    def test_exceeded_nested_delta_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("small", encoding="utf-8")
            (root / "routing").mkdir()
            (root / "routing" / "AGENTS.md").write_text("small", encoding="utf-8")
            (root / "routing" / "by-task.md").write_text("small", encoding="utf-8")
            (root / "routing" / "area-map.md").write_text("small", encoding="utf-8")

            # Create nested AGENTS.md exceeding delta ceiling
            nested_dir = root / "docs"
            nested_dir.mkdir()
            (nested_dir / "AGENTS.md").write_text("x" * (NESTED_AGENTS_MAX_CHARS + 200), encoding="utf-8")

            ok, results, errors = check_context_budgets(root)
            self.assertFalse(ok)
            self.assertTrue(any("exceeded delta budget" in e for e in errors))

    def test_nested_duplicating_root_header_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("small", encoding="utf-8")
            (root / "routing").mkdir()
            (root / "routing" / "AGENTS.md").write_text("small", encoding="utf-8")
            (root / "routing" / "by-task.md").write_text("small", encoding="utf-8")
            (root / "routing" / "area-map.md").write_text("small", encoding="utf-8")

            nested_dir = root / "docs"
            nested_dir.mkdir()
            (nested_dir / "AGENTS.md").write_text("# Repository AGENTS\n\nduplicate content", encoding="utf-8")

            ok, results, errors = check_context_budgets(root)
            self.assertFalse(ok)
            self.assertTrue(any("improperly duplicates root" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
