"""Unit tests for the in-repo Harness CLI control plane.

tags: [tests, harness, cli, isolation]
routing_hints: [tests, harness-cli, status, branch, agent, pr, clean]

Run: python -m unittest scripts.tests.test_harness_cli -v
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SCRIPTS = Path(__file__).resolve().parents[1]
_LIB = _SCRIPTS / "_lib"
for _p in (str(_SCRIPTS), str(_LIB)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.harness import (  # noqa: E402
    SLUG_PATTERN,
    build_parser,
    cmd_agent,
    cmd_branch,
    cmd_clean,
    cmd_status,
    format_branch_name,
    is_conventional_commit,
    load_claims,
    main,
)


class TestHarnessArgParsing(unittest.TestCase):
    """Test argument parser definitions and defaults."""

    def setUp(self) -> None:
        self.parser = build_parser()

    def test_status_parser(self) -> None:
        args = self.parser.parse_args(["status", "--json"])
        self.assertEqual(args.cmd, "status")
        self.assertTrue(args.json)

    def test_branch_parser_defaults(self) -> None:
        args = self.parser.parse_args(["branch", "my-slug"])
        self.assertEqual(args.cmd, "branch")
        self.assertEqual(args.slug, "my-slug")
        self.assertEqual(args.agent, "harness-operator")
        self.assertEqual(args.type, "agent")
        self.assertFalse(args.force)
        self.assertFalse(args.dry_run)

    def test_branch_parser_custom(self) -> None:
        args = self.parser.parse_args([
            "branch", "feature-x",
            "--areas", "scripts,docs",
            "--agent", "router",
            "--type", "feat",
            "--force",
            "--dry-run",
        ])
        self.assertEqual(args.slug, "feature-feature-x" if False else "feature-x")
        self.assertEqual(args.areas, "scripts,docs")
        self.assertEqual(args.agent, "router")
        self.assertEqual(args.type, "feat")
        self.assertTrue(args.force)
        self.assertTrue(args.dry_run)

    def test_agent_parser(self) -> None:
        args1 = self.parser.parse_args(["agent"])
        self.assertEqual(args1.cmd, "agent")
        self.assertIsNone(args1.agent_id)

        args2 = self.parser.parse_args(["agent", "harness-operator", "--json"])
        self.assertEqual(args2.cmd, "agent")
        self.assertEqual(args2.agent_id, "harness-operator")
        self.assertTrue(args2.json)

    def test_pr_parser(self) -> None:
        args = self.parser.parse_args([
            "pr",
            "--base", "main",
            "--title", "feat: my title",
            "--body", "my body",
            "--draft",
            "--dry-run",
        ])
        self.assertEqual(args.cmd, "pr")
        self.assertEqual(args.base, "main")
        self.assertEqual(args.title, "feat: my title")
        self.assertEqual(args.body, "my body")
        self.assertTrue(args.draft)
        self.assertTrue(args.dry_run)

    def test_clean_parser(self) -> None:
        args = self.parser.parse_args(["clean", "--merged", "--stale", "--force", "--dry-run"])
        self.assertEqual(args.cmd, "clean")
        self.assertTrue(args.merged)
        self.assertTrue(args.stale)
        self.assertTrue(args.force)
        self.assertTrue(args.dry_run)

    def test_auth_parser(self) -> None:
        args_login = self.parser.parse_args(["auth", "login", "anthropic", "--no-browser", "--api-key", "my-key"])
        self.assertEqual(args_login.cmd, "auth")
        self.assertEqual(args_login.auth_cmd, "login")
        self.assertEqual(args_login.provider, "anthropic")
        self.assertTrue(args_login.no_browser)
        self.assertEqual(args_login.api_key, "my-key")

        args_status = self.parser.parse_args(["auth", "status", "--json"])
        self.assertEqual(args_status.cmd, "auth")
        self.assertEqual(args_status.auth_cmd, "status")
        self.assertTrue(args_status.json)

        args_logout = self.parser.parse_args(["auth", "logout", "--all"])
        self.assertEqual(args_logout.cmd, "auth")
        self.assertEqual(args_logout.auth_cmd, "logout")
        self.assertTrue(args_logout.all)


class TestBranchNamingAndValidation(unittest.TestCase):
    """Test slug validation and Conventional branch naming."""

    def test_slug_pattern(self) -> None:
        self.assertTrue(bool(SLUG_PATTERN.match("valid-slug")))
        self.assertTrue(bool(SLUG_PATTERN.match("feature123")))
        self.assertTrue(bool(SLUG_PATTERN.match("a-b-c-1-2-3")))

        self.assertFalse(bool(SLUG_PATTERN.match("Invalid-Slug")))
        self.assertFalse(bool(SLUG_PATTERN.match("invalid_slug")))
        self.assertFalse(bool(SLUG_PATTERN.match("-invalid")))
        self.assertFalse(bool(SLUG_PATTERN.match("invalid-")))
        self.assertFalse(bool(SLUG_PATTERN.match("slug/with/slash")))

    def test_format_branch_name_agent(self) -> None:
        branch = format_branch_name("test-feature", "agent")
        self.assertTrue(branch.startswith("agent/"))
        self.assertTrue(branch.endswith("-test-feature"))
        parts = branch.split("/")
        self.assertEqual(len(parts), 2)
        # Should contain ISO date: YYYY-MM-DD
        date_and_slug = parts[1]
        self.assertRegex(date_and_slug, r"^\d{4}-\d{2}-\d{2}-test-feature$")

    def test_format_branch_name_feat(self) -> None:
        branch = format_branch_name("test-feature", "feat")
        self.assertEqual(branch, "feat/test-feature")


class TestConventionalCommits(unittest.TestCase):
    """Test Conventional Commit regex verification."""

    def test_valid_conventional_commits(self) -> None:
        valid_samples = [
            "feat: add harness cli control plane",
            "fix: handle missing claim gracefully",
            "docs: update agent dispatch table",
            "style: format python files with black",
            "refactor(cli): simplify branch command dispatch",
            "perf: optimize qmd query latency",
            "test: add unit tests for harness cli",
            "build: bump dependency versions",
            "ci: add fast validation check to github actions",
            "chore: remove obsolete scratch worktree",
            "revert: revert previous faulty commit",
            "feat(auth)!: introduce breaking oauth provider changes",
        ]
        for sample in valid_samples:
            with self.subTest(sample=sample):
                self.assertTrue(is_conventional_commit(sample), f"Failed for {sample}")

    def test_invalid_conventional_commits(self) -> None:
        invalid_samples = [
            "add harness cli",
            "WIP: working on something",
            "Merge branch 'main' into agent/feature",
            "Merge pull request #123 from user/branch",
            "feat no colon",
            "invalid_type: something",
            "feat:   ",
        ]
        for sample in invalid_samples:
            with self.subTest(sample=sample):
                self.assertFalse(is_conventional_commit(sample), f"Should fail for {sample}")


class TestHarnessCommands(unittest.TestCase):
    """Functional tests for CLI commands."""

    def test_status_json_execution(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["status", "--json"])
        self.assertEqual(ret, 0)
        data = json.loads(capture.getvalue())
        self.assertIn("branch", data)
        self.assertIn("primary_root", data)
        self.assertIn("active_claims", data)
        self.assertIsInstance(data["active_claims"], list)

    def test_agent_listing_json(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["agent", "--json"])
        self.assertEqual(ret, 0)
        agents = json.loads(capture.getvalue())
        self.assertIsInstance(agents, list)
        self.assertGreater(len(agents), 0)
        # Verify harness-operator is present
        harness_op = next((a for a in agents if a.get("agent_id") == "harness-operator"), None)
        self.assertIsNotNone(harness_op)
        self.assertEqual(harness_op.get("model_tier"), "standard")

    def test_agent_single_detail(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["agent", "harness-operator", "--json"])
        self.assertEqual(ret, 0)
        agent = json.loads(capture.getvalue())
        self.assertEqual(agent.get("agent_id"), "harness-operator")
        self.assertIn("capabilities", agent)
        self.assertIn("allowed_tools", agent)
        self.assertIn("delegation_targets", agent)

    def test_agent_nonexistent_fails(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            ret = main(["agent", "nonexistent-specialist-xyz"])
        self.assertEqual(ret, 2)
        self.assertIn("not found", err_capture.getvalue())

    def test_branch_invalid_slug(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            ret = main(["branch", "Invalid_Slug", "--areas", "scripts"])
        self.assertEqual(ret, 2)
        self.assertIn("slug must be kebab-case", err_capture.getvalue())

    def test_branch_invalid_areas(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            ret = main(["branch", "valid-slug", "--areas", "nonexistent-area-xyz", "--force"])
        self.assertEqual(ret, 2)
        self.assertIn("unknown areas", err_capture.getvalue())

    def test_clean_status_no_args(self) -> None:
        capture = io.StringIO()
        with patch("sys.stdout", capture):
            ret = main(["clean"])
        self.assertEqual(ret, 0)
        self.assertIn("Worktree Cleanup Candidates", capture.getvalue())

    def test_clean_merged_detection(self) -> None:
        mock_proc = MagicMock()
        mock_proc.stdout = "  main\n+ agent/2026-09-15-test-worktree\n"
        with patch("cli.harness.run_git", return_value=mock_proc):
            with patch(
                "cli.harness.load_claims",
                return_value=[{"slug": "test-worktree", "branch": "agent/2026-09-15-test-worktree"}],
            ):
                with patch("routing.spawn_worktree.cmd_remove") as mock_remove:
                    ret = main(["clean", "--merged", "--dry-run"])
                    self.assertEqual(ret, 0)
                    mock_remove.assert_called_once_with(slug="test-worktree", dry_run=True, force=False)

    def test_pr_missing_gh(self) -> None:
        err_capture = io.StringIO()
        with patch("shutil.which", return_value=None):
            with patch("sys.stderr", err_capture):
                ret = main(["pr"])
        self.assertEqual(ret, 1)
        self.assertIn("GitHub CLI ('gh') is not installed", err_capture.getvalue())

    def test_pr_detached_head(self) -> None:
        err_capture = io.StringIO()
        mock_proc = MagicMock()
        mock_proc.stdout = ""
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("cli.harness.run_git", return_value=mock_proc):
                with patch("sys.stderr", err_capture):
                    ret = main(["pr"])
        self.assertEqual(ret, 1)
        self.assertIn("detached HEAD", err_capture.getvalue())

    def test_pr_same_as_base(self) -> None:
        err_capture = io.StringIO()
        mock_proc = MagicMock()
        mock_proc.stdout = "main\n"
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("cli.harness.run_git", return_value=mock_proc):
                with patch("sys.stderr", err_capture):
                    ret = main(["pr"])
        self.assertEqual(ret, 1)
        self.assertIn("cannot create PR from base branch 'main'", err_capture.getvalue())

    def test_pr_dry_run_success(self) -> None:
        capture = io.StringIO()

        def fake_git(args, **kwargs):
            m = MagicMock()
            if args == ["branch", "--show-current"]:
                m.stdout = "agent/2026-09-16-my-test\n"
            elif args == ["log", "main..HEAD", "--format=%s"]:
                m.stdout = "feat: add awesome feature\n"
            else:
                m.stdout = ""
            return m

        mock_sub = MagicMock()
        mock_sub.returncode = 0
        mock_sub.stdout = "OK"

        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("cli.harness.run_git", side_effect=fake_git):
                with patch("subprocess.run", return_value=mock_sub):
                    with patch("sys.stdout", capture):
                        ret = main(["pr", "--dry-run"])
        self.assertEqual(ret, 0)
        self.assertIn("[dry-run] Would execute:", capture.getvalue())
        self.assertIn("PR Title: feat: add awesome feature", capture.getvalue())

    def test_branch_claim_collision(self) -> None:
        err_capture = io.StringIO()
        fake_claims = [{
            "slug": "existing-task",
            "branch": "agent/2026-09-16-existing-task",
            "areas": ["scripts"],
            "agent": "harness-operator",
        }]
        clean_status = MagicMock(returncode=0, stdout="")
        with patch("cli.harness.run_git", return_value=clean_status):
            with patch("cli.harness.load_claims", return_value=fake_claims):
                with patch("sys.stderr", err_capture):
                    ret = main(["branch", "new-task", "--areas", "scripts"])
        self.assertEqual(ret, 3)
        self.assertIn("overlapping areas with active claims", err_capture.getvalue())

    def test_claim_lock_concurrency(self) -> None:
        from routing.spawn_worktree import claim_lock

        # First acquisition should succeed
        with claim_lock(timeout_sec=0.5):
            # Second concurrent acquisition should timeout
            with self.assertRaises(TimeoutError):
                with claim_lock(timeout_sec=0.1, poll_interval=0.02):
                    pass


    def test_harness_missing_command_exits_2(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            with self.assertRaises(SystemExit) as ctx:
                main([])
        self.assertEqual(ctx.exception.code, 2)

    def test_branch_dirty_repo_rejected(self) -> None:
        dirty_proc = MagicMock(returncode=0, stdout=" M scripts/cli/harness.py\n")
        err_capture = io.StringIO()
        with patch("cli.harness.run_git", return_value=dirty_proc):
            with patch("sys.stderr", err_capture):
                ret = main(["branch", "my-feature", "--areas", "scripts"])
        self.assertEqual(ret, 1)
        self.assertIn("primary repository has uncommitted changes", err_capture.getvalue())

    def test_pr_non_conforming_commit_rejected(self) -> None:
        def fake_git(args, **kwargs):
            m = MagicMock()
            if args == ["branch", "--show-current"]:
                m.stdout = "agent/2026-09-16-my-test\n"
            elif args == ["log", "main..HEAD", "--format=%s"]:
                m.stdout = "WIP: non-conforming commit subject without type\n"
            else:
                m.stdout = ""
            return m

        mock_sub = MagicMock(returncode=0, stdout="OK")
        err_capture = io.StringIO()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("cli.harness.run_git", side_effect=fake_git):
                with patch("subprocess.run", return_value=mock_sub):
                    with patch("sys.stderr", err_capture):
                        ret = main(["pr"])
        self.assertEqual(ret, 1)
        self.assertIn("commits do not conform to Conventional Commits", err_capture.getvalue())

    def test_cli_registry_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_cfg = Path(tmp) / "config.json"
            repo1 = Path(tmp) / "spoke-1"
            repo1.mkdir()
            (repo1 / ".git").mkdir()

            with patch.dict(os.environ, {"HARNESS_CONFIG_PATH": str(tmp_cfg)}):
                # 1. Register
                out_reg = io.StringIO()
                with patch("sys.stdout", out_reg):
                    ret_reg = main(["register", str(repo1), "--name", "Spoke One", "--json"])
                self.assertEqual(ret_reg, 0)
                reg_payload = json.loads(out_reg.getvalue())
                self.assertEqual(reg_payload["id"], "spoke-one")

                # 2. List
                out_list = io.StringIO()
                with patch("sys.stdout", out_list):
                    ret_list = main(["list", "--json"])
                self.assertEqual(ret_list, 0)
                list_payload = json.loads(out_list.getvalue())
                self.assertEqual(list_payload["count"], 1)

                # 3. Switch
                out_switch = io.StringIO()
                with patch("sys.stdout", out_switch):
                    ret_switch = main(["switch", "spoke-one", "--json"])
                self.assertEqual(ret_switch, 0)

                # 4. Status includes active harness
                out_status = io.StringIO()
                with patch("sys.stdout", out_status):
                    ret_status = main(["status", "--json"])
                self.assertEqual(ret_status, 0)
                status_payload = json.loads(out_status.getvalue())
                self.assertIn("active_harness", status_payload)
                self.assertEqual(status_payload["active_harness"]["id"], "spoke-one")

                # 5. Deregister
                out_dereg = io.StringIO()
                with patch("sys.stdout", out_dereg):
                    ret_dereg = main(["deregister", "spoke-one", "--json"])
                self.assertEqual(ret_dereg, 0)

                # 6. List after deregister
                out_list2 = io.StringIO()
                with patch("sys.stdout", out_list2):
                    ret_list2 = main(["list", "--json"])
                self.assertEqual(ret_list2, 0)
                list_payload2 = json.loads(out_list2.getvalue())
                self.assertEqual(list_payload2["count"], 0)

    def test_cli_scan_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_cfg = Path(tmp) / "config.json"
            base_dir = Path(tmp) / "repos"
            base_dir.mkdir()
            repo_a = base_dir / "repo-a"
            repo_a.mkdir()
            (repo_a / ".git").mkdir()
            (repo_a / "AGENTS.md").write_text("# Repo A\n", encoding="utf-8")

            with patch.dict(os.environ, {"HARNESS_CONFIG_PATH": str(tmp_cfg)}):
                out_scan = io.StringIO()
                with patch("sys.stdout", out_scan):
                    ret = main(["scan", str(base_dir), "--json"])
                self.assertEqual(ret, 0)
                payload = json.loads(out_scan.getvalue())
                self.assertEqual(payload["scanned_count"], 1)
                self.assertEqual(payload["discovered"][0]["name"], "repo-a")

    def test_cli_no_args_json_runs_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_cfg = Path(tmp) / "config.json"
            with patch.dict(os.environ, {"HARNESS_CONFIG_PATH": str(tmp_cfg)}):
                out = io.StringIO()
                with patch("sys.stdout", out):
                    ret = main(["--json"])
                self.assertEqual(ret, 0)
                payload = json.loads(out.getvalue())
                self.assertIn("harnesses", payload)


if __name__ == "__main__":
    unittest.main()
