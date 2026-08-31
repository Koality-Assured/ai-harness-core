#!/usr/bin/env python3
"""Automated synchronization, sanitation, commit, and push engine for public downstream repositories.

tags: [sync, git, export, downstream]
routing_hints: [sync-and-push, update-downstreams, multi-repo-publish, downstream-repo-update]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as DEFAULT_ROOT  # noqa: E402

from sync_public_repos import (  # noqa: E402
    DEFAULT_REPO_MAPPINGS,
    RedactionEngine,
    SyncEngine,
    build_default_rules,
)

DOWNSTREAM_REPOS = list(DEFAULT_REPO_MAPPINGS.keys())
SKILL_FAMILIES = {
    "admin",
    "aws",
    "azure",
    "benchmarks",
    "community",
    "confluence",
    "cost-layers",
    "gcp",
    "git",
    "google",
    "harness-review",
    "memory",
    "meta",
    "model-memory-operate",
    "reporting",
    "research",
    "slack",
}


@dataclasses.dataclass
class DownstreamPublishResult:
    repo: str
    path: str
    files_synced: int
    redactions: int
    status: str
    committed: bool
    pushed: bool
    commit_sha: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "path": self.path,
            "files_synced": self.files_synced,
            "redactions": self.redactions,
            "status": self.status,
            "committed": self.committed,
            "pushed": self.pushed,
            "commit_sha": self.commit_sha,
            "error": self.error,
        }


def prune_legacy_skill_dirs(skills_dir: Path) -> list[str]:
    """Remove obsolete flat skill directories from downstream skills folder."""
    pruned: list[str] = []
    if not skills_dir.exists():
        return pruned

    for child in list(skills_dir.iterdir()):
        if child.is_dir() and child.name not in SKILL_FAMILIES and not child.name.startswith("."):
            pruned.append(child.name)
            shutil.rmtree(child)
    return pruned


def run_git_cmd(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Execute a git subprocess in target directory."""
    res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def sync_and_push_downstreams(
    source_root: Path,
    dest_root: Path,
    target_repo: str | None = None,
    commit_msg: str | None = None,
    push: bool = False,
    dry_run: bool = False,
) -> list[DownstreamPublishResult]:
    """Orchestrate end-to-end sync, sanitization, git commit, and push across downstream repositories."""
    results: list[DownstreamPublishResult] = []
    rules = build_default_rules()
    engine = SyncEngine(
        source_root=source_root,
        dest_root=dest_root,
        redactor=RedactionEngine(rules=rules),
        dry_run=dry_run,
    )

    # 1. Execute sanitization and copy
    sync_report = engine.sync_all(repo_filter=target_repo)
    repos_to_process = [target_repo] if target_repo else DOWNSTREAM_REPOS

    default_commit_msg = commit_msg or "feat: synchronize updates from ai-router"

    for repo_name in repos_to_process:
        repo_dir = dest_root / repo_name
        repo_sync_res = sync_report.repos.get(repo_name)
        files_synced = repo_sync_res.files_synced if repo_sync_res else 0
        redactions = repo_sync_res.redactions_count if repo_sync_res else 0

        if not repo_dir.exists() or not (repo_dir / ".git").exists():
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="skipped_no_git_repo",
                    committed=False,
                    pushed=False,
                )
            )
            continue

        if dry_run:
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="dry_run_success",
                    committed=False,
                    pushed=False,
                )
            )
            continue

        # Prune legacy skills in agent-skills-and-tools
        if repo_name == "agent-skills-and-tools":
            prune_legacy_skill_dirs(repo_dir / "skills")

        # Check git status
        code, stdout, stderr = run_git_cmd(["git", "status", "-s"], repo_dir)
        if code != 0:
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="failed_git_status",
                    committed=False,
                    pushed=False,
                    error=stderr,
                )
            )
            continue

        if not stdout.strip():
            # Clean working tree, nothing to commit
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="clean_up_to_date",
                    committed=False,
                    pushed=False,
                )
            )
            continue

        # Stage all changes
        code, _, stderr = run_git_cmd(["git", "add", "-A"], repo_dir)
        if code != 0:
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="failed_git_add",
                    committed=False,
                    pushed=False,
                    error=stderr,
                )
            )
            continue

        # Commit changes
        code, stdout, stderr = run_git_cmd(["git", "commit", "-m", default_commit_msg], repo_dir)
        if code != 0:
            results.append(
                DownstreamPublishResult(
                    repo=repo_name,
                    path=str(repo_dir),
                    files_synced=files_synced,
                    redactions=redactions,
                    status="failed_git_commit",
                    committed=False,
                    pushed=False,
                    error=stderr,
                )
            )
            continue

        # Get latest commit sha
        _, sha, _ = run_git_cmd(["git", "rev-parse", "--short", "HEAD"], repo_dir)

        # Push to remote if requested
        pushed = False
        if push:
            code, stdout, stderr = run_git_cmd(["git", "push", "origin", "main"], repo_dir)
            if code != 0:
                results.append(
                    DownstreamPublishResult(
                        repo=repo_name,
                        path=str(repo_dir),
                        files_synced=files_synced,
                        redactions=redactions,
                        status="failed_git_push",
                        committed=True,
                        pushed=False,
                        commit_sha=sha,
                        error=stderr,
                    )
                )
                continue
            pushed = True

        results.append(
            DownstreamPublishResult(
                repo=repo_name,
                path=str(repo_dir),
                files_synced=files_synced,
                redactions=redactions,
                status="success",
                committed=True,
                pushed=pushed,
                commit_sha=sha,
            )
        )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated synchronization, sanitation, commit, and push engine for public downstream repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_ROOT,
        help="Source repository root directory (default: current repo root)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("c:/Code"),
        help="Destination root containing downstream repositories (default: c:/Code)",
    )
    parser.add_argument(
        "--repo",
        choices=DOWNSTREAM_REPOS,
        help="Specific downstream repository to process",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        help="Custom commit message for downstream repositories",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push committed changes to remote origin/main",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate synchronization without modifying downstream checkouts or git state",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON results",
    )

    args = parser.parse_args()
    results = sync_and_push_downstreams(
        source_root=args.source.resolve(),
        dest_root=args.dest.resolve(),
        target_repo=args.repo,
        commit_msg=args.message,
        push=args.push,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return 0 if all(r.status in ("success", "clean_up_to_date", "dry_run_success") for r in results) else 1

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("=" * 70)
    print("Downstream Multi-Repo Publishing Summary")
    print(f"Source: {args.source} | Dest: {args.dest} | Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    for r in results:
        status_icon = "OK" if r.status in ("success", "clean_up_to_date", "dry_run_success") else "FAIL"
        push_str = " (Pushed)" if r.pushed else ""
        sha_str = f" [{r.commit_sha}]" if r.commit_sha else ""
        print(f"[{status_icon:<4}] {r.repo:<30} Status: {r.status:<18} Synced: {r.files_synced:<3} Redactions: {r.redactions:<2}{sha_str}{push_str}")
        if r.error:
            print(f"    Error: {r.error}")
    print("=" * 70)

    has_failures = any(r.status.startswith("failed_") for r in results)
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
