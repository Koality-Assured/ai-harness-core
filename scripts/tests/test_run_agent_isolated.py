"""Unit tests for isolated zero-disk subagent execution.

tags: [tests, cli, isolation, security, credentials, agent]
routing_hints: [tests, run_agent_isolated, zero-disk]

Run: python -m unittest scripts.tests.test_run_agent_isolated -v
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SCRIPTS = Path(__file__).resolve().parents[1]
_LIB = _SCRIPTS / "_lib"
for _p in (str(_SCRIPTS), str(_LIB)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.run_agent_isolated import execute_agent_isolated, find_harness_binary, main  # noqa: E402


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
            "access_token": f"sk-EXAMPLE-secret-{provider}-key-12345"
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
        self.assertEqual(child_env.get("ANTHROPIC_API_KEY"), "sk-EXAMPLE-secret-anthropic-key-12345")
        self.assertEqual(child_env.get("OPENAI_API_KEY"), "sk-EXAMPLE-secret-openai-key-12345")
        self.assertEqual(child_env.get("GEMINI_API_KEY"), "sk-EXAMPLE-secret-gemini-key-12345")
        self.assertEqual(child_env.get("HARNESS_AGENT_ID"), "harness-operator")

    def test_main_cli_dispatch(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["--agent", "mock-agent", "--dry-run", "--", "echo", "test"])
        self.assertEqual(code, 0)
        self.assertIn("mock-agent", buf.getvalue())




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
