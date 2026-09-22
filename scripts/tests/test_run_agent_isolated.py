"""Unit tests for isolated zero-disk subagent execution wrapper and lease TTL tracking.

tags: [tests, cli, isolation, security, credentials, agent]
routing_hints: [tests, run_agent_isolated, spawn_worktree, ttl, zero-disk]

Run: python -m unittest scripts.tests.test_run_agent_isolated -v
"""

from __future__ import annotations

import datetime as dt
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

from cli.run_agent_isolated import execute_agent_isolated, find_harness_binary, main  # noqa: E402
from routing.spawn_worktree import cmd_add, cmd_check, query_active_claims  # noqa: E402


class TestRunAgentIsolated(unittest.TestCase):
    """Test zero-disk credential injection and command execution."""

    def test_dry_run_zero_disk(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = execute_agent_isolated(
                agent_id="test-agent",
                cmd_args=["echo", "hello"],
                dry_run=True,
            )
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("echo hello", output)
        self.assertIn("test-agent", output)

    @patch("cli.run_agent_isolated.find_harness_binary", return_value=None)
    @patch("cli.run_agent_isolated.get_vault")
    @patch("subprocess.run")
    def test_in_memory_secret_injection_python_fallback(
        self, mock_run: MagicMock, mock_get_vault: MagicMock, mock_find: MagicMock
    ) -> None:
        mock_run.return_value.returncode = 0
        fake_vault = MagicMock()
        fake_vault.get_credential.side_effect = lambda provider: {
            "access_token": f"sk-secret-{provider}-key-12345"
        }
        mock_get_vault.return_value = fake_vault

        code = execute_agent_isolated(
            agent_id="harness-operator",
            cmd_args=["python", "-c", "print(1)"],
            dry_run=False,
        )
        self.assertEqual(code, 0)
        self.assertTrue(mock_run.called)
        _, kwargs = mock_run.call_args
        child_env = kwargs.get("env", {})
        self.assertEqual(child_env.get("ANTHROPIC_API_KEY"), "sk-secret-anthropic-key-12345")
        self.assertEqual(child_env.get("OPENAI_API_KEY"), "sk-secret-openai-key-12345")
        self.assertEqual(child_env.get("GEMINI_API_KEY"), "sk-secret-gemini-key-12345")
        self.assertEqual(child_env.get("HARNESS_AGENT_ID"), "harness-operator")

    def test_main_cli_dispatch(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--agent", "mock-agent", "--dry-run", "--", "echo", "test"])
        self.assertEqual(code, 0)
        self.assertIn("mock-agent", buf.getvalue())


class TestSpawnWorktreeTTLAndClaims(unittest.TestCase):
    """Test worktree claim TTL lease calculation and preflight collision checks."""

    def test_cmd_add_dry_run_records_ttl_and_expiry(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = cmd_add(
                slug="ttl-test-feature",
                areas=["routing"],
                agent="test-agent",
                force=False,
                dry_run=True,
                as_json=True,
                ttl_hours=12.0,
            )
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        claim = payload["claim"]
        self.assertEqual(claim["slug"], "ttl-test-feature")
        self.assertEqual(claim["ttl_hours"], 12.0)
        self.assertIn("created_at", claim)
        self.assertIn("expires_at", claim)

        # Validate timestamp delta matches TTL
        created_dt = dt.datetime.fromisoformat(claim["created_at"].replace("Z", "+00:00"))
        expires_dt = dt.datetime.fromisoformat(claim["expires_at"].replace("Z", "+00:00"))
        delta_hours = (expires_dt - created_dt).total_seconds() / 3600.0
        self.assertAlmostEqual(delta_hours, 12.0, places=2)

    def test_query_active_claims_filters_expired_leases(self) -> None:
        now_utc = dt.datetime.now(dt.timezone.utc)
        active_claim = {
            "slug": "active-worker",
            "areas": ["routing"],
            "created_at": (now_utc - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": (now_utc + dt.timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "is_stale": False,
        }
        expired_claim = {
            "slug": "expired-worker",
            "areas": ["routing"],
            "created_at": (now_utc - dt.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at": (now_utc - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "is_stale": True,
        }

        with patch("routing.spawn_worktree.load_claims", return_value=[active_claim, expired_claim]):
            with patch("shutil.which", return_value=None):
                active = query_active_claims()
                slugs = [c["slug"] for c in active]
                self.assertIn("active-worker", slugs)
                self.assertNotIn("expired-worker", slugs)


class TestHostAgnosticHardening(unittest.TestCase):
    """Test host-agnostic binary resolution and Python subprocess normalization."""

    @patch("cli.run_agent_isolated.find_harness_binary", return_value=None)
    @patch("cli.run_agent_isolated.get_vault")
    @patch("subprocess.run")
    def test_sys_executable_normalization(
        self, mock_run: MagicMock, mock_vault: MagicMock, mock_find: MagicMock
    ) -> None:
        mock_run.return_value.returncode = 0
        mock_vault.return_value.get_credential.return_value = None

        code = execute_agent_isolated(
            agent_id="test-agent",
            cmd_args=["python", "-c", "print('hello')"],
            dry_run=False,
        )
        self.assertEqual(code, 0)
        self.assertTrue(mock_run.called)
        called_args, _ = mock_run.call_args
        cmd_executed = called_args[0]
        # Must invoke sys.executable instead of bare "python"
        self.assertEqual(cmd_executed[0], sys.executable)

    @patch("shutil.which", return_value=None)
    def test_find_harness_binary_searches_standard_paths(self, mock_which: MagicMock) -> None:
        def fake_is_file(self_path):
            return ".local" in str(self_path) and ("harness" in str(self_path))

        with patch("pathlib.Path.is_file", fake_is_file):
            found = find_harness_binary()
            self.assertIsNotNone(found)
            self.assertIn(".local", found)


class TestRegisterWatcher(unittest.TestCase):
    """Test cross-platform daemon registration script across Windows, macOS, and Linux mocks."""

    def test_register_watcher_windows_mock(self) -> None:
        _DAEMON_DIR = _SCRIPTS / "daemon"
        sys.path.insert(0, str(_DAEMON_DIR))
        import register_watcher

        with patch("sys.platform", "win32"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="SUCCESS", stderr="")
                code = register_watcher.main(["--status", "--task-name", "TestWatcher"])
                self.assertEqual(code, 0)
                mock_run.assert_called_with(
                    ["schtasks", "/Query", "/TN", "TestWatcher", "/FO", "LIST", "/V"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                code_unreg = register_watcher.main(["--unregister", "--task-name", "TestWatcher"])
                self.assertEqual(code_unreg, 0)
                mock_run.assert_called_with(
                    ["schtasks", "/Delete", "/TN", "TestWatcher", "/F"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

    def test_register_watcher_macos_mock(self) -> None:
        _DAEMON_DIR = _SCRIPTS / "daemon"
        sys.path.insert(0, str(_DAEMON_DIR))
        import register_watcher

        with patch("sys.platform", "darwin"):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="loaded", stderr="")
                    code = register_watcher.main(["--status", "--task-name", "TestWatcher"])
                    self.assertEqual(code, 0)
                    mock_run.assert_called_with(
                        ["launchctl", "list", "com.harness.testwatcher"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

    def test_register_watcher_linux_mock(self) -> None:
        _DAEMON_DIR = _SCRIPTS / "daemon"
        sys.path.insert(0, str(_DAEMON_DIR))
        import register_watcher

        with patch("sys.platform", "linux"):
            with patch("pathlib.Path.is_file", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="active", stderr="")
                    code = register_watcher.main(["--status", "--task-name", "TestWatcher"])
                    self.assertEqual(code, 0)
                    mock_run.assert_called_with(
                        ["systemctl", "--user", "status", "harness-testwatcher.timer"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )


if __name__ == "__main__":
    unittest.main()

