"""Unit tests for HarnessRegistry, multi-harness discovery, and schema adaptation.

tags: [tests, harness, registry, switcher, tui]
routing_hints: [tests, harness-registry, switch, scan, list, register, deregister]

Run: python -m unittest scripts.tests.test_harness_registry -v
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SCRIPTS = Path(__file__).resolve().parents[1]
_CLI = _SCRIPTS / "cli"
_LIB = _SCRIPTS / "_lib"
for _p in (str(_CLI), str(_SCRIPTS), str(_LIB)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.registry import (  # noqa: E402
    HarnessRegistry,
    infer_harness_domain,
    inspect_harness,
    slugify_id,
)
from cli.schema_adapter import (  # noqa: E402
    load_dynamic_agents,
    load_dynamic_areas,
    resolve_harness_root,
)


class TestHarnessRegistryCore(unittest.TestCase):
    """Test core persistence, thread safety, and recovery of HarnessRegistry."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp_dir.name) / "config.json"
        self.registry = HarnessRegistry(config_path=self.config_path)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_default_config_creation(self) -> None:
        data = self.registry._load()
        self.assertEqual(data["version"], "1.0.0")
        self.assertIsNone(data["active_harness"])
        self.assertEqual(data["harnesses"], {})

    def test_register_valid_directory(self) -> None:
        repo_dir = Path(self.tmp_dir.name) / "my-repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        rec = self.registry.register(repo_dir, name="My Test Repo", domain="Test Domain")
        self.assertEqual(rec["id"], "my-test-repo")
        self.assertEqual(rec["name"], "My Test Repo")
        self.assertEqual(rec["domain"], "Test Domain")
        self.assertEqual(Path(rec["path"]).resolve(), repo_dir.resolve())

        # Check persistence
        loaded = self.registry._load()
        self.assertIn("my-test-repo", loaded["harnesses"])
        self.assertEqual(loaded["active_harness"], "my-test-repo")

    def test_register_nonexistent_directory_fails(self) -> None:
        nonexistent = Path(self.tmp_dir.name) / "does-not-exist"
        with self.assertRaises(FileNotFoundError):
            self.registry.register(nonexistent)

    def test_register_file_fails(self) -> None:
        file_path = Path(self.tmp_dir.name) / "file.txt"
        file_path.write_text("hello", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            self.registry.register(file_path)

    def test_register_duplicate_path_updates_record(self) -> None:
        repo_dir = Path(self.tmp_dir.name) / "spoke-repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        rec1 = self.registry.register(repo_dir, name="Initial Name")
        self.assertEqual(rec1["id"], "initial-name")

        rec2 = self.registry.register(repo_dir, name="Updated Name")
        # Should retain same ID since it's the exact same resolved path
        self.assertEqual(rec2["id"], "initial-name")
        self.assertEqual(rec2["name"], "Updated Name")

        harnesses = self.registry.list_harnesses()
        self.assertEqual(len(harnesses), 1)

    def test_register_without_repo_markers_requires_force(self) -> None:
        plain_dir = Path(self.tmp_dir.name) / "plain-folder"
        plain_dir.mkdir()

        with self.assertRaises(ValueError) as ctx:
            self.registry.register(plain_dir)
        self.assertIn("does not appear to be a git repository or domain harness", str(ctx.exception))

        # With force=True, registration succeeds
        rec = self.registry.register(plain_dir, force=True)
        self.assertEqual(rec["id"], "plain-folder")

    def test_deregister_by_id_and_path(self) -> None:
        repo1 = Path(self.tmp_dir.name) / "repo-1"
        repo1.mkdir()
        (repo1 / ".git").mkdir()
        repo2 = Path(self.tmp_dir.name) / "repo-2"
        repo2.mkdir()
        (repo2 / ".git").mkdir()

        self.registry.register(repo1, name="Repo One")
        self.registry.register(repo2, name="Repo Two")

        self.assertEqual(len(self.registry.list_harnesses()), 2)

        # Deregister by ID
        deleted1 = self.registry.deregister("repo-one")
        self.assertTrue(deleted1)
        self.assertEqual(len(self.registry.list_harnesses()), 1)

        # Deregister by path
        deleted2 = self.registry.deregister(str(repo2))
        self.assertTrue(deleted2)
        self.assertEqual(len(self.registry.list_harnesses()), 0)

        # Deregister nonexistent
        deleted3 = self.registry.deregister("nonexistent")
        self.assertFalse(deleted3)

    def test_switch_active_harness(self) -> None:
        repo1 = Path(self.tmp_dir.name) / "repo-1"
        repo1.mkdir()
        (repo1 / ".git").mkdir()
        repo2 = Path(self.tmp_dir.name) / "repo-2"
        repo2.mkdir()
        (repo2 / ".git").mkdir()

        self.registry.register(repo1, name="Repo 1")
        self.registry.register(repo2, name="Repo 2")

        self.registry.switch("repo-2")
        active = self.registry.get_active_harness()
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], "repo-2")
        self.assertIsNotNone(active["last_switched_at"])

        # Switch to nonexistent raises KeyError
        with self.assertRaises(KeyError):
            self.registry.switch("ghost-repo")

        # Switch to harness whose directory was removed raises FileNotFoundError
        repo3 = Path(self.tmp_dir.name) / "repo-3"
        repo3.mkdir()
        (repo3 / ".git").mkdir()
        self.registry.register(repo3, name="Repo 3")
        (repo3 / ".git").rmdir()
        repo3.rmdir()
        with self.assertRaises(FileNotFoundError):
            self.registry.switch("repo-3")

        # Switch to path that is a file raises NotADirectoryError
        fake_file = Path(self.tmp_dir.name) / "fake-file"
        fake_file.write_text("not a dir", encoding="utf-8")
        data = self.registry._load()
        data["harnesses"]["file-repo"] = {"id": "file-repo", "path": str(fake_file)}
        self.registry._save(data)
        with self.assertRaises(NotADirectoryError):
            self.registry.switch("file-repo")

    def test_corrupted_config_recovery(self) -> None:
        # Write corrupted JSON
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{{corrupted-bad-json-syntax}}", encoding="utf-8")

        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            data = self.registry._load()

        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["harnesses"], {})
        self.assertIn("corrupted harness registry config", err_capture.getvalue())

        # Verify a backup was created
        backups = list(self.config_path.parent.glob("config.json.corrupted.*"))
        self.assertEqual(len(backups), 1)

    def test_concurrent_registration_safety(self) -> None:
        num_threads = 8
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                p = Path(self.tmp_dir.name) / f"worker-repo-{idx}"
                p.mkdir(exist_ok=True)
                (p / ".git").mkdir(exist_ok=True)
                self.registry.register(p, name=f"Worker {idx}")
                self.registry.switch(f"worker-{idx}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        harnesses = self.registry.list_harnesses()
        self.assertEqual(len(harnesses), num_threads)


class TestSiblingDiscoveryAndInspection(unittest.TestCase):
    """Test sibling repository discovery and live inspection heuristics."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.registry = HarnessRegistry(config_path=self.base_dir / "reg_config.json")

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_slugify_id(self) -> None:
        self.assertEqual(slugify_id("AI Router"), "ai-router")
        self.assertEqual(slugify_id("art_router"), "art-router")
        self.assertEqual(slugify_id("UI/UX Router!"), "ui-ux-router")
        self.assertEqual(slugify_id("---"), "harness")
        # Reserved DOS/Windows slugs
        self.assertEqual(slugify_id("con"), "harness-con")
        self.assertEqual(slugify_id("nul"), "harness-nul")
        self.assertEqual(slugify_id("COM1"), "harness-com1")

    def test_inspect_harness_git_timeout(self) -> None:
        r = self.base_dir / "timeout-repo"
        r.mkdir()
        (r / ".git").mkdir()

        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=3)):
            info = inspect_harness(r)
        self.assertEqual(info["branch"], "(timeout)")
        self.assertEqual(info["status"], "(timeout)")

    def test_infer_harness_domain(self) -> None:
        # Known domains
        ai_dir = self.base_dir / "ai-router"
        ai_dir.mkdir()
        self.assertEqual(infer_harness_domain(ai_dir), "General Orchestrator & AI Router")

        # Inferred from config
        custom_dir = self.base_dir / "custom-harness"
        custom_dir.mkdir()
        (custom_dir / "config").mkdir()
        (custom_dir / "config" / "harness.config.json").write_text(
            json.dumps({"domain": "Custom Robotics Engine"}), encoding="utf-8"
        )
        self.assertEqual(infer_harness_domain(custom_dir), "Custom Robotics Engine")

        # Inferred from AGENTS.md
        doc_dir = self.base_dir / "doc-harness"
        doc_dir.mkdir()
        (doc_dir / "AGENTS.md").write_text("# Documentation Engine Guidelines\n", encoding="utf-8")
        self.assertEqual(infer_harness_domain(doc_dir), "Documentation Engine Guidelines")

    def test_scan_siblings_discovers_repositories(self) -> None:
        # Create sibling repos
        # 1. Valid router repo (has .git and routing/areas.yaml)
        r1 = self.base_dir / "art-router"
        r1.mkdir()
        (r1 / ".git").mkdir()
        (r1 / "routing").mkdir()
        (r1 / "routing" / "areas.yaml").write_text("areas:\n  - id: canvas\n", encoding="utf-8")

        # 2. Valid router repo (has .git and config/harness.config.json)
        r2 = self.base_dir / "legal-router"
        r2.mkdir()
        (r2 / ".git").mkdir()
        (r2 / "config").mkdir()
        (r2 / "config" / "harness.config.json").write_text("{}", encoding="utf-8")

        # 3. Non-git directory (should be ignored)
        r3 = self.base_dir / "random-folder"
        r3.mkdir()
        (r3 / "routing").mkdir()
        (r3 / "routing" / "areas.yaml").write_text("areas:\n", encoding="utf-8")

        # 4. Git repo without router markers (should be ignored)
        r4 = self.base_dir / "plain-git-repo"
        r4.mkdir()
        (r4 / ".git").mkdir()

        discovered = self.registry.scan_siblings(parent_dir=self.base_dir, auto_register=True)
        self.assertEqual(len(discovered), 2)
        ids = {d["id"] for d in discovered}
        self.assertIn("art-router", ids)
        self.assertIn("legal-router", ids)

        # Verify auto-registered in catalog
        catalog = self.registry.list_harnesses()
        self.assertEqual(len(catalog), 2)


class TestDynamicSchemaAdapter(unittest.TestCase):
    """Test dynamic inspection of areas and agents across arbitrary checkouts."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.tmp_dir.name) / "test-spoke"
        self.repo_dir.mkdir()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_load_dynamic_areas(self) -> None:
        routing_dir = self.repo_dir / "routing"
        routing_dir.mkdir()
        (routing_dir / "areas.yaml").write_text(
            "areas:\n"
            "  - id: core-logic\n"
            "    purpose: Main logic\n"
            "  - id: visual-assets\n"
            "    purpose: Graphics\n",
            encoding="utf-8",
        )

        areas = load_dynamic_areas(self.repo_dir)
        self.assertEqual(len(areas), 2)
        self.assertEqual(areas[0]["id"], "core-logic")
        self.assertEqual(areas[1]["id"], "visual-assets")

    def test_load_dynamic_agents(self) -> None:
        agents_dir = self.repo_dir / "ai-tooling" / "agents" / "specialist-one"
        agents_dir.mkdir(parents=True)
        (agents_dir / "AGENT.md").write_text(
            "# Specialist One Agent\nmodel_tier: pro\n", encoding="utf-8"
        )

        agents = load_dynamic_agents(self.repo_dir)
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["id"], "specialist-one")
        self.assertEqual(agents[0]["title"], "Specialist One Agent")
        self.assertEqual(agents[0]["tier"], "pro")

    def test_resolve_harness_root(self) -> None:
        # Explicit path
        resolved = resolve_harness_root(str(self.repo_dir))
        self.assertEqual(resolved, self.repo_dir.resolve())

        # Invalid path raises ValueError
        with self.assertRaises(ValueError):
            resolve_harness_root("invalid-nonexistent-path-12345")


if __name__ == "__main__":
    unittest.main()
