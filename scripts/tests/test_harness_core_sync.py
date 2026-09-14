"""Tests for core-spoke harness protocol scripts.

tags: [tests, sync, harness]
routing_hints: [tests, scaffold-harness, pull-harness-core, propose-core-update]

Run: python -m unittest scripts.tests.test_harness_core_sync -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SYNC = Path(__file__).resolve().parents[1] / "sync"
if str(_SYNC) not in sys.path:
    sys.path.insert(0, str(_SYNC))

from io import StringIO
from unittest.mock import patch

from _harness_core_protocol import (
    CORE_REMOTE_NAME,
    ORIGIN_REMOTE_NAME,
    classify_spoke_path,
    copy_tree_filtered,
    default_visibility,
    detect_instance_leakage,
    domain_overlay_files,
    is_allowlisted_core_path,
    is_domain_marker,
    may_copy_core_source_rel,
)
from _harness_template import (
    HARNESS_TEMPLATE_DEST_EXCLUDE_RELS,
    HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES,
    HARNESS_TEMPLATE_DROP_SKILL_FAMILIES,
    HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES,
    HARNESS_TEMPLATE_SKILL_FAMILIES,
    SKILL_FAMILIES,
    harness_template_prune_dest_leftovers,
    is_harness_template_rel_kept,
    skill_is_kept,
)
from propose_core_update import DomainPathRefused, SpokePrRefused, propose_core_update
from pull_harness_core import main as pull_main
from pull_harness_core import pull_harness_core
from scaffold_harness import main as scaffold_main
from scaffold_harness import scaffold_harness


def _git(cwd: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "git failed")


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.email", "dev@example.com")
    _git(path, "config", "user.name", "Dev")
    _git(path, "config", "commit.gpgsign", "false")
    _git(path, "config", "core.autocrlf", "false")


def _commit(path: Path, message: str) -> None:
    _git(path, "add", "-A")
    _git(path, "commit", "-m", message)


def _mini_core(root: Path) -> None:
    (root / ".harness").mkdir(parents=True, exist_ok=True)
    (root / ".harness" / "__init__.py").write_text('"""core"""\n', encoding="utf-8")
    (root / "AGENTS.md").write_text("# Core AGENTS\n", encoding="utf-8")
    (root / "docs" / "standards").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "standards" / "harness-template.md").write_text(
        "# Harness template\n", encoding="utf-8"
    )
    scripts = root / "scripts" / "sync"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "pull_harness_core.py").write_text(
        '"""tags: [sync]\\npull stub"""\n', encoding="utf-8"
    )


class SkillFamilyCouplingTests(unittest.TestCase):
    def test_template_families_omit_vendor_and_workplace(self) -> None:
        leftover = {"aws", "azure", "gcp", "slack", "confluence", "google"}
        self.assertTrue(leftover.isdisjoint(SKILL_FAMILIES))
        self.assertTrue(leftover.isdisjoint(HARNESS_TEMPLATE_SKILL_FAMILIES))
        self.assertTrue(leftover <= HARNESS_TEMPLATE_DROP_SKILL_FAMILIES)
        self.assertIn("reporting", HARNESS_TEMPLATE_SKILL_FAMILIES)
        self.assertEqual(SKILL_FAMILIES, HARNESS_TEMPLATE_SKILL_FAMILIES)

    def test_protocol_scripts_are_template_kept(self) -> None:
        for rel in (
            "scripts/sync/scaffold_harness.py",
            "scripts/sync/pull_harness_core.py",
            "scripts/sync/propose_core_update.py",
            "scripts/sync/_harness_core_protocol.py",
            "scripts/tests/test_harness_core_sync.py",
        ):
            self.assertTrue(is_harness_template_rel_kept(rel), rel)

    def test_domain_marker_not_core(self) -> None:
        self.assertTrue(is_domain_marker(".harness/domain.json"))
        self.assertFalse(is_allowlisted_core_path(".harness/domain.json"))
        self.assertEqual(classify_spoke_path("docs/standards/legal-overlay.md"), "domain")
        self.assertEqual(classify_spoke_path("AGENTS.md"), "core")
        self.assertFalse(is_harness_template_rel_kept("ai-tooling/skills/aws/aws-read/SKILL.md"))
        self.assertFalse(is_harness_template_rel_kept("ai-tooling/skills/slack/slack-message/SKILL.md"))
        self.assertFalse(skill_is_kept("slack-message"))
        self.assertFalse(skill_is_kept("google-workspace-admin"))
        self.assertFalse(is_harness_template_rel_kept("references/financial/sox.md"))
        self.assertFalse(is_harness_template_rel_kept("scripts/tests/test_windows_security.py"))
        self.assertFalse(is_harness_template_rel_kept("scripts/tests/test_network_discovery.py"))
        self.assertIn(
            "scripts/tests/test_network_discovery.py",
            HARNESS_TEMPLATE_DEST_EXCLUDE_RELS,
        )
        self.assertTrue(
            {"financial", "windows-security", "cis-controls"}
            <= HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES
        )
        self.assertTrue(
            HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES.isdisjoint(
                HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES
            )
        )


    def test_prune_drops_leftover_vendor_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            aws = dest / "ai-tooling" / "skills" / "aws" / "aws-read"
            aws.mkdir(parents=True)
            (aws / "SKILL.md").write_text("# leftover aws\n", encoding="utf-8")
            meta = dest / "ai-tooling" / "skills" / "meta" / "isolate-work"
            meta.mkdir(parents=True)
            (meta / "SKILL.md").write_text("# isolate\n", encoding="utf-8")
            pruned = harness_template_prune_dest_leftovers(dest)
            self.assertFalse((dest / "ai-tooling" / "skills" / "aws").exists())
            self.assertTrue((dest / "ai-tooling" / "skills" / "meta" / "isolate-work").exists())
            self.assertTrue(any("aws" in item for item in pruned))

    def test_prune_drops_orphan_network_discovery_test(self) -> None:
        rel = "scripts/tests/test_network_discovery.py"
        self.assertIn(rel, HARNESS_TEMPLATE_DEST_EXCLUDE_RELS)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            orphan = dest / rel
            orphan.parent.mkdir(parents=True)
            orphan.write_text(
                "from scripts.network.discover_network import discover\n",
                encoding="utf-8",
            )
            keeper = dest / "scripts" / "tests" / "test_harness_core_sync.py"
            keeper.write_text("# keep\n", encoding="utf-8")
            pruned = harness_template_prune_dest_leftovers(dest)
            self.assertFalse(orphan.exists())
            self.assertTrue(keeper.exists())
            self.assertIn(rel, pruned)


class ScaffoldHarnessTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "legal-router"
            payload = scaffold_harness(
                name="legal-router",
                target=target,
                domain="legal",
                visibility="public",
                dry_run=True,
            )
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["pushed"])
            self.assertEqual(payload["visibility"], "public")
            self.assertIn(".harness/domain.json", payload["overlay_files"])
            self.assertIn("docs/standards/legal-overlay.md", payload["overlay_files"])
            self.assertFalse(target.exists())

    def test_private_visibility_is_first_class(self) -> None:
        self.assertEqual(default_visibility("game-dev", None), "private")
        self.assertEqual(default_visibility("legal", "private"), "private")
        payload = scaffold_harness(
            name="game-dev-router",
            target=Path("unused"),
            domain="game-dev",
            dry_run=True,
        )
        self.assertEqual(payload["visibility"], "private")
        self.assertTrue(payload["remotes"][ORIGIN_REMOTE_NAME].endswith("game-dev-router.git"))
        self.assertIn("ai-harness-core.git", payload["remotes"][CORE_REMOTE_NAME])

    def test_live_path_source_writes_overlays_and_remotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            _mini_core(core)
            target = Path(tmp) / "ui-ux-router"
            payload = scaffold_harness(
                name="ui-ux-router",
                target=target,
                domain="ui-ux",
                visibility="public",
                core_source="path",
                core_path=core,
                dry_run=False,
            )
            self.assertTrue(payload["ok"])
            self.assertTrue((target / "AGENTS.md").exists())
            self.assertTrue((target / ".harness" / "domain.json").exists())
            overlay = (target / "docs" / "standards" / "ui-ux-overlay.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("ui-ux", overlay)
            marker = json.loads((target / ".harness" / "domain.json").read_text(encoding="utf-8"))
            self.assertEqual(marker["visibility"], "public")
            self.assertEqual(marker["domain"], "ui-ux")
            remotes = subprocess.run(
                ["git", "remote", "-v"],
                cwd=target,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            self.assertIn("origin", remotes)
            self.assertIn("harness-core", remotes)
            self.assertIn("ui-ux-router.git", remotes)
            self.assertIn("ai-harness-core.git", remotes)
            self.assertEqual(detect_instance_leakage(target), [])
            self.assertFalse((target / "projects" / "secpanic").exists())
            self.assertIn("initial-commit", payload["actions"])
            self.assertTrue(payload["committed"])
            self.assertFalse(payload["pushed"])
            head = subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(head.returncode, 0)

    def test_refuses_instance_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "instance"
            _mini_core(core)
            owasp = core / "references" / "owasp"
            owasp.mkdir(parents=True)
            (owasp / "asvs.md").write_text("# owasp\n", encoding="utf-8")
            target = Path(tmp) / "legal-router"
            with self.assertRaises(ValueError) as ctx:
                scaffold_harness(
                    name="legal-router",
                    target=target,
                    domain="legal",
                    core_source="path",
                    core_path=core,
                    dry_run=False,
                )
            self.assertIn("fed-instance", str(ctx.exception).lower())
            self.assertFalse(target.exists())

    def test_path_source_filters_non_kept_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            dest = Path(tmp) / "dest"
            _mini_core(src)
            (src / "NOTES.txt").write_text("not template\n", encoding="utf-8")
            owasp = src / "references" / "owasp"
            owasp.mkdir(parents=True)
            (owasp / "asvs.md").write_text("# owasp\n", encoding="utf-8")
            copied = copy_tree_filtered(src, dest, dry_run=False)
            self.assertGreater(copied, 0)
            self.assertTrue((dest / "AGENTS.md").exists())
            self.assertFalse((dest / "NOTES.txt").exists())
            self.assertFalse((dest / "references" / "owasp").exists())
            self.assertFalse(may_copy_core_source_rel("references/owasp/asvs.md"))
            self.assertFalse(may_copy_core_source_rel("NOTES.txt"))

    def test_cli_json_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = StringIO()
            with patch("sys.stdout", buf):
                code = scaffold_main(
                    [
                        "--name",
                        "legal-router",
                        "--target",
                        str(Path(tmp) / "legal-router"),
                        "--domain",
                        "legal",
                        "--visibility",
                        "public",
                        "--dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["pushed"])


class ProposeCoreUpdateTests(unittest.TestCase):
    def test_refuses_domain_overlay_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            with self.assertRaises(DomainPathRefused):
                propose_core_update(
                    spoke=spoke,
                    paths=["docs/standards/legal-overlay.md", "AGENTS.md"],
                    dry_run=True,
                )

    def test_refuses_vendor_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            with self.assertRaises(DomainPathRefused):
                propose_core_update(
                    spoke=spoke,
                    paths=["ai-tooling/skills/aws/aws-read/SKILL.md"],
                    dry_run=True,
                )

    def test_allowlisted_core_path_plan_never_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            payload = propose_core_update(
                spoke=spoke,
                paths=["AGENTS.md", "scripts/sync/pull_harness_core.py"],
                dry_run=True,
            )
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["merged"])
            self.assertFalse(payload["pushed"])
            self.assertIn("AGENTS.md", payload["paths"])

    def test_create_pr_always_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            with self.assertRaises(SpokePrRefused) as ctx:
                propose_core_update(
                    spoke=spoke,
                    paths=["AGENTS.md"],
                    create_pr=True,
                    dry_run=True,
                )
            self.assertIn("spoke", str(ctx.exception).lower())

    def test_create_pr_refused_without_visibility_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            with self.assertRaises(SpokePrRefused):
                propose_core_update(
                    spoke=spoke,
                    paths=["AGENTS.md"],
                    create_pr=True,
                    dry_run=False,
                )

    def test_private_spoke_refuses_create_pr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            marker_dir = spoke / ".harness"
            marker_dir.mkdir()
            (marker_dir / "domain.json").write_text(
                json.dumps(
                    {
                        "domain": "game-dev",
                        "visibility": "private",
                        "name": "game-dev-router",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SpokePrRefused) as ctx:
                propose_core_update(
                    spoke=spoke,
                    paths=["AGENTS.md"],
                    create_pr=True,
                    dry_run=True,
                )
            self.assertIn("spoke", str(ctx.exception).lower())

    def test_create_issue_scans_full_dirty_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp)
            _init_repo(spoke)
            (spoke / "AGENTS.md").write_text("# core\n", encoding="utf-8")
            (spoke / "docs" / "standards").mkdir(parents=True)
            (spoke / "docs" / "standards" / "legal-overlay.md").write_text(
                "# domain\n", encoding="utf-8"
            )
            with self.assertRaises(DomainPathRefused) as ctx:
                propose_core_update(
                    spoke=spoke,
                    paths=["AGENTS.md"],
                    create_issue=True,
                    dry_run=True,
                )
            self.assertIn("legal-overlay", str(ctx.exception))


class PullHarnessCoreTests(unittest.TestCase):
    def test_dry_run_and_live_branch_never_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            spoke = Path(tmp) / "spoke"
            _init_repo(core)
            (core / "AGENTS.md").write_text("# core v1\n", encoding="utf-8")
            (core / "docs" / "standards").mkdir(parents=True)
            (core / "docs" / "standards" / "legal-overlay.md").write_text(
                "# domain leftover\n", encoding="utf-8"
            )
            _commit(core, "core v1")

            _init_repo(spoke)
            (spoke / "AGENTS.md").write_text("# core v1\n", encoding="utf-8")
            _commit(spoke, "spoke v1")
            _git(spoke, "remote", "add", CORE_REMOTE_NAME, str(core))
            _git(spoke, "fetch", CORE_REMOTE_NAME)

            (core / "AGENTS.md").write_text("# core v2\n", encoding="utf-8")
            (core / "docs" / "standards" / "legal-overlay.md").write_text(
                "# domain leftover v2\n", encoding="utf-8"
            )
            _commit(core, "core v2")

            dry = pull_harness_core(spoke=spoke, ref="main", dry_run=True, fetch=True)
            self.assertTrue(dry["ok"])
            self.assertFalse(dry["merged"])
            self.assertIn("AGENTS.md", dry["updates"])
            self.assertIn("docs/standards/legal-overlay.md", dry["skipped_domain"])
            self.assertEqual((spoke / "AGENTS.md").read_text(encoding="utf-8"), "# core v1\n")
            base = dry["base_branch"]

            live = pull_harness_core(spoke=spoke, ref="main", dry_run=False, fetch=True)
            self.assertTrue(live["ok"])
            self.assertFalse(live["merged"])
            self.assertIsNotNone(live["branch"])
            self.assertTrue(str(live["branch"]).startswith("chore/pull-harness-core-"))
            self.assertEqual((spoke / "AGENTS.md").read_text(encoding="utf-8"), "# core v2\n")
            self.assertFalse((spoke / "docs" / "standards" / "legal-overlay.md").exists())
            current = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=spoke,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.assertEqual(current, live["branch"])
            self.assertNotEqual(current, base)

    def test_unborn_head_dry_run_lists_core_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / "core"
            spoke = Path(tmp) / "spoke"
            _init_repo(core)
            (core / "AGENTS.md").write_text("# core\n", encoding="utf-8")
            (core / "docs" / "standards").mkdir(parents=True)
            (core / "docs" / "standards" / "legal-overlay.md").write_text(
                "# domain\n", encoding="utf-8"
            )
            _commit(core, "core")

            spoke.mkdir()
            _git(spoke, "init", "-b", "main")
            _git(spoke, "remote", "add", CORE_REMOTE_NAME, str(core))
            dry = pull_harness_core(spoke=spoke, ref="main", dry_run=True, fetch=True)
            self.assertTrue(dry["ok"])
            self.assertFalse(dry["merged"])
            self.assertIn("AGENTS.md", dry["updates"])
            self.assertIn("docs/standards/legal-overlay.md", dry["skipped_domain"])
            self.assertTrue(any("no commits" in w for w in dry.get("warnings", [])))

    def test_cli_dry_run_does_not_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spoke = Path(tmp) / "spoke"
            _init_repo(spoke)
            (spoke / "AGENTS.md").write_text("# x\n", encoding="utf-8")
            _commit(spoke, "init")
            _git(
                spoke,
                "remote",
                "add",
                CORE_REMOTE_NAME,
                "https://example.invalid/ai-harness-core.git",
            )
            buf = StringIO()
            with patch("sys.stdout", buf):
                code = pull_main(["--spoke", str(spoke), "--dry-run", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload.get("fetched"))
            self.assertFalse(payload["merged"])


class OverlayStubTests(unittest.TestCase):
    def test_none_domain_skips_markdown_overlay(self) -> None:
        files = domain_overlay_files(
            domain="none",
            name="custom-router",
            org="Koality-Assured",
            visibility="private",
        )
        self.assertEqual(set(files), {".harness/domain.json"})
        marker = json.loads(files[".harness/domain.json"])
        self.assertEqual(marker["visibility"], "private")


if __name__ == "__main__":
    unittest.main()
