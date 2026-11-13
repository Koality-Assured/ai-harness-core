"""Unit tests for router structure validator results-layout check.

tags: [tests, docs, validation, results]
routing_hints: [tests, validate_router_structure, results-layout]

Run: python -m unittest scripts.tests.test_validate_router_structure -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "docs"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from validate_router_structure import (  # noqa: E402
    ALLOWED_RESULTS_FAMILIES,
    check_results_layout,
    check_supporting_subfolders,
)


def _seed_allowed_results(root: Path) -> Path:
    results = root / "results"
    results.mkdir()
    for name in ("AGENTS.md", "README.md", "results-conventions.md"):
        (results / name).write_text("# stub\n", encoding="utf-8")
    for family in ALLOWED_RESULTS_FAMILIES:
        family_dir = results / family
        family_dir.mkdir()
        (family_dir / ".gitkeep").write_text("", encoding="utf-8")
    reviews = results / "reviews"
    reviews.mkdir()
    (reviews / ".gitkeep").write_text("", encoding="utf-8")
    return results


class ResultsLayoutTests(unittest.TestCase):
    def test_allowed_layout_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_allowed_results(root)
            errors: list[str] = []
            check_results_layout(errors, root=root)
            self.assertEqual(errors, [])

    def test_missing_results_dir_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors: list[str] = []
            check_results_layout(errors, root=Path(tmp))
            self.assertTrue(any("missing results/" in e for e in errors))

    def test_unknown_top_level_dirs_fail(self) -> None:
        leftover = ("headroom-dry-run", "ast-grep-dry-run", "scaffolded-repos", "mystery")
        for name in leftover:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    results = _seed_allowed_results(root)
                    (results / name).mkdir()
                    errors: list[str] = []
                    check_results_layout(errors, root=root)
                    self.assertTrue(
                        any(f"results/{name}/" in e for e in errors),
                        errors,
                    )

    def test_unexpected_top_level_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = _seed_allowed_results(root)
            (results / "scratch-notes.md").write_text("nope\n", encoding="utf-8")
            errors: list[str] = []
            check_results_layout(errors, root=root)
            self.assertTrue(any("scratch-notes.md" in e for e in errors), errors)

    def test_reviews_gitkeep_only_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_allowed_results(root)
            errors: list[str] = []
            check_results_layout(errors, root=root)
            self.assertEqual(errors, [])

    def test_reviews_topic_run_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = _seed_allowed_results(root)
            topic = results / "reviews" / "harness-v2"
            topic.mkdir()
            (topic / "report.md").write_text("# review\n", encoding="utf-8")
            errors: list[str] = []
            check_results_layout(errors, root=root)
            self.assertTrue(
                any("results/reviews/harness-v2/" in e for e in errors),
                errors,
            )

    def test_does_not_walk_allowed_family_trees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = _seed_allowed_results(root)
            nested = results / "cost-layers" / "combined" / "2026-08-20"
            nested.mkdir(parents=True)
            (nested / "report.md").write_text("# ok\n", encoding="utf-8")
            errors: list[str] = []
            check_results_layout(errors, root=root)
            self.assertEqual(errors, [])


class SupportingSubfoldersTests(unittest.TestCase):
    def test_supporting_subfolders_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            supp = root / "supporting"
            supp.mkdir()
            sub1 = supp / "ast-grep"
            sub1.mkdir()
            (sub1 / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
            (sub1 / "README.md").write_text("# README\n", encoding="utf-8")

            # Hidden or underscore ignored
            hidden = supp / ".hidden"
            hidden.mkdir()
            underscore = supp / "_temp"
            underscore.mkdir()

            errors: list[str] = []
            check_supporting_subfolders(errors, root=root)
            self.assertEqual(errors, [])

    def test_missing_agents_md_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            supp = root / "supporting"
            supp.mkdir()
            sub = supp / "my-tool"
            sub.mkdir()
            (sub / "README.md").write_text("# README\n", encoding="utf-8")

            errors: list[str] = []
            check_supporting_subfolders(errors, root=root)
            self.assertTrue(any("my-tool/: missing required AGENTS.md" in e for e in errors), errors)

    def test_missing_readme_md_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            supp = root / "supporting"
            supp.mkdir()
            sub = supp / "my-tool"
            sub.mkdir()
            (sub / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")

            errors: list[str] = []
            check_supporting_subfolders(errors, root=root)
            self.assertTrue(any("my-tool/: missing required README.md" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
