"""Run markdownlint-cli2 over repo Markdown (read-only by default).

tags: [docs, markdown]
routing_hints: [markdownlint, lint, markdownlint-cli2, dry-run]

Invokes DavidAnson markdownlint-cli2 (pinned) via npx — not classic markdownlint-cli.
Repo config is expected at ``.markdownlint-cli2.jsonc`` (documentation-ops adds it);
``--config`` is passed only when that file exists.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

CLI2_PACKAGE = "markdownlint-cli2@0.23.2"
DEFAULT_CONFIG_NAME = ".markdownlint-cli2.jsonc"

# Prefer cli2 globs (# negation; / separators). Excludes cover scratch (incl. worktrees),
# change-history, VCS, and node_modules. Includes docs/, routing/, ai-tooling/, supporting/,
# references/, AGENTS.md / README.md / skills, and other tracked Markdown via **/*.md.
DEFAULT_GLOBS = [
    "**/*.md",
    "#scratch/**",
    "#change-history/**",
    "#.git/**",
    "#node_modules/**",
]


def resolve_npx() -> str | None:
    if sys.platform == "win32":
        return shutil.which("npx.cmd") or shutil.which("npx.exe") or shutil.which("npx")
    return shutil.which("npx")


def resolve_node() -> str | None:
    if sys.platform == "win32":
        return shutil.which("node.exe") or shutil.which("node")
    return shutil.which("node")


def build_command(
    *,
    npx: str,
    globs: list[str],
    fix: bool,
    config_path: Path | None,
) -> list[str]:
    cmd = [npx, "--yes", CLI2_PACKAGE]
    if fix:
        cmd.append("--fix")
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    cmd.extend(globs)
    return cmd


def format_command(cmd: list[str]) -> str:
    parts: list[str] = []
    for part in cmd:
        if any(c in part for c in (' ', '*', '#', '?')):
            parts.append(f'"{part}"')
        else:
            parts.append(part)
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Config: default is <repo>/.markdownlint-cli2.jsonc. "
            "If missing, the script omits --config (documentation-ops owns adding the file). "
            "Lint is read-only unless --fix is passed."
        ),
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply markdownlint-cli2 auto-fixes (opt-in; default is read-only lint)",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help=(
            f"Config file for cli2 (default: <repo>/{DEFAULT_CONFIG_NAME}; "
            "passed only when the file exists)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact npx command and globs without running",
    )
    parser.add_argument(
        "globs",
        nargs="*",
        help="Optional cli2 globs (default: repo Markdown with scratch/change-history exclusions)",
    )
    args = parser.parse_args(argv)

    globs = list(args.globs) if args.globs else list(DEFAULT_GLOBS)

    if args.config:
        config_candidate = Path(args.config).expanduser()
        if not config_candidate.is_absolute():
            config_candidate = (ROOT / config_candidate).resolve()
        else:
            config_candidate = config_candidate.resolve()
        if not config_candidate.is_file():
            parser.error(f"config file not found: {config_candidate}")
        config_path: Path | None = config_candidate
    else:
        default_config = (ROOT / DEFAULT_CONFIG_NAME).resolve()
        if default_config.is_file():
            config_path = default_config
        else:
            config_path = None
            print(
                f"note: {DEFAULT_CONFIG_NAME} not found under repo root; "
                "omitting --config (documentation-ops will add it)",
                file=sys.stderr,
            )

    node = resolve_node()
    npx = resolve_npx()
    npx_for_cmd = npx or "npx"
    cmd = build_command(npx=npx_for_cmd, globs=globs, fix=args.fix, config_path=config_path)

    if args.dry_run:
        print("cwd:", ROOT.as_posix())
        print("globs:")
        for g in globs:
            print(f"  {g}")
        if config_path is not None:
            print("config:", config_path.as_posix())
        else:
            print("config: (none — file not present)")
        print("command:", format_command(cmd))
        if node is None or npx is None:
            missing = [name for name, found in (("node", node), ("npx", npx)) if found is None]
            print(
                f"note: missing {' and '.join(missing)} on PATH "
                "(would fail if not --dry-run)",
                file=sys.stderr,
            )
        return 0

    if node is None or npx is None:
        missing = [name for name, found in (("node", node), ("npx", npx)) if found is None]
        print(
            f"error: missing {' and '.join(missing)} on PATH; "
            "install Node.js (includes npx) to run markdownlint-cli2",
            file=sys.stderr,
        )
        return 2

    print("+", format_command(cmd))
    try:
        completed = subprocess.run(cmd, cwd=ROOT, check=False)
    except OSError as exc:
        print(f"error: failed to run npx/markdownlint-cli2: {exc}", file=sys.stderr)
        return 2
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
