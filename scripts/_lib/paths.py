"""Shared repo/script root paths. Not indexed (_lib).

REPO_ROOT is the git repository root resolved from the process **cwd** via
``git rev-parse --show-toplevel``, falling back to the parent of ``scripts/``
(from ``__file__``) when git is unavailable. That way an absolute-path invoke
of a script that lives in another worktree still writes into the checkout you
are standing in.

SCRIPTS_ROOT is always this checkout's ``scripts/`` directory (from ``__file__``).
Pass ``--repo-root`` (where supported) or call ``resolve_repo_root(override)``
to force a specific root.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_FILE_REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_repo_root(override: str | Path | None = None) -> Path:
    """Return the repo root to read/write against.

    Order: explicit override → ``git rev-parse --show-toplevel`` from cwd →
    checkout that contains this ``_lib`` module.
    """
    if override is not None:
        return Path(override).expanduser().resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
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


REPO_ROOT = resolve_repo_root()
