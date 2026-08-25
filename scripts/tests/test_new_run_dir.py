"""Unit tests for results run-directory scaffold.

tags: [tests, results]
routing_hints: [tests, new_run_dir, families]

Run: python -m unittest scripts.tests.test_new_run_dir -v
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "results"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from new_run_dir import FAMILIES, TYPE_REQUIRED, build_rel, main  # noqa: E402


class NewRunDirTests(unittest.TestCase):
    def test_reviews_not_in_families(self) -> None:
        self.assertNotIn("reviews", FAMILIES)
        for family in (
            "research",
            "diagrams",
            "threat-model",
            "reports",
            "as-code",
            "cost-layers",
        ):
            self.assertIn(family, FAMILIES)

    def test_reviews_cli_rejected(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                main(["--family", "reviews", "--topic", "sample-topic", "--dry-run"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("reviews", stderr.getvalue())

    def test_allowed_families_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for family in FAMILIES:
                extra = ["--type", "executive"] if family in TYPE_REQUIRED else []
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    ret = main(
                        [
                            "--family",
                            family,
                            "--topic",
                            "sample-topic",
                            "--date",
                            "2026-08-25",
                            "--dry-run",
                            "--repo-root",
                            tmp,
                            *extra,
                        ]
                    )
                self.assertEqual(ret, 0, family)
                printed = stdout.getvalue().strip()
                self.assertTrue(printed.startswith(f"results/{family}/"), printed)
                self.assertIn("sample-topic/2026-08-25", printed)

    def test_build_rel_typed_family(self) -> None:
        rel = build_rel(
            family="reports",
            topic="quarterly-status",
            date="2026-08-25",
            type_seg="executive",
        )
        self.assertEqual(
            rel.as_posix(),
            "results/reports/executive/quarterly-status/2026-08-25",
        )


if __name__ == "__main__":
    unittest.main()
