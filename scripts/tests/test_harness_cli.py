"""Unit tests for the in-repo Harness CLI control plane.

tags: [tests, harness, cli, isolation]
routing_hints: [tests, harness-cli, status, branch, agent, pr, clean]

Run: python -m unittest scripts.tests.test_harness_cli -v
"""

from __future__ import annotations

import io
import json
import os
import subprocess
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

import cli.harness as harness_module  # noqa: E402
from routing.spawn_worktree import WORKTREE_BRANCH_RE, _new_worktree_identity  # noqa: E402

from cli.harness import (  # noqa: E402
    SLUG_PATTERN,
    build_parser,
    cmd_agent,
    cmd_branch,
    cmd_clean,
    cmd_status,
    is_conventional_commit,
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
        self.assertFalse(args.dry_run)
        self.assertFalse(args.json)

    def test_branch_parser_custom(self) -> None:
        args = self.parser.parse_args(["branch", "feature-x", "--dry-run", "--json"])
        self.assertEqual(args.slug, "feature-x")
        self.assertTrue(args.dry_run)
        self.assertTrue(args.json)

    def test_agent_parser(self) -> None:
        args1 = self.parser.parse_args(["agent"])
        self.assertEqual(args1.cmd, "agent")
        self.assertIsNone(args1.agent_id)

        args2 = self.parser.parse_args(["agent", "harness-operator", "--json"])
        self.assertEqual(args2.cmd, "agent")
        self.assertEqual(args2.agent_id, "harness-operator")
        self.assertTrue(args2.json)

    def test_pr_parser(self) -> None:
        default_args = self.parser.parse_args(["pr"])
        self.assertIsNone(default_args.base)
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
        args = self.parser.parse_args(["clean", "--pr", "42"])
        self.assertEqual(args.cmd, "clean")
        self.assertIsNone(args.branch)
        self.assertEqual(args.pr, 42)
        self.assertFalse(args.apply)

        apply_args = self.parser.parse_args(["clean", "--branch", "codex/feature-x", "--pr", "42", "--apply"])
        self.assertEqual(apply_args.branch, "codex/feature-x")
        self.assertTrue(apply_args.apply)

    def test_chat_no_stream_parser(self) -> None:
        args = self.parser.parse_args(["chat", "-q", "ping", "--no-stream"])
        self.assertEqual(args.cmd, "chat")
        self.assertEqual(args.query, "ping")
        self.assertTrue(args.no_stream)

    def test_adapter_provider_choices_exclude_cursor_and_gateway_help_is_qualified(self) -> None:
        for adapter in ("gateway", "acp"):
            with self.subTest(adapter=adapter), self.assertRaises(SystemExit):
                self.parser.parse_args([adapter, "--provider", "cursor"])
        gateway_parser = self.parser._subparsers._group_actions[0].choices["gateway"]
        gateway_help = " ".join(gateway_parser.format_help().split())
        self.assertIn("text-only", gateway_help)
        self.assertIn("tools registered by the server", gateway_help)
        self.assertIn("client tools or image content", gateway_help)

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

    def test_task_branch_identity_uses_unique_codex_branch(self) -> None:
        first_id, first_branch = _new_worktree_identity("test-feature")
        second_id, second_branch = _new_worktree_identity("test-feature")
        self.assertRegex(first_id, r"^test-feature-\d{8}t\d{6}z-[0-9a-f]{8}$")
        self.assertRegex(first_branch, WORKTREE_BRANCH_RE)
        self.assertTrue(first_branch.endswith(first_id))
        self.assertNotEqual(first_id, second_id)
        self.assertNotEqual(first_branch, second_branch)


class TestConventionalCommits(unittest.TestCase):
    """Test Conventional Commit regex verification."""

    def test_valid_conventional_commits(self) -> None:
        valid_samples = [
            "feat: add harness cli control plane",
            "fix: handle missing task metadata gracefully",
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
        self.assertIn("worktrees", data)
        self.assertNotIn("active_claims", data)
        self.assertIsInstance(data["worktrees"], list)

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
            ret = main(["branch", "Invalid_Slug"])
        self.assertEqual(ret, 2)
        self.assertIn("slug must be kebab-case", err_capture.getvalue())


    def test_clean_requires_only_pr(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            with self.assertRaises(SystemExit):
                build_parser().parse_args(["clean"])
        self.assertIn("--pr", err_capture.getvalue())

    def test_clean_delegates_to_verified_cleanup(self) -> None:
        with patch("routing.spawn_worktree.cmd_cleanup", return_value=0) as cleanup:
            ret = main(["clean", "--pr", "7", "--json"])
        self.assertEqual(ret, 0)
        args, kwargs = cleanup.call_args
        self.assertEqual(args, (None, 7))
        self.assertTrue(kwargs["dry_run"])
        self.assertTrue(kwargs["as_json"])
        self.assertIsInstance(kwargs["root"], Path)

    def test_clean_apply_is_explicit_and_dry_run_wins_as_error(self) -> None:
        with patch("routing.spawn_worktree.cmd_cleanup", return_value=0) as cleanup:
            ret = main(["clean", "--branch", "codex/task-one", "--pr", "7", "--apply"])
        self.assertEqual(ret, 0)
        self.assertFalse(cleanup.call_args.kwargs["dry_run"])

        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            ret = main(["clean", "--pr", "7", "--apply", "--dry-run"])
        self.assertEqual(ret, 2)
        self.assertIn("cannot be used together", err_capture.getvalue())











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
            with patch("routing.spawn_worktree.default_branch_name", return_value="main"):
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
            with patch("routing.spawn_worktree.default_branch_name", return_value="main"):
                with patch("cli.harness.run_git", side_effect=fake_git):
                    with patch("subprocess.run", return_value=mock_sub):
                        with patch("sys.stdout", capture):
                            ret = main(["pr", "--dry-run"])
        self.assertEqual(ret, 0)
        self.assertIn("[dry-run] Would execute:", capture.getvalue())
        self.assertIn("PR Title: feat: add awesome feature", capture.getvalue())

    def test_pr_uses_repository_default_branch_when_base_is_omitted(self) -> None:
        capture = io.StringIO()
        git_calls: list[list[str]] = []

        def fake_git(args, **kwargs):
            git_calls.append(args)
            proc = MagicMock()
            if args == ["branch", "--show-current"]:
                proc.stdout = "codex/example-task\n"
            elif args == ["log", "trunk..HEAD", "--format=%s"]:
                proc.stdout = "feat: add example\n"
            else:
                proc.stdout = ""
            return proc

        mock_sub = MagicMock(returncode=0, stdout="OK")
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("routing.spawn_worktree.default_branch_name", return_value="trunk") as resolve:
                with patch("cli.harness.run_git", side_effect=fake_git):
                    with patch("subprocess.run", return_value=mock_sub):
                        with patch("sys.stdout", capture):
                            ret = main(["pr", "--dry-run"])

        self.assertEqual(ret, 0)
        resolve.assert_called_once()
        self.assertIn("targeting 'trunk'", capture.getvalue())
        self.assertIn("--base trunk", capture.getvalue())
        self.assertIn(["log", "trunk..HEAD", "--format=%s"], git_calls)

    def test_same_task_slug_can_be_created_in_parallel_sessions(self) -> None:
        with patch("routing.spawn_worktree.cmd_create", return_value=0) as create:
            self.assertEqual(main(["branch", "overlapping-task"]), 0)
            self.assertEqual(main(["branch", "overlapping-task"]), 0)
        self.assertEqual(create.call_count, 2)
        self.assertEqual([call.args[0] for call in create.call_args_list], ["overlapping-task", "overlapping-task"])



    def test_harness_missing_command_exits_2(self) -> None:
        err_capture = io.StringIO()
        with patch("sys.stderr", err_capture):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                with self.assertRaises(SystemExit) as ctx:
                    main([])
        self.assertEqual(ctx.exception.code, 2)

    def test_branch_does_not_require_clean_primary_checkout(self) -> None:
        with patch("cli.harness.run_git") as git:
            with patch("routing.spawn_worktree.cmd_create", return_value=0) as create:
                self.assertEqual(main(["branch", "dirty-primary-task"]), 0)
        git.assert_not_called()
        create.assert_called_once()

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
            with patch("routing.spawn_worktree.default_branch_name", return_value="main"):
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
