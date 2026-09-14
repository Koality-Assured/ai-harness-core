"""Scaffold a domain harness spoke from generic ai-harness-core.

tags: [sync, harness, scaffold]
routing_hints: [scaffold-harness, domain-router, harness-core, spoke]

Clone or export the generic core, write domain overlay stubs only, and set
remotes (origin=domain repo, harness-core=ai-harness-core). Does not push.
Does not copy instance projects/research/memory or a fed-instance source.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_SYNC = Path(__file__).resolve().parent
_LIB = Path(__file__).resolve().parents[1] / "_lib"
for _p in (_SYNC, _LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from paths import resolve_repo_root  # noqa: E402
from _harness_core_protocol import (  # noqa: E402
    CORE_REMOTE_NAME,
    CORE_REPO_NAME,
    CORE_SOURCE_CHOICES,
    DEFAULT_ORG,
    DOMAIN_CHOICES,
    ORIGIN_REMOTE_NAME,
    VISIBILITY_CHOICES,
    configure_remotes,
    copy_tree_filtered,
    core_remote_url,
    default_visibility,
    detect_instance_leakage,
    domain_overlay_files,
    refuse_public_game_dev,
    ensure_initial_commit,
    git_init_if_needed,
    github_https_url,
    instance_corpus_rels,
    run_git,
    validate_org,
    validate_repo_name,
)
from sync_public_repos import SyncEngine  # noqa: E402


def _resolve_exported_core(dest_root: Path) -> Path:
    named = dest_root / CORE_REPO_NAME
    if named.is_dir() and (named / "AGENTS.md").exists():
        return named
    if (dest_root / "AGENTS.md").exists():
        return dest_root
    raise FileNotFoundError(f"harness template export not found under {dest_root}")


def export_core(source_root: Path, dest_root: Path, dry_run: bool) -> Path:
    """Export generic core via the template sync engine."""
    engine = SyncEngine(
        source_root=source_root,
        dest_root=dest_root,
        dry_run=dry_run,
    )
    report = engine.sync_all(repo_filter="ai-harness-core")
    if not report.summary.get("success", False):
        errors = []
        for res in report.repos.values():
            errors.extend(res.errors)
        raise RuntimeError("; ".join(errors) or "ai-harness-core export failed")
    if dry_run:
        return dest_root / CORE_REPO_NAME
    return _resolve_exported_core(dest_root)


def clone_core(target: Path, core_url: str, dry_run: bool) -> None:
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    code, _, err = run_git(
        ["git", "clone", "--origin", CORE_REMOTE_NAME, core_url, str(target)],
        cwd=target.parent,
        timeout=180,
    )
    if code != 0:
        raise RuntimeError(err or "git clone of ai-harness-core failed")


def scaffold_harness(
    *,
    name: str,
    target: Path,
    org: str = DEFAULT_ORG,
    visibility: str | None = None,
    domain: str = "none",
    core_source: str = "export",
    core_path: Path | None = None,
    source_root: Path | None = None,
    dry_run: bool = False,
    allow_public_game_dev: bool = False,
) -> dict[str, Any]:
    """Scaffold a domain spoke. Never pushes. Never auto-merges."""
    name = validate_repo_name(name)
    org = validate_org(org)
    if domain not in DOMAIN_CHOICES:
        raise ValueError(f"invalid --domain {domain!r}")
    if core_source not in CORE_SOURCE_CHOICES:
        raise ValueError(f"invalid --core-source {core_source!r}")
    vis = default_visibility(domain, visibility)
    refuse_public_game_dev(
        domain, vis, allow_public_game_dev=allow_public_game_dev
    )
    origin_url = github_https_url(org, name)
    core_url = core_remote_url(DEFAULT_ORG)
    overlays = domain_overlay_files(domain=domain, name=name, org=org, visibility=vis)
    target = target.expanduser().resolve()

    payload: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "name": name,
        "target": str(target),
        "org": org,
        "visibility": vis,
        "domain": domain,
        "core_source": core_source,
        "remotes": {
            ORIGIN_REMOTE_NAME: origin_url,
            CORE_REMOTE_NAME: core_url,
        },
        "overlay_files": sorted(overlays),
        "pushed": False,
        "merged": False,
        "committed": False,
        "warnings": [],
        "actions": [],
        "leaks": [],
    }

    if core_source == "path" and core_path is None:
        raise ValueError("--core-path is required when --core-source path")
    if core_source == "clone" and core_path is not None:
        raise ValueError("--core-path is only valid with --core-source path")

    if dry_run:
        payload["actions"] = [
            f"obtain-core:{core_source}",
            "write-overlays",
            "git-init",
            "configure-remotes",
            "initial-commit",
        ]
        return payload

    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"target {target} exists and is not empty")

    staging: tempfile.TemporaryDirectory[str] | None = None
    try:
        if core_source == "export":
            src = resolve_repo_root(source_root)
            staging = tempfile.TemporaryDirectory()
            exported = export_core(src, Path(staging.name), dry_run=False)
            payload["actions"].append("export-core")
            copy_tree_filtered(exported, target, dry_run=False)
        elif core_source == "clone":
            clone_core(target, core_url, dry_run=False)
            payload["actions"].append("clone-core")
        else:
            src_core = core_path.expanduser().resolve()  # type: ignore[union-attr]
            if not src_core.is_dir():
                raise FileNotFoundError(f"--core-path {src_core} does not exist")
            leaks = instance_corpus_rels(src_core)
            if leaks:
                raise ValueError(
                    "refusing fed-instance source (non-template paths): "
                    + ", ".join(leaks[:20])
                )
            copy_tree_filtered(src_core, target, dry_run=False)
            payload["actions"].append("copy-core-path")

        payload["actions"].append("write-overlays")
        write_list = []
        for rel, content in overlays.items():
            dest = target / Path(*rel.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            write_list.append(rel)
        payload["overlay_files"] = write_list

        leaks = detect_instance_leakage(target)
        payload["leaks"] = leaks
        if leaks:
            shutil.rmtree(target, ignore_errors=True)
            raise ValueError(
                "scaffold produced instance leakage; aborted: " + ", ".join(leaks)
            )

        git_init_if_needed(target)
        payload["actions"].append("git-init")
        configure_remotes(target, origin_url=origin_url, core_url=core_url)
        payload["actions"].append("configure-remotes")
        ensure_initial_commit(
            target, f"chore: scaffold {name} from ai-harness-core"
        )
        payload["actions"].append("initial-commit")
        payload["committed"] = True
        return payload
    finally:
        if staging is not None:
            staging.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", required=True, help="Spoke repository name (kebab-case)")
    parser.add_argument("--target", required=True, type=Path, help="Destination directory")
    parser.add_argument("--org", default=DEFAULT_ORG, help=f"GitHub org (default {DEFAULT_ORG})")
    parser.add_argument(
        "--visibility",
        choices=VISIBILITY_CHOICES,
        default=None,
        help="Repo visibility. Private is first-class. Default follows --domain. "
        "Public is refused for --domain game-dev unless --allow-public-game-dev.",
    )
    parser.add_argument(
        "--allow-public-game-dev",
        action="store_true",
        default=False,
        help="Break-glass: allow --visibility public for --domain game-dev. Off by default.",
    )
    parser.add_argument(
        "--domain",
        choices=DOMAIN_CHOICES,
        default="none",
        help="Domain overlay stubs only (default none)",
    )
    parser.add_argument(
        "--core-source",
        choices=CORE_SOURCE_CHOICES,
        default="export",
        help="Obtain core via local template export, clone, or existing path",
    )
    parser.add_argument(
        "--core-path",
        type=Path,
        default=None,
        help="Existing ai-harness-core checkout when --core-source path",
    )
    parser.add_argument(
        "--source",
        "--instance-root",
        type=Path,
        default=None,
        dest="source",
        help="Fed instance root used only for --core-source export",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan only; write nothing")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args(argv)

    try:
        payload = scaffold_harness(
            name=args.name,
            target=args.target,
            org=args.org,
            visibility=args.visibility,
            domain=args.domain,
            core_source=args.core_source,
            core_path=args.core_path,
            source_root=args.source,
            dry_run=args.dry_run,
            allow_public_game_dev=args.allow_public_game_dev,
        )
    except (ValueError, FileExistsError, FileNotFoundError, RuntimeError) as exc:
        err = {"ok": False, "error": str(exc), "pushed": False, "merged": False}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        mode = "DRY-RUN" if payload["dry_run"] else "LIVE"
        print(f"Scaffold harness ({mode})")
        print(f"  name:       {payload['name']}")
        print(f"  target:     {payload['target']}")
        print(f"  domain:     {payload['domain']}")
        print(f"  visibility: {payload['visibility']}")
        print(f"  origin:     {payload['remotes'][ORIGIN_REMOTE_NAME]}")
        print(f"  core:       {payload['remotes'][CORE_REMOTE_NAME]}")
        for rel in payload["overlay_files"]:
            print(f"  overlay:    {rel}")
        print("  pushed:     no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
