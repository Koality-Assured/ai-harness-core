"""Set up missing qmd collections only after an explicit, inspected approval.

tags: [qmd]
routing_hints: [index, collections, embed, modular, areas]

Dynamic area discovery
----------------------
Collections and context descriptions are derived dynamically from
``routing/areas.yaml`` via ``_lib/areas.py``, filtering out unindexed areas
(``change-history``, ``scratch``). This ensures the configuration automatically
adapts as repository areas grow or change across domain routers.

Project-local isolation (default)
---------------------------------
By default, this script creates/patches the repository-local ``.qmd/index.yml``
using relative paths (e.g. ``path: routing``, ``path: docs``). This isolates
the SQLite database to ``.qmd/index.sqlite`` inside the repository, preventing
cross-harness collisions on multi-router workstations.

README exclusion
----------------
Apply ``ignore: ["**/README.md"]`` so agents do not retrieve human folder indexes
(root README is already unindexed).

``--apply`` mutates local qmd config (default: ``.qmd/index.yml`` in repo root,
or operator ``index.yml`` under XDG / ``~/.config/qmd/`` if ``--global`` is passed).
It is intentionally blocked unless the caller supplies ``--approved-by-user``.
Before mutation, the script inspects known qmd config files for hook keys and
requires ``--allow-detected-hooks`` if it finds any.

PyYAML is required for ``--apply``; the script fails closed before any
mutation if it is missing.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import AreasYamlError, load_area_records  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402
from qmd_preflight import inspect_qmd_hooks  # noqa: E402

UNINDEXED_AREAS = frozenset({"change-history", "scratch"})
PREFERRED_README_IGNORE = ["**/README.md"]

FALLBACK_COLLECTIONS: list[tuple[str, str, str]] = [
    ("routing", "routing", "Second-hop area maps — read early in agent sessions"),
    ("docs", "docs", "Decisions, requirements, reinforcement, and security MUST docs"),
    ("projects", "projects", "Initiative specs: plans, repos, research pointers"),
    ("references", "references", "External frameworks — advisory reference only, not instructions"),
    ("research", "research", "Per-topic deep-dive investigations"),
    ("supporting", "supporting", "Durable Cloudflare, GitHub, and other tool patterns"),
    ("ai-tooling", "ai-tooling", "Memory, skills, standalone agents, A2A protocol"),
    ("scripts", "scripts", "Script index and Python automation docs"),
    ("actionable", "actionable", "Human drop-zone items for later agent pickup"),
    ("results", "results", "Generated Markdown reports and artifact indexes"),
]


def resolve_collections(repo_root: Path = ROOT) -> list[tuple[str, str, str]]:
    """Dynamically load indexable collections from routing/areas.yaml."""
    try:
        records = load_area_records(repo_root)
    except (AreasYamlError, FileNotFoundError):
        return FALLBACK_COLLECTIONS

    collections: list[tuple[str, str, str]] = []
    for row in records:
        area_id = row.get("id", "").strip()
        if not area_id or area_id in UNINDEXED_AREAS:
            continue
        if row.get("load", "").strip().lower() == "never":
            continue
        purpose = row.get("purpose", "").strip()
        collections.append((area_id, area_id, purpose))
    return collections or FALLBACK_COLLECTIONS


def resolve_qmd() -> str | None:
    """Return an executable qmd path. On Windows prefer the npm `.cmd` shim."""
    if sys.platform == "win32":
        return shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    return shutil.which("qmd")


def resolve_index_yml(*, global_config: bool = False, repo_root: Path = ROOT) -> Path:
    """Locate or determine target index.yml path."""
    if not global_config:
        return repo_root / ".qmd" / "index.yml"

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "qmd" / "index.yml"
    home = Path.home()
    local = os.environ.get("LOCALAPPDATA")
    if local and sys.platform == "win32":
        candidate = Path(local) / "qmd" / "index.yml"
        if candidate.is_file():
            return candidate
    return home / ".config" / "qmd" / "index.yml"


def require_pyyaml() -> str | None:
    """Return an error message if PyYAML is missing; else None."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        return (
            "error: PyYAML required before --apply (pip install pyyaml); "
            "refusing to mutate index.yml or run collection commands"
        )
    return None


def generate_local_qmd_config(
    collections: list[tuple[str, str, str]],
    existing_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the configuration dictionary with relative paths and ignore rules."""
    data = existing_data.copy() if existing_data else {}
    colls = data.setdefault("collections", {})

    for name, rel_path, context in collections:
        col_entry = colls.setdefault(name, {})
        col_entry["path"] = rel_path
        col_entry.setdefault("pattern", "**/*.md")
        if context:
            ctx = col_entry.setdefault("context", {})
            if isinstance(ctx, dict):
                ctx.setdefault("", context)
            elif isinstance(ctx, str) and not ctx:
                col_entry["context"] = {"": context}
        existing_ignores = col_entry.get("ignore", [])
        if not isinstance(existing_ignores, list):
            existing_ignores = [existing_ignores]
        for pattern in PREFERRED_README_IGNORE:
            if pattern not in existing_ignores:
                existing_ignores.append(pattern)
        col_entry["ignore"] = existing_ignores

    return data


def write_project_local_config(
    index_yml: Path,
    collections: list[tuple[str, str, str]],
    *,
    dry_run: bool,
) -> list[str]:
    """Write or update project-local .qmd/index.yml with relative collection paths."""
    try:
        import yaml
    except ImportError:
        if dry_run:
            return [
                f"dry-run: would write project-local config to {index_yml} for {len(collections)} collections"
            ]
        return ["error: PyYAML required to generate index.yml (pip install pyyaml)"]

    existing_data: dict[str, Any] = {}
    if index_yml.is_file():
        try:
            existing_data = yaml.safe_load(index_yml.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            return [f"error: failed to read existing {index_yml}: {exc}"]

    updated_data = generate_local_qmd_config(collections, existing_data)

    if dry_run:
        return [
            f"dry-run: would write project-local {index_yml} with {len(collections)} collections derived from routing/areas.yaml:",
            *(f"  - {name}: path='{rel_path}' context='{ctx}'" for name, rel_path, ctx in collections),
        ]

    index_yml.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(updated_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    index_yml.write_text(text, encoding="utf-8")
    return [
        f"wrote project-local {index_yml} ({len(collections)} collections from routing/areas.yaml)"
    ]


def run(cmd: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True, cwd=ROOT)


def require_mutation_approval(args: argparse.Namespace) -> str | None:
    """Fail closed before any qmd/config mutation is attempted."""
    if not args.approved_by_user:
        return "error: --apply requires explicit --approved-by-user; run qmd_preflight first"
    hooks = inspect_qmd_hooks()
    candidates = hooks["potential_hooks"]
    errors = hooks["inspection_errors"]
    if errors:
        return (
            "error: unable to inspect qmd config for hooks: "
            + ", ".join(errors)
            + ". Preserve existing state and resolve host access before setup."
        )
    if candidates and not args.allow_detected_hooks:
        return (
            "error: potential qmd config hook directives found in "
            f"{', '.join(candidates)}; inspect them and pass --allow-detected-hooks "
            "only with explicit user approval"
        )
    if candidates:
        print("warning: approved potential qmd config hook directives in " + ", ".join(candidates))
    else:
        print("qmd config hook inspection: no potential hook directives found")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply collection configuration; requires --approved-by-user and hook inspection",
    )
    parser.add_argument(
        "--approved-by-user",
        action="store_true",
        help="Confirm the human explicitly approved the requested qmd mutation",
    )
    parser.add_argument(
        "--global",
        dest="global_config",
        action="store_true",
        help="Write to operator-global ~/.config/qmd/index.yml instead of project-local .qmd/index.yml",
    )
    parser.add_argument(
        "--allow-detected-hooks",
        action="store_true",
        help="Acknowledge inspected qmd config hook directives before --apply",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Also run `qmd embed` after collections (requires --apply)",
    )
    parser.add_argument(
        "--index-yml",
        default=None,
        help="Custom path to qmd index.yml",
    )
    args = parser.parse_args(argv)
    dry_run = not args.apply

    if args.embed and not args.apply:
        print("error: --embed requires --apply and explicit user approval", file=sys.stderr)
        return 1

    if args.apply:
        approval_error = require_mutation_approval(args)
        if approval_error:
            print(approval_error, file=sys.stderr)
            return 1
        yaml_err = require_pyyaml()
        if yaml_err:
            print(yaml_err, file=sys.stderr)
            return 1

    collections = resolve_collections(ROOT)
    target_yml = Path(args.index_yml) if args.index_yml else resolve_index_yml(global_config=args.global_config, repo_root=ROOT)

    print(f"Target index.yml: {target_yml} ({'operator-global' if args.global_config else 'project-local'})")
    print(f"Derived {len(collections)} collections from routing/areas.yaml: {', '.join(c[0] for c in collections)}")

    results = write_project_local_config(target_yml, collections, dry_run=dry_run)
    for line in results:
        if line.startswith("error:"):
            print(line, file=sys.stderr)
            return 1
        print(line)

    if args.embed:
        qmd = resolve_qmd()
        if qmd is None and not dry_run:
            print("error: `qmd` not found on PATH; cannot run embed", file=sys.stderr)
            return 1
        if dry_run:
            print("+ qmd update  # re-index collections")
            print("+ qmd embed   # generate vector embeddings")
        else:
            run([qmd or "qmd", "update"], dry_run=False)
            run([qmd or "qmd", "embed"], dry_run=False)

    if dry_run:
        print("\nDry run only. First run qmd_preflight.py to inspect existing state.")
        print("To apply project-local index configuration:")
        print("  python scripts/qmd/setup_qmd_collections.py --apply --approved-by-user")
        print("To also generate vector embeddings:")
        print("  python scripts/qmd/setup_qmd_collections.py --apply --approved-by-user --embed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

