"""Unit tests for the non-mutating qmd lifecycle preflight.

tags: [tests, qmd]
routing_hints: [qmd, preflight, onboarding]
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_QMD = Path(__file__).resolve().parents[1] / "qmd"
sys.path.insert(0, str(_QMD))

import qmd_preflight  # noqa: E402
import refresh_qmd_index  # noqa: E402
import setup_qmd_collections  # noqa: E402


class QmdPreflightTests(unittest.TestCase):
    def test_candidate_paths_honor_cache_override_without_duplicates(self) -> None:
        paths = qmd_preflight.candidate_index_paths(
            environ={"QMD_CACHE_DIR": "C:/cache/qmd", "XDG_CACHE_HOME": "C:/cache"},
            home=Path("C:/home/developer"),
            repo_root=Path("C:/repo"),
        )
        self.assertEqual(paths[0], Path("C:/repo/.qmd/index.sqlite"))
        self.assertEqual(paths[1], Path("C:/cache/qmd/index.sqlite"))
        self.assertEqual(len(paths), len(set(paths)))

    def test_config_candidates_prioritizes_repo_local(self) -> None:
        paths = qmd_preflight.config_candidates(
            environ={"XDG_CONFIG_HOME": "C:/config"},
            home=Path("C:/home/developer"),
            repo_root=Path("C:/repo"),
        )
        self.assertEqual(paths[0], Path("C:/repo/.qmd/index.yml"))
        self.assertEqual(paths[1], Path("C:/repo/.qmd/index.yaml"))
        self.assertEqual(len(paths), len(set(paths)))

    def test_dynamic_collection_resolution_from_areas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            routing_dir = tmp_root / "routing"
            routing_dir.mkdir()
            areas_yaml = routing_dir / "areas.yaml"
            areas_yaml.write_text(
                "areas:\n"
                "  - id: custom-docs\n"
                "    purpose: Custom documentation area\n"
                "  - id: scratch\n"
                "    purpose: Temp workspace\n"
                "  - id: archive\n"
                "    purpose: Archived items\n"
                "    load: never\n",
                encoding="utf-8",
            )
            colls = setup_qmd_collections.resolve_collections(tmp_root)
            self.assertEqual(len(colls), 1)
            self.assertEqual(colls[0], ("custom-docs", "custom-docs", "Custom documentation area"))

    def test_local_qmd_config_generation_uses_relative_paths(self) -> None:
        colls = [("docs", "docs", "Decisions and standards"), ("routing", "routing", "Area maps")]
        config = setup_qmd_collections.generate_local_qmd_config(colls)
        self.assertIn("docs", config["collections"])
        self.assertEqual(config["collections"]["docs"]["path"], "docs")
        self.assertEqual(config["collections"]["docs"]["ignore"], ["**/README.md"])
        self.assertEqual(config["collections"]["docs"]["context"][""], "Decisions and standards")

    def test_index_observations_only_stat_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            present = Path(tmp) / "index.sqlite"
            present.write_bytes(b"sqlite placeholder")
            observations = qmd_preflight.index_observations([present, Path(tmp) / "missing.sqlite"])
        self.assertTrue(observations[0]["exists"])
        self.assertEqual(observations[0]["bytes"], 18)
        self.assertFalse(observations[1]["exists"])

    def test_classification_distinguishes_reuse_inaccessible_and_missing(self) -> None:
        indexes = [{"path": "index.sqlite", "exists": True, "bytes": 1, "readable": True}]
        self.assertEqual(
            qmd_preflight.classify(indexes=indexes, qmd="qmd", probe={"ok": True}),
            "healthy_reusable",
        )
        self.assertEqual(
            qmd_preflight.classify(
                indexes=indexes,
                qmd="qmd",
                probe={"ok": False, "diagnostic_tail": "SqliteError: unable to open database file"},
            ),
            "inaccessible_sandbox_or_permissions",
        )
        self.assertEqual(qmd_preflight.classify(indexes=[], qmd="qmd", probe=None), "missing")

    def test_hook_inspection_reports_lines_not_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "index.yml"
            config.write_text("collections: {}\nhooks:\n  after: redact-me\n", encoding="utf-8")
            result = qmd_preflight.inspect_qmd_hooks([config])
        self.assertEqual(result["potential_hooks"], [str(config)])
        self.assertEqual(result["config"][0]["hook_lines"], [2])
        self.assertNotIn("redact-me", str(result))

    def test_config_access_error_is_not_treated_as_reusable(self) -> None:
        indexes = [{"path": "index.sqlite", "exists": True, "bytes": 1, "readable": True}]
        self.assertEqual(
            qmd_preflight.classify(indexes=indexes, qmd="qmd", probe=None, config_errors=True),
            "inaccessible_sandbox_or_permissions",
        )

    def test_default_report_never_probes_or_mutates(self) -> None:
        with patch.object(qmd_preflight, "resolve_qmd", return_value="qmd") as resolver, patch.object(
            qmd_preflight, "probe_status"
        ) as probe:
            report = qmd_preflight.build_report(probe_cli=False, inspect_hooks=False, timeout=1)
        resolver.assert_called_once()
        probe.assert_not_called()
        self.assertEqual(report["mutating_commands_run"], [])

    def test_setup_requires_explicit_approval_before_any_qmd_call(self) -> None:
        with patch.object(setup_qmd_collections, "resolve_qmd") as resolve:
            rc = setup_qmd_collections.main(["--apply"])
        self.assertEqual(rc, 1)
        resolve.assert_not_called()

    def test_refresh_requires_approval_unless_dry_run(self) -> None:
        with patch.object(refresh_qmd_index, "resolve_qmd") as resolve:
            rc = refresh_qmd_index.main([])
        self.assertEqual(rc, 1)
        resolve.assert_not_called()

    def test_refresh_dry_run_never_calls_update_or_embed(self) -> None:
        with patch.object(refresh_qmd_index, "resolve_qmd", return_value="qmd"), patch.object(
            refresh_qmd_index, "run"
        ) as run:
            rc = refresh_qmd_index.main(["--dry-run"])
        self.assertEqual(rc, 0)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(call.kwargs["dry_run"] for call in run.call_args_list))


if __name__ == "__main__":
    unittest.main()
