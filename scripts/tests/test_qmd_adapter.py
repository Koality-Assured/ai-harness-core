"""Tests for fail-closed QMD adapter source routing.

tags: [tests, harness, qmd, isolation]
routing_hints: [tests, qmd, adapter, main-worktree]
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
_HARNESS_INIT = REPO_ROOT / ".harness" / "__init__.py"
if ("harness" not in sys.modules or not hasattr(sys.modules["harness"], "__path__")) and _HARNESS_INIT.is_file():
    spec = importlib.util.spec_from_file_location(
        "harness", _HARNESS_INIT, submodule_search_locations=[str(_HARNESS_INIT.parent)]
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules["harness"] = mod
        spec.loader.exec_module(mod)

from harness.adapters import QMDAdapter, QMDError  # noqa: E402
from harness.config import QMDAdapterConfig  # noqa: E402


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr or proc.stdout}")
    return proc.stdout.strip()


class QMDAdapterSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.root = base / "router"
        self.remote = base / "origin.git"
        self.source = self.root / "scratch" / "qmd-main"
        self.task = self.root / "scratch" / "worktrees" / "task"

        subprocess.run(["git", "init", "--quiet", "--bare", str(self.remote)], check=True)
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(self.root)], check=True)
        git(self.root, "config", "user.name", "QMD adapter test")
        git(self.root, "config", "user.email", "qmd-adapter@example.invalid")
        (self.root / ".gitignore").write_text(".qmd/index.sqlite\n", encoding="utf-8")
        qmd_config = self.root / ".qmd" / "index.yml"
        qmd_config.parent.mkdir(parents=True)
        qmd_config.write_text("collections: []\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# test main\n", encoding="utf-8")
        git(self.root, "add", ".gitignore", ".qmd/index.yml", "AGENTS.md")
        git(self.root, "commit", "--quiet", "-m", "test: establish qmd fixture")
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "--quiet", "-u", "origin", "main")
        git(self.root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

        self.source.parent.mkdir(parents=True)
        git(self.root, "worktree", "add", "--quiet", "--detach", str(self.source), "main")
        (self.source / ".qmd" / "index.sqlite").write_bytes(b"preserve local QMD index")
        self.task.parent.mkdir(parents=True)
        git(self.root, "worktree", "add", "--quiet", "-b", "codex/task", str(self.task), "main")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_queries_refresh_and_run_only_from_dedicated_detached_snapshot(self) -> None:
        fresh = self.root / "fresh-on-main.txt"
        fresh.write_text("main advanced\n", encoding="utf-8")
        git(self.root, "add", "fresh-on-main.txt")
        git(self.root, "commit", "--quiet", "-m", "docs: advance main")
        git(self.root, "push", "--quiet", "origin", "main")

        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        calls: list[tuple[list[str], Path]] = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append((args, cwd.resolve()))
            return 0, "[]", ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            self.assertEqual(adapter.search("fresh main content"), [])

        self.assertEqual(calls[0][0], ["update"])
        self.assertTrue(calls[1][0][0] == "search")
        self.assertEqual({cwd for _, cwd in calls}, {self.source.resolve()})
        self.assertNotIn(self.task.resolve(), {cwd for _, cwd in calls})
        self.assertEqual(git(self.source, "rev-parse", "HEAD"), git(self.root, "rev-parse", "HEAD"))
        self.assertTrue((self.source / ".qmd" / "index.sqlite").is_file())
        self.assertEqual(git(self.root, "for-each-ref", "--format=%(refname)", "refs/codex/qmd-refresh"), "")

    def test_missing_dedicated_snapshot_fails_without_falling_back(self) -> None:
        no_source = Path(self.temp.name) / "no-qmd-source"
        subprocess.run(["git", "init", "--quiet", "--initial-branch=main", str(no_source)], check=True)
        git(no_source, "config", "user.name", "QMD adapter test")
        git(no_source, "config", "user.email", "qmd-adapter@example.invalid")
        (no_source / "AGENTS.md").write_text("# no QMD snapshot\n", encoding="utf-8")
        git(no_source, "add", "AGENTS.md")
        git(no_source, "commit", "--quiet", "-m", "test: initialize without qmd source")

        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=no_source, binary="unused-qmd")
        with patch.object(adapter, "_run_qmd") as qmd:
            with self.assertRaisesRegex(QMDError, "never falls back"):
                adapter.search("must not use task checkout")
        qmd.assert_not_called()

    def test_explicit_suffix_selects_replacement_while_preserving_old_snapshot(self) -> None:
        replacement = self.root / "scratch" / "qmd-main-recovery"
        git(self.root, "worktree", "add", "--quiet", "--detach", str(replacement), "main")
        preserved_note = self.source / "preserve-this-snapshot.txt"
        preserved_note.write_text("old candidate kept in place\n", encoding="utf-8")
        (replacement / ".qmd" / "index.sqlite").write_bytes(b"replacement QMD index")
        git(self.root, "config", "--local", "harness.qmd.source-worktree", "scratch/qmd-main-recovery")
        other_task = self.root / "scratch" / "worktrees" / "task-two"
        git(self.root, "worktree", "add", "--quiet", "-b", "codex/task-two", str(other_task), "main")

        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        other_adapter = QMDAdapter(QMDAdapterConfig(), repo_root=other_task, binary="unused-qmd")
        calls: list[tuple[list[str], Path]] = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append((args, cwd.resolve()))
            return 0, "[]", ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            self.assertEqual(adapter.search("use explicit recovery snapshot"), [])
        with patch.object(other_adapter, "_run_qmd", side_effect=fake_qmd):
            self.assertEqual(other_adapter.search("use the shared recovery snapshot"), [])

        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[0][0], ["update"])
        self.assertTrue(calls[1][0][0] == "search")
        self.assertEqual(calls[2][0], ["update"])
        self.assertTrue(calls[3][0][0] == "search")
        self.assertEqual({cwd for _, cwd in calls}, {replacement.resolve()})
        self.assertEqual(preserved_note.read_text(encoding="utf-8"), "old candidate kept in place\n")
        self.assertTrue((self.source / ".qmd" / "index.sqlite").is_file())
        self.assertTrue((replacement / ".qmd" / "index.sqlite").is_file())
        listed = git(self.root, "worktree", "list", "--porcelain")
        normalized_list = listed.replace("\\", "/")
        self.assertIn(str(self.source).replace("\\", "/"), normalized_list)
        self.assertIn(str(replacement).replace("\\", "/"), normalized_list)

    def test_multiple_shared_selectors_fail_closed(self) -> None:
        git(self.root, "config", "--local", "--add", "harness.qmd.source-worktree", "scratch/qmd-main")
        git(
            self.root,
            "config",
            "--local",
            "--add",
            "harness.qmd.source-worktree",
            "scratch/qmd-main-recovery",
        )
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")

        with patch.object(adapter, "_run_qmd") as qmd:
            with self.assertRaisesRegex(QMDError, "selector is ambiguous"):
                adapter.search("must not guess between selectors")

        qmd.assert_not_called()

    def test_dirty_dedicated_snapshot_is_preserved_and_not_queried(self) -> None:
        config = self.source / ".qmd" / "index.yml"
        original = config.read_text(encoding="utf-8")
        config.write_text("collections: [dirty]\n", encoding="utf-8")
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")

        with patch.object(adapter, "_run_qmd") as qmd:
            with self.assertRaisesRegex(QMDError, "tracked or untracked changes"):
                adapter.search("do not overwrite user data")

        qmd.assert_not_called()
        self.assertEqual(config.read_text(encoding="utf-8"), "collections: [dirty]\n")
        config.write_text(original, encoding="utf-8")


    def test_vsearch_invokes_qmd_vsearch_with_flags(self) -> None:
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        calls = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append(args)
            return 0, '[{"docid": "#v1", "score": 0.88, "file": "qmd://doc.md", "title": "Doc"}]', ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            hits = adapter.vsearch("vector query", collection="docs", min_score=0.4, limit=3)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].docid, "#v1")

        self.assertEqual(calls[0], ["update"])
        self.assertEqual(calls[1], ["vsearch", "--format", "json", "--min-score", "0.4", "-n", "3", "-c", "docs", "vector query"])

    def test_structured_query_formats_document(self) -> None:
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        calls = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append(args)
            return 0, '[]', ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            adapter.query(intent="Find auth", lex="oauth", vec="token header", hyde="Bearer token")

        self.assertEqual(calls[1][0], "query")
        self.assertIn("intent: Find auth\nlex: oauth\nvec: token header\nhyde: Bearer token", calls[1])

    def test_multi_get_invokes_correct_args(self) -> None:
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        calls = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "batch contents", ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            res = adapter.multi_get(["#1", "#2"], max_lines=50, max_bytes=10000, output_format="md")
            self.assertEqual(res, "batch contents")

        self.assertEqual(calls[1], ["multi-get", "#1,#2", "--format", "md", "-l", "50", "--max-bytes", "10000"])

    def test_cleanup_and_embed(self) -> None:
        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=self.task, binary="unused-qmd")
        calls = []

        def fake_qmd(args: list[str], *, cwd: Path, timeout: int | None = None) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "ok", ""

        with patch.object(adapter, "_run_qmd", side_effect=fake_qmd):
            adapter.cleanup(dry_run=True)
            adapter.embed(collection="docs", force=True, timeout=5)

        self.assertIn(["cleanup", "--dry-run"], calls)
        self.assertIn(["embed", "-c", "docs", "-f", "--timeout", "5"], calls)


if __name__ == "__main__":
    unittest.main()
