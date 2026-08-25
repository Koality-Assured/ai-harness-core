"""Scaffolding CLI to initialize the .harness engine, config, and folder skeleton in any repository.

Do not invoke as `python -m .harness.cli.harness_init` — Python rejects dotted
relative module names. From this repository use:

    python scripts/harness_init.py --help
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from ..config import HarnessConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import HarnessConfig

DEFAULT_SKELETON_DIRS = [
    "config",
    "ai-tooling/skills",
    "ai-tooling/agents",
    "ai-tooling/a2a",
    "scratch/worktrees",
    "scratch/memory",
    "docs",
    "routing",
]


def init_harness(
    target_dir: Path | str,
    with_config: bool = True,
    with_skeletons: bool = True,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Initialize repository scaffolding with .harness configuration and folder structure."""
    target_path = Path(target_dir).resolve()
    created_dirs: list[str] = []
    created_files: list[str] = []
    skipped_files: list[str] = []

    # 1. Create skeleton directories
    if with_skeletons:
        for rel_dir in DEFAULT_SKELETON_DIRS:
            d = target_path / rel_dir
            if not d.exists():
                created_dirs.append(str(d.relative_to(target_path)).replace("\\", "/"))
                if not dry_run:
                    d.mkdir(parents=True, exist_ok=True)

    # 2. Create config/harness.config.json
    if with_config:
        cfg_dir = target_path / "config"
        cfg_file = cfg_dir / "harness.config.json"
        rel_cfg = str(cfg_file.relative_to(target_path)).replace("\\", "/")

        if cfg_file.exists() and not force:
            skipped_files.append(rel_cfg)
        else:
            default_config = HarnessConfig(repo_root=target_path)
            content = default_config.to_json(indent=2) + "\n"
            created_files.append(rel_cfg)
            if not dry_run:
                cfg_dir.mkdir(parents=True, exist_ok=True)
                cfg_file.write_text(content, encoding="utf-8")

    return {
        "target": str(target_path),
        "dry_run": dry_run,
        "created_dirs": created_dirs,
        "created_files": created_files,
        "skipped_files": skipped_files,
        "ok": True,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for harness-init."""
    parser = argparse.ArgumentParser(
        description="Initialize .harness engine, configuration, and folder skeleton in a repository."
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Target directory to initialize (default: current working directory)",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip generating config/harness.config.json",
    )
    parser.add_argument(
        "--no-skeletons",
        action="store_true",
        help="Skip creating standard skeleton directories",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display actions without making changes on disk",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args(argv)

    result = init_harness(
        target_dir=args.target,
        with_config=not args.no_config,
        with_skeletons=not args.no_skeletons,
        force=args.force,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    mode_str = " [DRY RUN]" if args.dry_run else ""
    print(f"Initialized .harness in {result['target']}{mode_str}")
    if result["created_dirs"]:
        print("\nCreated directories:")
        for d in result["created_dirs"]:
            print(f"  + {d}")
    if result["created_files"]:
        print("\nCreated files:")
        for f in result["created_files"]:
            print(f"  + {f}")
    if result["skipped_files"]:
        print("\nSkipped existing files (use --force to overwrite):")
        for f in result["skipped_files"]:
            print(f"  ~ {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
