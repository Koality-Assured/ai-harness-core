"""Print qmd collection/context setup commands for this repo (and optionally run them).

tags: [qmd]
routing_hints: [index, collections, embed]

README exclusion
----------------
Apply ``ignore: ["**/README.md"]`` on **this repo's** collections only (the
``COLLECTIONS`` names below) so agents do not retrieve human folder indexes
(root README is already unindexed). Other collections in the operator-global
``index.yml`` are left untouched.

qmd ignore patterns are **YAML-only** (no ``collection add`` flag). After
``collection add`` / ``context add``, this script patches the operator
``index.yml`` with ``PREFERRED_README_IGNORE`` for matching names only.

``--apply`` mutates local qmd config (operator ``index.yml`` under XDG /
``~/.config/qmd/`` / AppData, or project ``.qmd/``). That can affect
workstation-wide qmd behavior for this repo's collection names — require
human OK before ``--apply``. After scoping, other repos' collections must
remain untouched.

Supporting tool pages are kebab-case topic files (not READMEs), e.g.
``query-pattern.md``, ``pages-wrangler.md``, ``precision-retrieval.md``,
``proxy-mcp.md``, ``gh-workflow-notes.md``. Re-run ``qmd update`` after
applying ignores so README files drop out of the index.

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

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

COLLECTIONS: list[tuple[str, str, str]] = [
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

COLLECTION_NAMES = frozenset(name for name, _, _ in COLLECTIONS)
PREFERRED_README_IGNORE = ["**/README.md"]


def resolve_qmd() -> str | None:
    """Return an executable qmd path. On Windows prefer the npm `.cmd` shim."""
    if sys.platform == "win32":
        return shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    return shutil.which("qmd")


def resolve_index_yml() -> Path | None:
    """Locate operator qmd index.yml (XDG / Windows config / project-local)."""
    candidates: list[Path] = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(Path(xdg) / "qmd" / "index.yml")
    home = Path.home()
    candidates.append(home / ".config" / "qmd" / "index.yml")
    # Windows-style AppData (some installs)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "qmd" / "index.yml")
    candidates.append(ROOT / ".qmd" / "index.yml")
    for path in candidates:
        if path.is_file():
            return path
    return None


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


def apply_readme_ignore(
    index_yml: Path,
    *,
    dry_run: bool,
    collection_names: frozenset[str] = COLLECTION_NAMES,
) -> list[str]:
    """Ensure this repo's collections have ignore: PREFERRED_README_IGNORE.

    Only names in ``collection_names`` (default: COLLECTIONS) are patched.
    Other entries in the operator-global index.yml are left unchanged.
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        return [
            "error: PyYAML required to patch index.yml ignore patterns "
            "(pip install pyyaml)"
        ]

    data = yaml.safe_load(index_yml.read_text(encoding="utf-8")) or {}
    collections = data.get("collections")
    if not isinstance(collections, dict):
        return [f"error: no collections mapping in {index_yml}"]

    changed: list[str] = []
    skipped_other = 0
    for name, cfg in collections.items():
        if name not in collection_names:
            skipped_other += 1
            continue
        if not isinstance(cfg, dict):
            continue
        ignore = cfg.get("ignore")
        if ignore is None:
            ignore = []
        if not isinstance(ignore, list):
            ignore = list(ignore)
        merged = list(ignore)
        for pattern in PREFERRED_README_IGNORE:
            if pattern not in merged:
                merged.append(pattern)
                changed.append(f"{name}: add ignore {pattern!r}")
        cfg["ignore"] = merged

    scope_note = (
        f"(scoped to {len(collection_names)} repo collection name(s); "
        f"left {skipped_other} other collection(s) untouched)"
    )

    if dry_run:
        if changed:
            return (
                [f"dry-run would patch {index_yml} {scope_note}:"]
                + [f"  - {c}" for c in changed]
            )
        return [f"dry-run: ignore already set on repo collections in {index_yml} {scope_note}"]

    if not changed:
        return [f"ignore already applied in {index_yml} {scope_note}"]

    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=True)
    index_yml.write_text(text, encoding="utf-8")
    return [f"patched {index_yml} {scope_note}:"] + [f"  - {c}" for c in changed]


def run(cmd: list[str], *, dry_run: bool) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True, cwd=ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Run qmd commands and patch index.yml ignore for this repo's "
            "COLLECTIONS only (mutates local qmd config; needs human OK)"
        ),
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Also run `qmd embed` after collections (requires --apply)",
    )
    parser.add_argument(
        "--index-yml",
        default=None,
        help="Path to qmd index.yml (default: auto-detect under ~/.config/qmd/)",
    )
    args = parser.parse_args(argv)
    dry_run = not args.apply

    if args.apply:
        yaml_err = require_pyyaml()
        if yaml_err:
            print(yaml_err, file=sys.stderr)
            return 1

    qmd = resolve_qmd()
    if args.apply and qmd is None:
        print("error: `qmd` not found on PATH; install with: npm i -g @tobilu/qmd", file=sys.stderr)
        return 1

    for name, rel, context in COLLECTIONS:
        path = ROOT / rel
        run([qmd or "qmd", "collection", "add", str(path), "--name", name], dry_run=dry_run)
        run([qmd or "qmd", "context", "add", f"qmd://{name}", context], dry_run=dry_run)

    index_yml = Path(args.index_yml) if args.index_yml else resolve_index_yml()
    if index_yml is None:
        msg = (
            "warning: qmd index.yml not found; cannot apply README ignore. "
            f"Pass --index-yml or add collections then re-run. Planned ignore: "
            f"{PREFERRED_README_IGNORE} (repo COLLECTIONS only)"
        )
        print(msg, file=sys.stderr)
    else:
        for line in apply_readme_ignore(index_yml, dry_run=dry_run):
            if line.startswith("error:"):
                print(line, file=sys.stderr)
                return 1
            print(line)

    if args.embed:
        if dry_run:
            print("+ qmd embed")
            print("+ qmd update  # after ignore patch so READMEs drop from index")
        else:
            run([qmd or "qmd", "update"], dry_run=False)
            run([qmd or "qmd", "embed"], dry_run=False)

    if dry_run:
        print("\nDry run only. Re-run with --apply (and optionally --embed) after installing qmd.")
        print(
            f"README ignore {PREFERRED_README_IGNORE} is applied via YAML patch of index.yml "
            f"for this repo's COLLECTIONS only ({', '.join(sorted(COLLECTION_NAMES))}). "
            "Other collections in the operator index are untouched. "
            "--apply mutates local qmd config and needs human OK for workstation-wide effects. "
            "(Supporting kebab-case pages: query-pattern.md, pages-wrangler.md, "
            "precision-retrieval.md, proxy-mcp.md, gh-workflow-notes.md)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
