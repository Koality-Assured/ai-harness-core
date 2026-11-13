"""Shared repo/script root paths. Not indexed (_lib).

REPO_ROOT is the git repository root of the checkout containing this module,
falling back to git rev-parse or Path.cwd() when appropriate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_FILE_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_repo_root(override: str | Path | None = None) -> Path:
    """Return the repo root to read/write against.

    Order: explicit override -> checkout containing this _lib module ->
    git rev-parse --show-toplevel -> _FILE_REPO_ROOT.
    """
    if override is not None:
        return Path(override).expanduser().resolve()
    if (_FILE_REPO_ROOT / ".git").exists() or (_FILE_REPO_ROOT / "routing").is_dir():
        return _FILE_REPO_ROOT
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=_FILE_REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        if proc.returncode == 0:
            top = (proc.stdout or "").strip()
            if top:
                return Path(top).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return _FILE_REPO_ROOT


repo_root = resolve_repo_root
REPO_ROOT = resolve_repo_root()
