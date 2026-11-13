"""Propose generic core improvements back to Koality-Assured/ai-harness-core.

tags: [sync, harness, propose]
routing_hints: [propose-core-update, harness-core, pull-request, issue]

Allowlisted core paths only. Refuses domain overlay and instance paths.
Never auto-merges. Opt-in --create-issue is the only GitHub mutation.
--create-pr from a spoke is refused (it would leak the spoke branch).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_SYNC = Path(__file__).resolve().parent
_LIB = Path(__file__).resolve().parents[1] / "_lib"
for _p in (_SYNC, _LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from paths import resolve_repo_root  # noqa: E402
from _harness_core_protocol import (  # noqa: E402
    CORE_REPO_NAME,
    DEFAULT_ORG,
    classify_spoke_path,
    is_allowlisted_core_path,
    posix_rel,
    unique_paths,
)


class DomainPathRefused(ValueError):
    """Raised when a domain or non-core path is offered to core."""


class SpokePrRefused(ValueError):
    """Raised when --create-pr is used from a spoke working tree."""


CREATE_PR_REFUSED = (
    "--create-pr is not supported from a spoke (it would attach the spoke "
    "branch as the PR head). Use --create-issue, or copy allowlisted files "
    "into an ai-harness-core clone and open a draft PR there."
)

SPOKE_GENERATED_INDEXES: frozenset[str] = frozenset(
    {
        "routing/skill-dispatch.md",
        "routing/area-map.md",
        "routing/agent-dispatch.md",
        "routing/by-task.md",
        "scripts/script-index.md",
    }
)


def _changed_paths(spoke: Path) -> list[str]:
    """List dirty/untracked paths. Empty when the spoke is not a git repo."""
    if not (spoke / ".git").exists():
        return []
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=spoke,
        capture_output=True,
        text=True,
        check=False,
    )
    commands: list[list[str]] = []
    if head.returncode == 0:
        commands.append(["git", "diff", "--name-only", "HEAD"])
    commands.append(["git", "diff", "--name-only", "--cached"])
    commands.append(["git", "ls-files", "--others", "--exclude-standard"])
    names: list[str] = []
    for args in commands:
        result = subprocess.run(
            args,
            cwd=spoke,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git path listing failed")
        names.extend(result.stdout.splitlines())
    return unique_paths(names)


def classify_proposal_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """Split paths into allowlisted core vs refused domain/other."""
    core: list[str] = []
    refused: list[str] = []
    for rel in unique_paths(paths):
        path = posix_rel(rel)
        if (
            path in SPOKE_GENERATED_INDEXES
            or classify_spoke_path(path) != "core"
            or not is_allowlisted_core_path(path)
        ):
            refused.append(path)
        else:
            core.append(path)
    return core, refused


def propose_core_update(
    *,
    spoke: Path,
    paths: list[str] | None = None,
    title: str | None = None,
    dry_run: bool = False,
    create_pr: bool = False,
    create_issue: bool = False,
    body: str | None = None,
) -> dict[str, Any]:
    """Plan or open a core issue. Refuses domain paths. Never opens a spoke PR."""
    if create_pr:
        raise SpokePrRefused(CREATE_PR_REFUSED)
    spoke = spoke.expanduser().resolve()
    dirty = _changed_paths(spoke)
    requested = unique_paths(paths) if paths else dirty
    candidates = unique_paths([*requested, *dirty])
    core, refused = classify_proposal_paths(candidates)
    payload: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "spoke": str(spoke),
        "core_repo": f"{DEFAULT_ORG}/{CORE_REPO_NAME}",
        "title": title or "chore: propose generic harness-core update",
        "paths": core,
        "refused": refused,
        "merged": False,
        "pushed": False,
        "created_pr": False,
        "created_issue": False,
    }
    if refused:
        payload["ok"] = False
        payload["error"] = "domain_path_refused"
        raise DomainPathRefused(
            "refusing domain or non-core paths: " + ", ".join(refused)
        )
    if not core:
        payload["ok"] = False
        payload["error"] = "no_core_paths"
        raise ValueError("no allowlisted core paths to propose")

    proposal_body = body or (
        "Generic harness-core improvement from a domain spoke.\n\n"
        "Allowlisted paths only. Do not merge automatically.\n\n"
        + "\n".join(f"- `{rel}`" for rel in core)
    )
    payload["body"] = proposal_body

    if dry_run or not create_issue:
        return payload

    repo = f"{DEFAULT_ORG}/{CORE_REPO_NAME}"
    result = subprocess.run(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            payload["title"],
            "--body",
            proposal_body,
        ],
        cwd=spoke,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh issue create failed")
    payload["created_issue"] = True
    payload["url"] = result.stdout.strip()
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
        "--path",
        action="append",
        dest="paths",
        default=None,
        help="Allowlisted core path to propose (repeatable). Default: git changes.",
    )
    parser.add_argument("--title", default=None, help="Issue title")
    parser.add_argument("--body", default=None, help="Issue body")
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Refused. A PR from a spoke leaks the spoke branch. Use --create-issue.",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="Open a text-only issue on ai-harness-core (never merged, never a PR)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan only; create nothing")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args(argv)

    spoke = resolve_repo_root(args.spoke)
    try:
        payload = propose_core_update(
            spoke=spoke,
            paths=args.paths,
            title=args.title,
            dry_run=args.dry_run,
            create_pr=args.create_pr,
            create_issue=args.create_issue,
            body=args.body,
        )
    except SpokePrRefused as exc:
        err = {
            "ok": False,
            "error": "spoke_pr_refused",
            "detail": str(exc),
            "merged": False,
            "pushed": False,
        }
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    except DomainPathRefused as exc:
        err = {
            "ok": False,
            "error": "domain_path_refused",
            "detail": str(exc),
            "merged": False,
            "pushed": False,
        }
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        err = {"ok": False, "error": str(exc), "merged": False, "pushed": False}
        if args.json:
            print(json.dumps(err, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        mode = "DRY-RUN" if payload["dry_run"] else "PLAN"
        print(f"Propose core update ({mode})")
        print(f"  repo:    {payload['core_repo']}")
        print(f"  title:   {payload['title']}")
        print(f"  merged:  no")
        for rel in payload["paths"]:
            print(f"  path:    {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
