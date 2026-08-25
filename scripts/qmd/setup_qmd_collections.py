"""Set up missing qmd collections only after an explicit, inspected approval.

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
``~/.config/qmd/`` / AppData, or project ``.qmd/``). It is intentionally
blocked unless the caller supplies ``--approved-by-user``. Existing
collections are reused; only ``--create-missing`` can add absent collections.
Before mutation, the script inspects known qmd config files for hook keys and
requires ``--allow-detected-hooks`` if it finds any. Other operator-global
collections remain untouched.

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
from qmd_preflight import inspect_qmd_hooks  # noqa: E402

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
        if dry_run:
            return [
                "warning: PyYAML unavailable; dry run cannot inspect existing ignore patterns. "
                f"Planned ignore for repo collections: {PREFERRED_README_IGNORE}"
            ]
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


def list_collection_names(qmd: str) -> set[str]:
    """Return qmd collection names before a requested setup mutation."""
    proc = subprocess.run(
        [qmd, "collection", "list"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[-1200:]
        raise RuntimeError(
            "qmd collection list failed; preserve the existing index and resolve "
            f"access before setup. Detail: {detail}"
        )
    names: set[str] = set()
    for line in proc.stdout.splitlines():
        if "(qmd://" in line:
            names.add(line.strip().split(None, 1)[0])
    return names


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
        help=(
            "Patch this repo's existing collection config only; requires "
            "--approved-by-user and hook inspection"
        ),
    )
    parser.add_argument(
        "--approved-by-user",
        action="store_true",
        help="Confirm the human explicitly approved the requested qmd mutation",
    )
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="With --apply, add only absent repo collections and their contexts",
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
        help="Path to qmd index.yml (default: auto-detect under ~/.config/qmd/)",
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

    qmd = resolve_qmd()
    if args.apply and qmd is None:
        print("error: `qmd` not found on PATH; install with: npm i -g @tobilu/qmd", file=sys.stderr)
        return 1

    existing: set[str] = set()
    if args.apply:
        try:
            existing = list_collection_names(qmd or "qmd")
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    missing = [name for name, _, _ in COLLECTIONS if name not in existing]
    if args.apply and missing and not args.create_missing:
        print(
            "error: repo qmd collection(s) missing: "
            + ", ".join(missing)
            + ". Existing collections were not changed. Re-run with --create-missing only after "
            "reviewing qmd_preflight output and receiving explicit user approval.",
            file=sys.stderr,
        )
        return 1

    for name, rel, context in COLLECTIONS:
        path = ROOT / rel
        if args.apply and name in existing:
            print(f"= reuse existing collection {name}; no collection/context mutation")
            continue
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
        print("\nDry run only. First run qmd_preflight.py to check whether an index is reusable.")
        print(
            f"README ignore {PREFERRED_README_IGNORE} would be applied via YAML patch of index.yml "
            f"for this repo's COLLECTIONS only ({', '.join(sorted(COLLECTION_NAMES))}). "
            "Other collections in the operator index are untouched. "
            "Mutation requires --apply --approved-by-user; use --create-missing only when preflight says "
            "collections are missing. Inspect hooks before approving any mutation. "
            "(Supporting kebab-case pages: query-pattern.md, pages-wrangler.md, "
            "precision-retrieval.md, proxy-mcp.md, gh-workflow-notes.md)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
