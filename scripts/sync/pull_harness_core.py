"""Pull allowlisted ai-harness-core updates into a domain spoke.

tags: [sync, harness, pull]
routing_hints: [pull-harness-core, core-update, spoke, allowlist]

Copies allowlisted core paths onto a new branch. Never auto-merges.
--dry-run does not git fetch; it plans against the existing
harness-core/<ref> remote-tracking ref.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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
    classify_spoke_path,
    current_branch,
    is_allowlisted_core_path,
    list_remotes,
    run_git,
    unique_paths,
)


def _branch_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"chore/pull-harness-core-{stamp}"


def _has_head(spoke: Path) -> bool:
    code, _, _ = run_git(["git", "rev-parse", "--verify", "HEAD"], cwd=spoke)
    return code == 0


def _diff_names(spoke: Path, core_ref: str) -> tuple[list[str], bool]:
    """Return (paths, used_unborn_fallback). Never requires a spoke commit."""
    if _has_head(spoke):
        code, stdout, stderr = run_git(
            ["git", "diff", "--name-only", "HEAD", core_ref],
            cwd=spoke,
        )
        if code != 0:
            raise RuntimeError(stderr or f"git diff against {core_ref} failed")
        return unique_paths(stdout.splitlines()), False
    code, stdout, stderr = run_git(
        ["git", "ls-tree", "-r", "--name-only", core_ref],
        cwd=spoke,
    )
    if code != 0:
        raise RuntimeError(stderr or f"git ls-tree {core_ref} failed")
    return unique_paths(stdout.splitlines()), True


def pull_harness_core(
    *,
    spoke: Path,
    ref: str = "main",
    dry_run: bool = False,
    fetch: bool = True,
) -> dict[str, Any]:
    """Apply allowlisted core updates onto a new branch. Never merges."""
    spoke = spoke.expanduser().resolve()
    remotes = list_remotes(spoke)
    if CORE_REMOTE_NAME not in remotes:
        raise RuntimeError(
            f"spoke is missing `{CORE_REMOTE_NAME}` remote; "
            "scaffold with scripts/sync/scaffold_harness.py"
        )
    core_ref = f"{CORE_REMOTE_NAME}/{ref}"
    payload: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "spoke": str(spoke),
        "ref": core_ref,
        "branch": None,
        "base_branch": current_branch(spoke),
        "updates": [],
        "skipped_domain": [],
        "merged": False,
        "pushed": False,
        "fetched": False,
    }

    if fetch:
        code, _, err = run_git(["git", "fetch", CORE_REMOTE_NAME, ref], cwd=spoke, timeout=180)
        if code != 0:
            raise RuntimeError(err or f"git fetch {CORE_REMOTE_NAME} {ref} failed")
        payload["fetched"] = True

    # dry-run still diffs if the remote-tracking ref exists locally
    code, _, _ = run_git(["git", "rev-parse", "--verify", core_ref], cwd=spoke)
    if code != 0:
        if dry_run:
            payload["warnings"] = [
                f"{core_ref} is not available locally; fetch skipped on dry-run"
            ]
            return payload
        raise RuntimeError(f"{core_ref} not found after fetch")

    names, unborn = _diff_names(spoke, core_ref)
    if unborn:
        payload.setdefault("warnings", []).append(
            "spoke has no commits yet; listed allowlisted paths from the core tree"
        )
    updates: list[str] = []
    skipped: list[str] = []
    for rel in names:
        kind = classify_spoke_path(rel)
        if kind == "core" and is_allowlisted_core_path(rel):
            updates.append(rel)
        else:
            skipped.append(rel)
    payload["updates"] = updates
    payload["skipped_domain"] = skipped

    if dry_run or not updates:
        return payload

    branch = _branch_name()
    code, _, err = run_git(["git", "checkout", "-b", branch], cwd=spoke)
    if code != 0:
        raise RuntimeError(err or f"failed to create branch {branch}")
    payload["branch"] = branch

    checkout_args = ["git", "checkout", core_ref, "--", *updates]
    code, _, err = run_git(checkout_args, cwd=spoke)
    if code != 0:
        raise RuntimeError(err or "failed to checkout allowlisted core paths")
    # Explicitly do not merge into the previous branch.
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--spoke",
        type=Path,
        default=None,
        help="Spoke repository root (default: current repo root)",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="harness-core ref to pull (default main)",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Do not git fetch; use the existing remote-tracking ref (implied by --dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report updates; do not checkout and do not git fetch. "
            "Uses the existing harness-core/<ref> remote-tracking ref. "
            "Run `git fetch harness-core` first, or omit --dry-run to fetch."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args(argv)

    spoke = resolve_repo_root(args.spoke)
    try:
        payload = pull_harness_core(
            spoke=spoke,
            ref=args.ref,
            dry_run=args.dry_run,
            fetch=False if args.dry_run else (not args.no_fetch),
        )
    except (RuntimeError, ValueError) as exc:
        err = {"ok": False, "error": str(exc), "merged": False, "pushed": False}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        mode = "DRY-RUN" if payload["dry_run"] else "LIVE"
        print(f"Pull harness core ({mode})")
        print(f"  spoke:   {payload['spoke']}")
        print(f"  ref:     {payload['ref']}")
        print(f"  merged:  no")
        if payload.get("branch"):
            print(f"  branch:  {payload['branch']}")
        for rel in payload["updates"]:
            print(f"  update:  {rel}")
        for rel in payload["skipped_domain"]:
            print(f"  skip:    {rel}")
        if not payload["updates"]:
            print("  no allowlisted core updates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
