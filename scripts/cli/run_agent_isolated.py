"""Execute subagent commands with provider API keys injected strictly in-memory.

tags: [cli, isolation, security, credentials, agent]
routing_hints: [exec, agent, keyring, vault, in-memory, zero-disk]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cli.auth.keyring_vault import get_vault, mask_token  # noqa: E402
from cli.auth.oauth_flows import ensure_fresh_token  # noqa: E402
from paths import REPO_ROOT  # noqa: E402


def find_harness_binary() -> str | None:
    """Locate the compiled harness CLI binary across Windows and POSIX platforms."""
    bin_name = "harness.exe" if os.name == "nt" else "harness"
    cmd = shutil.which("harness") or shutil.which(bin_name)
    if cmd:
        return cmd
    candidates: list[Path] = [
        # POSIX standard paths
        Path.home() / ".local" / "bin" / bin_name,
        Path("/opt/homebrew/bin") / bin_name,
        Path("/usr/local/bin") / bin_name,
    ]
    if os.name == "nt":
        candidates.extend([
            Path.home() / "scoop" / "shims" / bin_name,
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "harness" / bin_name,
            Path("C:/Code/harness-cli") / bin_name,
        ])
    candidates.append(REPO_ROOT.parent / "harness-cli" / bin_name)

    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def execute_agent_isolated(
    agent_id: str,
    cmd_args: Sequence[str],
    workspace: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Wrap command execution with foundation model credentials injected strictly in-memory."""
    if not cmd_args:
        print("error: no command provided to execute", file=sys.stderr)
        return 1

    # Standardize Python subcommands: invoke sys.executable instead of bare "python" or "python3"
    normalized_cmd = list(cmd_args)
    if normalized_cmd and normalized_cmd[0] in ("python", "python3"):
        normalized_cmd[0] = sys.executable

    work_dir = (workspace or Path.cwd()).resolve()
    harness_bin = find_harness_binary()

    if harness_bin:
        # Use compiled harness exec for native sub-millisecond in-memory secret injection
        exec_cmd = [harness_bin, "exec", "--agent", agent_id]
        if dry_run:
            exec_cmd.append("--dry-run")
        exec_cmd.extend(["--", *normalized_cmd])

        if dry_run:
            print(f"dry-run (harness binary): {' '.join(exec_cmd)} (cwd: {work_dir})")
            return 0

        proc = subprocess.run(exec_cmd, cwd=str(work_dir))
        return proc.returncode

    # Fallback to Python in-memory keyring retrieval (zero-disk)
    vault = get_vault()
    child_env = os.environ.copy()
    injected_providers = []

    provider_env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "cursor": "CURSOR_API_KEY",
    }

    for provider, env_var in provider_env_map.items():
        try:
            # Check and refresh tokens approaching expiry via RFC 6749 background rotation
            cred = ensure_fresh_token(provider, vault=vault)
            if not cred:
                cred = vault.get_credential(provider)
            if cred and cred.get("access_token"):
                child_env[env_var] = cred["access_token"]
                injected_providers.append((env_var, mask_token(cred["access_token"])))
        except Exception:
            pass

    child_env["HARNESS_AGENT_ID"] = agent_id

    if dry_run:
        print(f"dry-run (python fallback): {' '.join(normalized_cmd)} (cwd: {work_dir})")
        print(f"agent: {agent_id}")
        print("injected credentials (in-memory only, zero-disk):")
        for env_var, masked in injected_providers:
            print(f"  {env_var}: {masked}")
        return 0

    proc = subprocess.run(normalized_cmd, env=child_env, cwd=str(work_dir))
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute subagent command with credentials injected strictly in-memory (zero-disk)."
    )
    parser.add_argument("--agent", default="router", help="Agent identity for profile tracking")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Workspace directory to execute command within (defaults to current dir)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Display invocation without running")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command and arguments to execute")

    args = parser.parse_args(argv)
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    return execute_agent_isolated(
        agent_id=args.agent,
        cmd_args=cmd,
        workspace=args.workspace,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
