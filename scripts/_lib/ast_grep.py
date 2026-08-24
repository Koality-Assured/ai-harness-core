"""Locate and run the ast-grep CLI. Not indexed (_lib)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMEOUT_SEC = 60
INSTALL_HINT = (
    "install with: python -m pip install ast-grep-cli "
    'or npm install -g @ast-grep/cli'
)


class AstGrepError(RuntimeError):
    """ast-grep missing, timed out, or returned unusable output."""


def find_ast_grep() -> Path:
    """Resolve the ast-grep executable.

    Order: AST_GREP env, PATH (`ast-grep` only), interpreter-adjacent paths,
    then deprecated `sg` if ast-grep is missing.
    """
    override = os.environ.get("AST_GREP", "").strip()
    if override:
        path = Path(override)
        if path.is_file():
            return path
        raise AstGrepError(f"AST_GREP is set but not a file: {override}")

    which = shutil.which("ast-grep")
    if which:
        return Path(which)

    exe_dir = Path(sys.executable).resolve().parent
    candidates: list[Path] = []
    if sys.platform == "win32":
        candidates.extend(
            [
                exe_dir / "Scripts" / "ast-grep.exe",
                exe_dir / "ast-grep.exe",
            ]
        )
    else:
        candidates.extend(
            [
                exe_dir / "ast-grep",
                exe_dir / "bin" / "ast-grep",
            ]
        )
    for cand in candidates:
        if cand.is_file():
            return cand

    sg = shutil.which("sg")
    if sg:
        return Path(sg)

    raise AstGrepError(f"ast-grep CLI not found; {INSTALL_HINT}")


def run_ast_grep(
    args: list[str],
    *,
    cwd: Path | None = None,
    stdin: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    binary: Path | None = None,
    check: bool = True,
) -> object:
    """Run ast-grep with a argv list (never shell=True). Parse --json=compact."""
    exe = binary or find_ast_grep()
    cmd = [str(exe), *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AstGrepError(f"ast-grep timed out after {timeout}s: {' '.join(cmd[:6])}") from exc

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if check and proc.returncode != 0:
        detail = stderr[-800:] or stdout[-800:] or f"exit {proc.returncode}"
        raise AstGrepError(f"ast-grep failed ({proc.returncode}): {detail}")
    if not stdout:
        return []
    payload = stdout
    start_arr = payload.find("[")
    start_obj = payload.find("{")
    starts = [i for i in (start_arr, start_obj) if i != -1]
    if starts:
        payload = payload[min(starts) :]
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        if proc.returncode != 0:
            detail = stderr[-800:] or stdout[-800:] or f"exit {proc.returncode}"
            raise AstGrepError(f"ast-grep failed ({proc.returncode}): {detail}") from exc
        raise AstGrepError(f"ast-grep JSON parse failed: {exc}") from exc
