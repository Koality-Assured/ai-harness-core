"""Create task-specific Git worktrees and verify safe post-merge cleanup.

tags: [routing, isolation, worktree]
routing_hints: [worktree, branch, concurrency, cleanup, post-merge]
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import errno
import json
import ntpath
import os
import re
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WORKTREE_BRANCH_RE = re.compile(r"^codex/[a-z0-9][a-z0-9-]{0,159}$")
COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
LOCAL_LINUX_FILESYSTEMS = frozenset({"btrfs", "ext2", "ext3", "ext4", "f2fs", "jfs", "overlay", "tmpfs", "xfs", "zfs"})


def resolve_primary_root() -> Path:
    """Resolve the common repository checkout for the current worktree."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            encoding="utf-8",
        )
    except OSError:
        return ROOT.resolve()
    if proc.returncode != 0 or not proc.stdout.strip():
        return ROOT.resolve()
    common_git = Path(proc.stdout.strip())
    if not common_git.is_absolute():
        common_git = ROOT / common_git
    return common_git.resolve().parent


PRIMARY_ROOT = resolve_primary_root()
WORKTREES = PRIMARY_ROOT / "scratch" / "worktrees"


def run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    root: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or root or PRIMARY_ROOT,
        check=check,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
    )


def run_gh(
    args: list[str],
    *,
    cwd: Path | None = None,
    root: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=cwd or root or PRIMARY_ROOT,
        check=check,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def worktrees_dir(root: Path | None = None) -> Path:
    return (root / "scratch" / "worktrees") if root else WORKTREES


def parse_worktrees(output: str) -> list[dict[str, str]]:
    """Parse `git worktree list --porcelain` without interpreting path text."""
    entries: list[dict[str, str]] = []
    entry: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if entry:
                entries.append(entry)
                entry = {}
        elif line.startswith("worktree "):
            entry["path"] = line[len("worktree "):]
        elif line.startswith("branch "):
            entry["branch"] = line[len("branch "):]
        elif line == "bare":
            entry["bare"] = "true"
        elif line == "detached":
            entry["detached"] = "true"
    if entry:
        entries.append(entry)
    return entries


def registered_worktrees(root: Path | None = None) -> list[dict[str, str]] | None:
    proc = run_git(["worktree", "list", "--porcelain"], root=root, check=False)
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        return None
    entries = parse_worktrees(proc.stdout)
    if not entries or any(not item.get("path") for item in entries):
        return None
    return entries


def _gh_json(args: list[str], *, root: Path | None = None) -> dict[str, Any]:
    proc = run_gh(args, root=root, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "gh command failed").strip()
        raise RuntimeError(detail)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("gh returned JSON that was not an object")
    return payload


def default_branch_name(root: Path | None = None) -> str:
    """Resolve GitHub's current repository default branch."""
    payload = _gh_json(["repo", "view", "--json", "defaultBranchRef"], root=root)
    default_ref = payload.get("defaultBranchRef")
    branch = default_ref.get("name") if isinstance(default_ref, dict) else None
    if not isinstance(branch, str) or not branch:
        raise RuntimeError("GitHub did not report this repository's default branch")
    validate_branch_ref(branch, root=root)
    return branch


def repository_name_with_owner(root: Path | None = None) -> str:
    """Resolve the current GitHub repository's owner/name identity."""
    payload = _gh_json(["repo", "view", "--json", "nameWithOwner"], root=root)
    name_with_owner = payload.get("nameWithOwner")
    if not isinstance(name_with_owner, str) or name_with_owner.count("/") != 1:
        raise RuntimeError("GitHub did not report this repository's owner/name")
    owner, name = name_with_owner.split("/", 1)
    if not owner or not name:
        raise RuntimeError("GitHub did not report this repository's owner/name")
    return name_with_owner


def _repository_url_identity(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        raise RuntimeError("repository URL is empty")
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"https", "ssh"} or not parsed.hostname or parsed.query or parsed.fragment:
            raise RuntimeError(f"repository URL cannot be verified safely: {value!r}")
        host = parsed.hostname
        repository_path = parsed.path.strip("/")
    else:
        match = re.fullmatch(r"(?:[^@/:]+@)?([^/:]+):([^?#]+)", value)
        if not match:
            raise RuntimeError(f"repository URL cannot be verified safely: {value!r}")
        host, repository_path = match.groups()
    if repository_path.lower().endswith(".git"):
        repository_path = repository_path[:-4]
    components = repository_path.strip("/").split("/")
    if len(components) != 2 or not all(components):
        raise RuntimeError(f"repository URL does not identify exactly one owner/repository: {value!r}")
    return host.casefold(), "/".join(components).casefold()


def _assert_origin_matches_repository(repository_url: str, repository_name: str, *, root: Path | None) -> None:
    proc = run_git(["remote", "get-url", "--all", "origin"], root=root, check=False)
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        detail = (proc.stderr or proc.stdout or "Git did not report origin's fetch URL").strip()
        raise RuntimeError(f"could not verify origin against the PR base repository: {detail}")
    urls = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(urls) != 1:
        raise RuntimeError("origin must have exactly one fetch URL for verified post-merge cleanup")
    origin_identity = _repository_url_identity(urls[0])
    base_identity = _repository_url_identity(repository_url)
    if origin_identity != base_identity:
        raise RuntimeError(
            f"origin {urls[0]!r} does not identify the PR base repository {repository_name!r}"
        )
    if base_identity[1] != repository_name.casefold():
        raise RuntimeError("PR base repository URL and owner/name identity disagree")


def validate_branch_ref(branch: str, *, root: Path | None = None) -> None:
    if not branch or branch.startswith("-") or "\x00" in branch:
        raise RuntimeError(f"invalid branch name: {branch!r}")
    proc = run_git(["check-ref-format", "--branch", branch], root=root, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"invalid branch name: {branch!r}")


@contextmanager
def fetch_branch(branch: str, *, root: Path | None = None) -> Iterator[str]:
    """Fetch a branch to a unique temporary ref and yield its pinned commit OID.

    The temporary ref avoids the repository-wide mutable FETCH_HEAD shared by
    concurrent lifecycle operations. Cleanup uses compare-and-delete so it can
    remove only the exact ref value this operation fetched.
    """
    validate_branch_ref(branch, root=root)
    temporary_ref = f"refs/codex/worktree-fetch/{uuid.uuid4().hex}"
    fetched_oid: str | None = None
    try:
        proc = run_git(
            ["fetch", "--no-tags", "--no-write-fetch-head", "origin", f"+refs/heads/{branch}:{temporary_ref}"],
            root=root,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "git fetch failed").strip()
            raise RuntimeError(f"could not fetch origin/{branch}: {detail}")

        rev = run_git(["rev-parse", "--verify", f"{temporary_ref}^{{commit}}"], root=root, check=False)
        fetched_oid = (rev.stdout or "").strip()
        if rev.returncode != 0 or not COMMIT_RE.fullmatch(fetched_oid):
            raise RuntimeError(f"could not resolve fetched commit for origin/{branch}")
        yield fetched_oid
    finally:
        # A failed fetch can still leave its destination ref behind. Resolve
        # only our random ref, then delete it only if it still has that OID.
        if fetched_oid is None:
            rev = run_git(["rev-parse", "--verify", f"{temporary_ref}^{{commit}}"], root=root, check=False)
            candidate = (rev.stdout or "").strip()
            if rev.returncode == 0 and COMMIT_RE.fullmatch(candidate):
                fetched_oid = candidate
        if fetched_oid is not None:
            removed = run_git(["update-ref", "-d", temporary_ref, fetched_oid], root=root, check=False)
            if removed.returncode != 0:
                detail = (removed.stderr or removed.stdout or "could not remove temporary fetch ref").strip()
                if sys.exc_info()[0] is None:
                    raise RuntimeError(f"could not remove temporary fetch ref {temporary_ref}: {detail}")
                print(f"warning: preserved temporary fetch ref {temporary_ref}: {detail}", file=sys.stderr)


def _new_worktree_identity(slug: str) -> tuple[str, str]:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()
    worktree_id = f"{slug}-{stamp}-{uuid.uuid4().hex[:8]}"
    return worktree_id, f"codex/{worktree_id}"


def _print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value)}")
        else:
            print(f"{key}: {value}")


def cmd_create(slug: str, *, dry_run: bool = False, as_json: bool = False, root: Path | None = None) -> int:
    if not SLUG_RE.fullmatch(slug):
        print(f"error: task slug must be kebab-case [a-z0-9-], got {slug!r}", file=sys.stderr)
        return 2
    repo_root = root or PRIMARY_ROOT
    try:
        base_branch = default_branch_name(repo_root)
        worktree_id, branch = _new_worktree_identity(slug)
        path = worktrees_dir(root) / worktree_id
        if path.exists():
            raise RuntimeError(f"generated worktree path already exists: {path}")
        if not WORKTREE_BRANCH_RE.fullmatch(branch):
            raise RuntimeError(f"generated branch name is invalid: {branch}")
        if dry_run:
            _print_payload(
                {"ok": True, "dry_run": True, "task_slug": slug, "worktree_id": worktree_id,
                 "path": str(path), "branch": branch, "base_branch": base_branch},
                as_json,
            )
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        with fetch_branch(base_branch, root=repo_root) as base_oid:
            add = run_git(["worktree", "add", "-b", branch, str(path), base_oid], root=repo_root, check=False)
            if add.returncode != 0:
                detail = (add.stderr or add.stdout or "git worktree add failed").strip()
                print(
                    f"error: could not create worktree {path} on {branch}: {detail}. "
                    "Any partial path or branch was left untouched for inspection.",
                    file=sys.stderr,
                )
                return 1
            entries = registered_worktrees(repo_root)
            expected_path = path.resolve()
            match = next((item for item in entries or [] if item.get("branch") == f"refs/heads/{branch}"), None)
            if not match or Path(match["path"]).resolve() != expected_path:
                print(
                    f"error: Git created the worktree but its registration could not be verified; "
                    f"preserving {path} and {branch} for inspection",
                    file=sys.stderr,
                )
                return 1
        _print_payload(
            {"ok": True, "task_slug": slug, "worktree_id": worktree_id, "path": str(path),
             "branch": branch, "base_branch": base_branch},
            as_json,
        )
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_list(*, as_json: bool = False, root: Path | None = None) -> int:
    entries = registered_worktrees(root)
    if entries is None:
        print("error: could not verify Git worktree registrations", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps({"worktrees": entries}, indent=2))
    else:
        for item in entries:
            print(f"{item.get('branch', '(detached)')}\t{item['path']}")
    return 0


def _status_entries(worktree: Path, *, root: Path | None = None) -> list[tuple[str, str]]:
    proc = run_git(
        ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "--no-renames", "-z"],
        cwd=worktree,
        root=root,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git status failed").strip()
        raise RuntimeError(f"could not read worktree status: {detail}")
    records: list[tuple[str, str]] = []
    for record in (proc.stdout or "").split("\x00"):
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise RuntimeError(f"git status returned malformed porcelain data: {record!r}")
        records.append((record[:2], record[3:]))
    return records


def _render_local_data(entries: list[tuple[str, str]]) -> str:
    categories: dict[str, list[str]] = {"tracked changes": [], "untracked": [], "ignored": []}
    for code, path in entries:
        category = "untracked" if code == "??" else "ignored" if code == "!!" else "tracked changes"
        categories[category].append(path)
    lines = ["worktree contains local data; nothing was changed:"]
    for category, paths in categories.items():
        if paths:
            lines.append(f"  {category} ({len(paths)}):")
            lines.extend(f"    {json.dumps(path)}" for path in paths)
    return "\n".join(lines)


def _worktree_for_branch(branch: str, *, root: Path | None = None) -> Path:
    if not WORKTREE_BRANCH_RE.fullmatch(branch):
        raise RuntimeError("--branch must name a task branch created under codex/<task-id>")
    entries = registered_worktrees(root)
    if entries is None:
        raise RuntimeError("could not verify Git worktree registrations")
    matches = [item for item in entries if item.get("branch") == f"refs/heads/{branch}"]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one registered worktree for {branch}; found {len(matches)}")
    raw_path = matches[0].get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise RuntimeError(f"Git returned a malformed worktree registration for {branch}")
    unresolved_path = Path(raw_path)
    if not unresolved_path.is_absolute() or unresolved_path.is_symlink():
        raise RuntimeError(f"Git returned a relative or redirected worktree path for {branch}: {raw_path!r}")
    _ensure_no_redirect_components(unresolved_path, label="registered checkout")
    path = unresolved_path.resolve()
    managed_root = worktrees_dir(root).resolve()
    if os.path.normcase(str(path.parent)) != os.path.normcase(str(managed_root)):
        raise RuntimeError(f"refusing cleanup outside a direct task worktree under {managed_root}: {path}")
    if not path.is_dir():
        raise RuntimeError(f"registered worktree path is missing or not a directory: {path}")
    return path


def _verify_merged_pr(
    branch: str | None,
    pr_number: int,
    *,
    root: Path | None = None,
) -> tuple[str, str, str, str, str]:
    if pr_number <= 0:
        raise RuntimeError("--pr must be a positive PR number")
    if branch is not None and not WORKTREE_BRANCH_RE.fullmatch(branch):
        raise RuntimeError("--branch must name a task branch created under codex/<task-id>")

    default_branch = default_branch_name(root)
    current_repository = repository_name_with_owner(root)

    pr = _gh_json(
        [
            "pr",
            "view",
            str(pr_number),
            "--json",
            "state,mergedAt,baseRefName,headRefName,headRepository,isCrossRepository,mergeCommit,url",
        ],
        root=root,
    )
    if pr.get("state") != "MERGED" or not pr.get("mergedAt"):
        raise RuntimeError(f"PR #{pr_number} is not merged")
    if pr.get("isCrossRepository") is not False:
        raise RuntimeError(f"PR #{pr_number} is cross-repository or its head repository could not be verified")
    head_repository = pr.get("headRepository")
    head_repository_name = head_repository.get("nameWithOwner") if isinstance(head_repository, dict) else None
    if not isinstance(head_repository_name, str) or not head_repository_name:
        raise RuntimeError(f"PR #{pr_number} has no verifiable head repository")
    if head_repository_name.casefold() != current_repository.casefold():
        raise RuntimeError(
            f"PR #{pr_number} head repository {head_repository_name!r} does not match current repository "
            f"{current_repository!r}"
        )
    head_branch = pr.get("headRefName")
    if not isinstance(head_branch, str) or not WORKTREE_BRANCH_RE.fullmatch(head_branch):
        raise RuntimeError(f"PR #{pr_number} head branch is not a valid codex task branch: {head_branch!r}")
    if branch is not None and head_branch != branch:
        raise RuntimeError(
            f"PR #{pr_number} head branch {head_branch!r} does not match {branch!r}"
        )
    if pr.get("baseRefName") != default_branch:
        raise RuntimeError(
            f"PR #{pr_number} targets {pr.get('baseRefName')!r}, not repository default branch {default_branch!r}"
        )
    merge_commit = pr.get("mergeCommit")
    merge_oid = merge_commit.get("oid") if isinstance(merge_commit, dict) else None
    if not isinstance(merge_oid, str) or not COMMIT_RE.fullmatch(merge_oid):
        raise RuntimeError(f"PR #{pr_number} has no valid merge commit")
    api_pr = _gh_json(["api", f"repos/{current_repository}/pulls/{pr_number}"], root=root)
    base = api_pr.get("base")
    base_repository = base.get("repo") if isinstance(base, dict) else None
    base_repository_name = base_repository.get("full_name") if isinstance(base_repository, dict) else None
    base_repository_url = base_repository.get("clone_url") if isinstance(base_repository, dict) else None
    head = api_pr.get("head")
    head_oid = head.get("sha") if isinstance(head, dict) else None
    if not isinstance(base_repository_name, str) or not base_repository_name:
        raise RuntimeError(f"PR #{pr_number} API response has no verifiable base repository")
    if base_repository_name.casefold() != current_repository.casefold():
        raise RuntimeError(
            f"PR #{pr_number} base repository {base_repository_name!r} does not match current repository "
            f"{current_repository!r}"
        )
    if not isinstance(base_repository_url, str) or not base_repository_url:
        raise RuntimeError(f"PR #{pr_number} API response has no verifiable base repository URL")
    _assert_origin_matches_repository(base_repository_url, base_repository_name, root=root)
    if not isinstance(head_oid, str) or not COMMIT_RE.fullmatch(head_oid):
        raise RuntimeError(f"PR #{pr_number} API response has no valid exact head commit SHA")
    with fetch_branch(default_branch, root=root) as default_oid:
        ancestry = run_git(["merge-base", "--is-ancestor", merge_oid, default_oid], root=root, check=False)
        if ancestry.returncode == 1:
            raise RuntimeError(f"PR #{pr_number} merge commit is not reachable from origin/{default_branch}")
        if ancestry.returncode != 0:
            detail = (ancestry.stderr or ancestry.stdout or "git ancestry check failed").strip()
            raise RuntimeError(f"could not verify PR merge commit on origin/{default_branch}: {detail}")
    return head_branch, default_branch, merge_oid, head_oid, str(pr.get("url") or f"PR #{pr_number}")


def _move_cwd_outside_worktree(worktree: Path, repo_root: Path) -> None:
    """Move the caller out before relocating a worktree checkout."""
    worktree_path = worktree.resolve()
    current_path = Path.cwd().resolve()
    try:
        current_is_inside = os.path.normcase(os.path.commonpath((str(current_path), str(worktree_path)))) == os.path.normcase(str(worktree_path))
    except ValueError:
        current_is_inside = False
    if not current_is_inside:
        return

    fallback = repo_root.resolve()
    try:
        fallback_is_inside = os.path.normcase(os.path.commonpath((str(fallback), str(worktree_path)))) == os.path.normcase(str(worktree_path))
    except ValueError:
        fallback_is_inside = False
    if fallback_is_inside:
        raise RuntimeError(f"cannot remove {worktree_path} while the cleanup repository root is inside it")
    os.chdir(fallback)


def _git_output(args: list[str], *, cwd: Path, root: Path | None = None) -> str:
    proc = run_git(args, cwd=cwd, root=root, check=False)
    if proc.returncode != 0 or not isinstance(proc.stdout, str) or not proc.stdout.strip():
        detail = (proc.stderr or proc.stdout or "Git returned no path").strip()
        raise RuntimeError(f"could not verify {' '.join(args)}: {detail}")
    return proc.stdout.strip()


def _same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(first.resolve()))) == os.path.normcase(
        os.path.normpath(str(second.resolve()))
    )


def _ensure_no_redirect_components(path: Path, *, label: str) -> None:
    """Reject symlinks and Windows reparse points in the path as spelled on disk."""
    if os.name == "nt" and path.anchor.startswith("\\\\"):
        raise RuntimeError(f"refusing a UNC {label} path: {path}")
    absolute = path if path.is_absolute() else Path.cwd() / path
    parts = absolute.parts
    if not parts:
        raise RuntimeError(f"refusing an empty {label} path")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)

    def inspect(candidate: Path) -> None:
        try:
            info = os.lstat(candidate)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise RuntimeError(f"could not inspect {label} path component {candidate}: {exc}") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or (reparse_flag and attributes & reparse_flag):
            raise RuntimeError(f"refusing redirected {label} path component: {candidate}")

    current = Path(parts[0])
    inspect(current)
    for component in parts[1:]:
        if component == "..":
            current = current.parent
            continue
        if component == ".":
            continue
        current = current / component
        inspect(current)


def _resolve_pointer(raw: str, *, base: Path, label: str) -> Path:
    value = raw.strip()
    if not value:
        raise RuntimeError(f"{label} pointer is empty")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    _ensure_no_redirect_components(candidate, label=label)
    try:
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"{label} pointer does not resolve: {value!r}: {exc}") from exc


def _verified_worktree_admin(path: Path, branch: str, *, root: Path) -> dict[str, Any]:
    """Resolve and validate one linked worktree's exact Git administration directory."""
    _ensure_no_redirect_components(path, label="task checkout")
    checkout = path.resolve(strict=True)
    if checkout.is_symlink() or not checkout.is_dir():
        raise RuntimeError(f"refusing a non-directory or redirected task checkout: {checkout}")

    git_file = checkout / ".git"
    _ensure_no_redirect_components(git_file, label="checkout Git pointer")
    if git_file.is_symlink() or not git_file.is_file():
        raise RuntimeError(f"task checkout has no regular linked-worktree .git file: {git_file}")
    git_pointer = git_file.read_text(encoding="utf-8").strip()
    if not git_pointer.startswith("gitdir:"):
        raise RuntimeError(f"task checkout .git file has an invalid pointer: {git_file}")
    checkout_gitdir_text = git_pointer[len("gitdir:"):].strip()
    checkout_gitdir = _resolve_pointer(checkout_gitdir_text, base=checkout, label="checkout gitdir")

    gitdir_raw = Path(_git_output(["rev-parse", "--absolute-git-dir"], cwd=checkout, root=root))
    common_raw = Path(
        _git_output(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=checkout, root=root)
    )
    if gitdir_raw.is_symlink() or common_raw.is_symlink():
        raise RuntimeError("Git returned a redirected worktree or common directory")
    _ensure_no_redirect_components(gitdir_raw, label="Git admin")
    _ensure_no_redirect_components(common_raw, label="common Git directory")
    gitdir = gitdir_raw.resolve(strict=True)
    common = common_raw.resolve(strict=True)
    if not _same_path(checkout_gitdir, gitdir):
        raise RuntimeError(f"checkout .git pointer does not match Git's absolute gitdir: {checkout}")

    worktrees_admin = common / "worktrees"
    if not _same_path(gitdir.parent, worktrees_admin) or gitdir.is_symlink() or not gitdir.is_dir():
        raise RuntimeError(f"task checkout is not backed by one direct linked-worktree admin directory: {gitdir}")

    admin_gitdir_file = gitdir / "gitdir"
    commondir_file = gitdir / "commondir"
    _ensure_no_redirect_components(admin_gitdir_file, label="admin gitdir pointer")
    _ensure_no_redirect_components(commondir_file, label="admin commondir pointer")
    if admin_gitdir_file.is_symlink() or not admin_gitdir_file.is_file():
        raise RuntimeError(f"linked-worktree admin directory has no regular gitdir pointer: {admin_gitdir_file}")
    if commondir_file.is_symlink() or not commondir_file.is_file():
        raise RuntimeError(f"linked-worktree admin directory has no regular commondir pointer: {commondir_file}")
    admin_gitdir_text = admin_gitdir_file.read_text(encoding="utf-8").strip()
    commondir_text = commondir_file.read_text(encoding="utf-8").strip()
    admin_gitdir_target = _resolve_pointer(admin_gitdir_text, base=gitdir, label="admin gitdir")
    commondir_target = _resolve_pointer(commondir_text, base=gitdir, label="admin commondir")
    if not _same_path(admin_gitdir_target, git_file):
        raise RuntimeError(f"linked-worktree admin gitdir pointer does not identify {git_file}")
    if not _same_path(commondir_target, common):
        raise RuntimeError(f"linked-worktree commondir pointer does not identify {common}")

    active_branch = _git_output(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=checkout, root=root)
    if active_branch != branch:
        raise RuntimeError(f"task checkout is on {active_branch!r}, not the verified PR branch {branch!r}")
    head_oid = _git_output(["rev-parse", "HEAD"], cwd=checkout, root=root)
    if not COMMIT_RE.fullmatch(head_oid):
        raise RuntimeError(f"task checkout returned an invalid HEAD object id: {head_oid!r}")

    worktree_config_enabled = _worktree_config_extension_enabled(root=root)
    config_worktree = gitdir / "config.worktree"
    _ensure_no_redirect_components(config_worktree, label="per-worktree config")
    reported_config = Path(_git_output(["rev-parse", "--git-path", "config.worktree"], cwd=checkout, root=root))
    if not reported_config.is_absolute():
        reported_config = checkout / reported_config
    _ensure_no_redirect_components(reported_config, label="reported per-worktree config")
    if not _same_path(reported_config, config_worktree):
        raise RuntimeError(f"Git's per-worktree config path is ambiguous: {reported_config}")
    if os.path.lexists(config_worktree):
        raise RuntimeError(f"per-worktree config is present and may contain path-sensitive values: {config_worktree}")

    _assert_no_common_core_worktree(root=root)
    shared_index_relative_path = _shared_index_relative_path(checkout, gitdir, root=root)

    return {
        "checkout": checkout,
        "checkout_git_file": git_file,
        "checkout_git_pointer": git_pointer,
        "gitdir": gitdir,
        "gitdir_pointer": admin_gitdir_text,
        "commondir_pointer": commondir_text,
        "common": common,
        "branch": active_branch,
        "head_oid": head_oid,
        "worktree_config_enabled": worktree_config_enabled,
        "shared_index_relative_path": shared_index_relative_path,
    }


def _worktree_config_extension_enabled(*, root: Path) -> bool:
    proc = run_git(
        ["config", "--local", "--bool", "--get", "extensions.worktreeConfig"],
        root=root,
        check=False,
    )
    if proc.returncode == 1:
        return False
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        detail = (proc.stderr or proc.stdout or "Git config lookup failed").strip()
        raise RuntimeError(f"could not inspect extensions.worktreeConfig; preserving checkout: {detail}")
    value = proc.stdout.strip().lower()
    if value not in {"true", "false"}:
        raise RuntimeError(f"extensions.worktreeConfig has an ambiguous value: {value!r}")
    return value == "true"


def _assert_no_common_core_worktree(*, root: Path) -> None:
    proc = run_git(["config", "--local", "--get-all", "core.worktree"], root=root, check=False)
    if proc.returncode == 1:
        return
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        detail = (proc.stderr or proc.stdout or "Git config lookup failed").strip()
        raise RuntimeError(f"could not inspect local core.worktree config; preserving checkout: {detail}")
    if proc.stdout.strip():
        raise RuntimeError("local core.worktree is configured; refusing path-sensitive Git metadata relocation")


def _shared_index_relative_path(checkout: Path, gitdir: Path, *, root: Path) -> str | None:
    proc = run_git(["rev-parse", "--shared-index-path"], cwd=checkout, root=root, check=False)
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        detail = (proc.stderr or proc.stdout or "Git did not inspect the shared index path").strip()
        raise RuntimeError(f"could not inspect split-index metadata; preserving checkout: {detail}")

    shared_files = sorted(gitdir.glob("sharedindex.*"))
    for shared_file in shared_files:
        _ensure_no_redirect_components(shared_file, label="split-index shared file")
        if shared_file.is_symlink() or not shared_file.is_file():
            raise RuntimeError(f"split-index metadata is not a regular file: {shared_file}")

    value = proc.stdout.strip()
    if not value:
        return None
    raw_path = Path(value)
    if not raw_path.is_absolute():
        raw_path = gitdir / raw_path
    _ensure_no_redirect_components(raw_path, label="split-index shared file")
    try:
        resolved = raw_path.resolve(strict=True)
        relative = resolved.relative_to(gitdir)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"split-index shared file is missing or outside its Git admin directory: {raw_path}") from exc
    if len(relative.parts) != 1 or not relative.name.startswith("sharedindex.") or not any(
        _same_path(resolved, item) for item in shared_files
    ):
        raise RuntimeError(f"split-index shared file is ambiguous: {resolved}")
    return relative.as_posix()


def _assert_worktree_metadata_state(gitdir: Path, expected: dict[str, Any], *, root: Path) -> None:
    """Reject path-sensitive per-worktree config and verify split-index files survived relocation."""
    enabled = _worktree_config_extension_enabled(root=root)
    if enabled != expected.get("worktree_config_enabled"):
        raise RuntimeError("extensions.worktreeConfig changed during archive recovery; preserving checkout")
    config_worktree = gitdir / "config.worktree"
    _ensure_no_redirect_components(config_worktree, label="per-worktree config")
    if os.path.lexists(config_worktree):
        raise RuntimeError(f"per-worktree config appeared during archive recovery; preserving it: {config_worktree}")
    _assert_no_common_core_worktree(root=root)

    relative = expected.get("shared_index_relative_path")
    if relative is not None:
        shared_index = gitdir / relative
        _ensure_no_redirect_components(shared_index, label="split-index shared file")
        if shared_index.is_symlink() or not shared_index.is_file():
            raise RuntimeError(f"split-index shared file is missing or redirected: {shared_index}")


def _ensure_no_initialized_submodules(checkout: Path, *, root: Path) -> None:
    proc = run_git(["submodule", "status", "--recursive"], cwd=checkout, root=root, check=False)
    if proc.returncode != 0 or not isinstance(proc.stdout, str):
        detail = (proc.stderr or proc.stdout or "git submodule status failed").strip()
        raise RuntimeError(f"could not inspect submodules; preserving checkout: {detail}")
    initialized = [line for line in proc.stdout.splitlines() if line and not line.startswith("-")]
    if initialized:
        raise RuntimeError(
            "initialized submodules require manual cleanup; preserving checkout: "
            + "; ".join(initialized)
        )


def _ensure_same_volume(paths: list[Path]) -> None:
    _ensure_local_atomic_volume(paths)
    try:
        devices = {os.stat(path).st_dev for path in paths}
    except OSError as exc:
        raise RuntimeError(f"could not verify archive move filesystem boundaries: {exc}") from exc
    if len(devices) != 1:
        raise RuntimeError("checkout, Git metadata, and retained archive must be on the same volume")


def _windows_drive_type(root: str) -> int:
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_drive_type = kernel32.GetDriveTypeW
        get_drive_type.argtypes = [ctypes.c_wchar_p]
        get_drive_type.restype = ctypes.c_uint
        return int(get_drive_type(root))
    except (AttributeError, OSError) as exc:
        raise RuntimeError(f"could not determine whether {root!r} is a local Windows drive") from exc


def _linux_mount(path: Path) -> tuple[str, str, str]:
    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        target = os.path.abspath(str(path))
    except OSError as exc:
        raise RuntimeError(f"could not inspect Linux mount information for {path}: {exc}") from exc

    def unescape(value: str) -> str:
        return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match.group(1), 8)), value)

    candidates: list[tuple[int, str, str, str]] = []
    for line in mountinfo.splitlines():
        left, separator, right = line.partition(" - ")
        fields = left.split()
        filesystem = right.split()[0] if separator and right.split() else ""
        if len(fields) < 5 or not filesystem:
            continue
        mountpoint = unescape(fields[4])
        if target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
            candidates.append((len(mountpoint), fields[0], mountpoint, filesystem.lower()))
    if not candidates:
        raise RuntimeError(f"could not identify the Linux mount for {path}; refusing archive moves")
    _, mount_id, mountpoint, filesystem = max(candidates)
    return mount_id, mountpoint, filesystem


def _ensure_local_atomic_volume(paths: list[Path]) -> None:
    """Fail closed when the platform cannot prove local same-mount rename semantics."""
    if os.name == "nt":
        roots: set[str] = set()
        for path in paths:
            drive, _ = ntpath.splitdrive(os.path.abspath(str(path)))
            if not drive or drive.startswith("\\\\"):
                raise RuntimeError(f"UNC or unrooted path cannot be archived safely: {path}")
            root = drive + "\\"
            drive_type = _windows_drive_type(root)
            if drive_type == 4:
                raise RuntimeError(f"network drive archives are blocked: {root}")
            if drive_type != 3:
                raise RuntimeError(f"could not prove fixed local-drive rename semantics for {root}")
            roots.add(ntpath.normcase(drive))
        if len(roots) != 1:
            raise RuntimeError("checkout, Git metadata, and retained archive must use one local Windows drive")
        return

    if sys.platform.startswith("linux"):
        mounts = [_linux_mount(path) for path in paths]
        ids = {mount_id for mount_id, _, _ in mounts}
        if len(ids) != 1:
            raise RuntimeError("archive paths span Linux mount boundaries; atomic rename is not guaranteed")
        for _, mountpoint, filesystem in mounts:
            if filesystem not in LOCAL_LINUX_FILESYSTEMS:
                raise RuntimeError(
                    f"unknown or unapproved Linux filesystem {filesystem!r} at {mountpoint} cannot be archived safely"
                )
        return

    raise RuntimeError(
        f"cannot verify local same-volume atomic rename semantics on {sys.platform}; preserving the worktree"
    )


def _archive_preflight(path: Path, branch: str, *, head_ref_oid: str, root: Path) -> dict[str, Any]:
    """Read-only validation shared by preview and apply before archive creation."""
    _ensure_no_redirect_components(path, label="task checkout")
    checkout = path.resolve(strict=True)
    admin = _verified_worktree_admin(checkout, branch, root=root)
    if admin["head_oid"] != head_ref_oid:
        raise RuntimeError(
            f"task checkout HEAD {admin['head_oid']} does not match the merged PR head SHA {head_ref_oid}; preserving checkout"
        )
    _ensure_no_initialized_submodules(checkout, root=root)

    lock_file = admin["gitdir"] / "locked"
    _ensure_no_redirect_components(lock_file, label="worktree lock")
    if os.path.lexists(lock_file):
        raise RuntimeError(f"worktree is already locked; preserving it: {checkout}")

    archive_parent = admin["common"] / "ai-router-worktree-archives"
    _ensure_no_redirect_components(archive_parent, label="archive root")
    if archive_parent.exists() and not archive_parent.is_dir():
        raise RuntimeError(f"refusing redirected or invalid archive parent: {archive_parent}")
    if archive_parent.exists():
        resolved_parent = archive_parent.resolve(strict=True)
    else:
        resolved_parent = archive_parent.resolve(strict=False)
    expected_parent = admin["common"] / "ai-router-worktree-archives"
    if not _same_path(resolved_parent, expected_parent):
        raise RuntimeError(f"archive parent does not resolve to the validated common Git directory: {resolved_parent}")
    admin_root = (admin["common"] / "worktrees").resolve()
    if resolved_parent == admin_root or resolved_parent.is_relative_to(admin_root):
        raise RuntimeError("archive destination must be outside Git's registered worktrees directory")

    volume_paths = [checkout, admin["gitdir"], admin["common"]]
    if archive_parent.exists():
        volume_paths.append(resolved_parent)
    _ensure_same_volume(volume_paths)
    return {**admin, "archive_parent": resolved_parent}


def _write_recovery_manifest(path: Path, payload: dict[str, Any], *, create: bool = False) -> None:
    content = json.dumps(payload, indent=2) + "\n"
    if create:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return

    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _move_directory(source: Path, destination: Path) -> None:
    if destination.exists():
        raise RuntimeError(f"archive destination already exists; refusing to overwrite: {destination}")
    try:
        os.replace(source, destination)
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            raise RuntimeError(f"cross-volume archive move refused: {source} -> {destination}") from exc
        raise


def _write_pointer(path: Path, value: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"refusing to rewrite a missing or redirected Git pointer: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value.rstrip("\r\n") + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _same_pointer_text(path: Path, expected: str) -> bool:
    return path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8").strip() == expected.strip()


def _archive_ref_name(pr_number: int, head_oid: str) -> str:
    if pr_number <= 0 or not COMMIT_RE.fullmatch(head_oid):
        raise RuntimeError("cannot name an archive ref without a valid PR number and head commit")
    return f"refs/ai-router/worktree-archives/pr-{pr_number}/{head_oid.lower()}"


def _archive_ref_oid(ref: str, *, root: Path) -> str | None:
    checked = run_git(["check-ref-format", ref], root=root, check=False)
    if checked.returncode != 0:
        raise RuntimeError(f"archive ref name is invalid: {ref}")
    symbolic = run_git(["symbolic-ref", "--quiet", ref], root=root, check=False)
    if symbolic.returncode == 0:
        raise RuntimeError(f"archive ref must be a direct ref, not symbolic: {ref}")
    if symbolic.returncode != 1:
        detail = (symbolic.stderr or symbolic.stdout or "Git could not inspect archive ref type").strip()
        raise RuntimeError(f"could not inspect archive ref {ref}: {detail}")
    result = run_git(["rev-parse", "--verify", "--quiet", ref], root=root, check=False)
    if result.returncode == 1 and not result.stdout.strip():
        return None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Git could not inspect the archive ref").strip()
        raise RuntimeError(f"could not inspect archive ref {ref}: {detail}")
    oid = result.stdout.strip().lower()
    if not COMMIT_RE.fullmatch(oid):
        raise RuntimeError(f"Git returned an invalid object ID for archive ref {ref}")
    return oid


def _validate_archive_ref(ref: str, head_oid: str, *, root: Path, allow_missing: bool = False) -> bool:
    current = _archive_ref_oid(ref, root=root)
    if current is None:
        if allow_missing:
            return False
        raise RuntimeError(f"persistent archive ref is missing: {ref}")
    if current != head_oid.lower():
        raise RuntimeError(f"persistent archive ref does not point to the recorded head commit: {ref}")
    commit = run_git(["cat-file", "-e", f"{head_oid}^{{commit}}"], root=root, check=False)
    if commit.returncode != 0:
        raise RuntimeError(f"persistent archive ref points to an unavailable commit: {head_oid}")
    return True


def _ensure_archive_ref(ref: str, head_oid: str, *, root: Path) -> None:
    if _validate_archive_ref(ref, head_oid, root=root, allow_missing=True):
        return
    zero_oid = "0" * len(head_oid)
    created = run_git(["update-ref", ref, head_oid, zero_oid], root=root, check=False)
    if created.returncode != 0 and not _validate_archive_ref(ref, head_oid, root=root, allow_missing=True):
        detail = (created.stderr or created.stdout or "Git could not create the archive ref").strip()
        raise RuntimeError(f"could not create persistent archive ref {ref}: {detail}")
    _validate_archive_ref(ref, head_oid, root=root)


def _manifest_paths(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    branch: str,
    pr_number: int,
    merge_oid: str,
    head_ref_oid: str,
    root: Path,
) -> dict[str, Path]:
    """Validate a recovery journal before using any path it names."""
    if manifest.get("schema_version") != 2:
        raise RuntimeError(f"unsupported recovery manifest schema: {manifest_path}")
    if manifest.get("branch") != branch or manifest.get("pr_number") != pr_number:
        raise RuntimeError(f"recovery manifest does not identify PR #{pr_number} and branch {branch}")
    if manifest.get("merge_commit") != merge_oid:
        raise RuntimeError(f"recovery manifest merge SHA does not match PR #{pr_number}")
    if manifest.get("head_ref_oid") != head_ref_oid or manifest.get("head_oid") != head_ref_oid:
        raise RuntimeError(f"recovery manifest head SHA does not match PR #{pr_number}")
    if manifest.get("submodules_checked") is not True:
        raise RuntimeError("recovery manifest does not prove initialized submodules were inspected")
    if not WORKTREE_BRANCH_RE.fullmatch(branch):
        raise RuntimeError(f"recovery manifest has an invalid task branch: {branch!r}")

    fields = (
        "archive_path",
        "archived_checkout_path",
        "archived_gitdir_path",
        "original_checkout_path",
        "original_gitdir_path",
        "common_gitdir_path",
        "recovery_manifest_path",
        "original_checkout_git_pointer",
        "original_gitdir_pointer",
        "original_commondir_pointer",
        "lock_reason",
        "head_oid",
        "archive_ref",
    )
    if any(not isinstance(manifest.get(field), str) or not manifest[field] for field in fields):
        raise RuntimeError(f"recovery manifest is missing required paths or pointer data: {manifest_path}")
    if not isinstance(manifest.get("worktree_config_enabled"), bool):
        raise RuntimeError("recovery manifest is missing the worktreeConfig state")
    if "shared_index_relative_path" not in manifest:
        raise RuntimeError("recovery manifest is missing the split-index state")
    shared_index_relative = manifest.get("shared_index_relative_path")
    if shared_index_relative is not None:
        if not isinstance(shared_index_relative, str):
            raise RuntimeError("recovery manifest has an invalid split-index path")
        shared_index_path = Path(shared_index_relative)
        if (
            shared_index_path.is_absolute()
            or ".." in shared_index_path.parts
            or len(shared_index_path.parts) != 1
            or not shared_index_path.name.startswith("sharedindex.")
        ):
            raise RuntimeError("recovery manifest split-index path is not a direct sharedindex file")

    common_raw = Path(manifest["common_gitdir_path"])
    _ensure_no_redirect_components(common_raw, label="common Git directory")
    archive_raw = Path(manifest["archive_path"])
    checkout_archive_raw = Path(manifest["archived_checkout_path"])
    gitdir_archive_raw = Path(manifest["archived_gitdir_path"])
    checkout_original_raw = Path(manifest["original_checkout_path"])
    gitdir_original_raw = Path(manifest["original_gitdir_path"])
    _ensure_no_redirect_components(archive_raw, label="recovery archive")
    _ensure_no_redirect_components(checkout_archive_raw, label="archived checkout")
    _ensure_no_redirect_components(gitdir_archive_raw, label="archived Git admin")
    _ensure_no_redirect_components(checkout_original_raw, label="original checkout")
    _ensure_no_redirect_components(gitdir_original_raw, label="original Git admin")
    _ensure_no_redirect_components(Path(manifest["recovery_manifest_path"]), label="recovery manifest")
    try:
        common = common_raw.resolve(strict=True)
        archive = archive_raw.resolve(strict=True)
        checkout_archive = checkout_archive_raw.resolve()
        gitdir_archive = gitdir_archive_raw.resolve()
        checkout_original = checkout_original_raw.resolve()
        gitdir_original = gitdir_original_raw.resolve()
        saved_manifest = Path(manifest["recovery_manifest_path"]).resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"recovery manifest contains an unresolved path: {exc}") from exc

    actual_common = Path(
        _git_output(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, root=root)
    )
    _ensure_no_redirect_components(actual_common, label="common Git directory")
    actual_common = actual_common.resolve(strict=True)
    if not _same_path(common, actual_common):
        raise RuntimeError(f"recovery manifest common Git directory does not match this repository: {common}")
    expected_parent = common / "ai-router-worktree-archives"
    _ensure_no_redirect_components(archive_raw, label="recovery archive")
    _ensure_no_redirect_components(Path(manifest["recovery_manifest_path"]), label="recovery manifest")
    _ensure_no_redirect_components(checkout_original, label="original checkout")
    _ensure_no_redirect_components(gitdir_original, label="Git admin")
    if not _same_path(archive.parent, expected_parent) or not archive.is_dir():
        raise RuntimeError(f"recovery archive is outside its managed common-dir archive directory: {archive}")
    if not _same_path(saved_manifest, manifest_path) or saved_manifest.parent != archive:
        raise RuntimeError(f"recovery manifest path does not match its archive: {manifest_path}")
    if not _same_path(checkout_archive, archive / "checkout") or not _same_path(gitdir_archive, archive / "git-admin"):
        raise RuntimeError(f"recovery manifest archive paths are ambiguous: {archive}")
    managed_raw = worktrees_dir(root)
    _ensure_no_redirect_components(managed_raw, label="managed worktrees directory")
    managed = managed_raw.resolve()
    admin_root = common / "worktrees"
    if not _same_path(checkout_original.parent, managed):
        raise RuntimeError(f"recovery manifest checkout is outside the managed worktrees directory: {checkout_original}")
    if not _same_path(gitdir_original.parent, admin_root):
        raise RuntimeError(f"recovery manifest admin directory is not a direct Git worktree registration: {gitdir_original}")
    if not COMMIT_RE.fullmatch(manifest["head_oid"]):
        raise RuntimeError("recovery manifest has an invalid original checkout HEAD")
    if manifest["archive_ref"] != _archive_ref_name(pr_number, head_ref_oid):
        raise RuntimeError("recovery manifest archive ref does not match this PR head SHA")
    if not isinstance(manifest.get("archive_ref_created"), bool):
        raise RuntimeError("recovery manifest is missing the persistent archive-ref state")

    original_checkout_pointer = manifest["original_checkout_git_pointer"].strip()
    if not original_checkout_pointer.startswith("gitdir:"):
        raise RuntimeError("recovery manifest checkout pointer is malformed")
    original_gitdir_target = Path(original_checkout_pointer[len("gitdir:"):].strip())
    if not original_gitdir_target.is_absolute():
        original_gitdir_target = checkout_original / original_gitdir_target
    original_gitdir_pointer = Path(manifest["original_gitdir_pointer"])
    if not original_gitdir_pointer.is_absolute():
        original_gitdir_pointer = gitdir_original / original_gitdir_pointer
    original_commondir_pointer = Path(manifest["original_commondir_pointer"])
    if not original_commondir_pointer.is_absolute():
        original_commondir_pointer = gitdir_original / original_commondir_pointer
    if not _same_path(original_gitdir_target, gitdir_original):
        raise RuntimeError("recovery manifest checkout pointer does not identify its original admin directory")
    if not _same_path(original_gitdir_pointer, checkout_original / ".git"):
        raise RuntimeError("recovery manifest admin pointer does not identify its original checkout")
    if not _same_path(original_commondir_pointer, common):
        raise RuntimeError("recovery manifest commondir pointer does not identify the repository common dir")

    return {
        "archive": archive,
        "checkout_archive": checkout_archive,
        "gitdir_archive": gitdir_archive,
        "checkout_original": checkout_original,
        "gitdir_original": gitdir_original,
        "common": common,
        "manifest": saved_manifest,
    }


def _load_archive_manifest(
    branch: str,
    pr_number: int,
    merge_oid: str,
    head_ref_oid: str,
    *,
    root: Path,
) -> tuple[Path, dict[str, Any]] | None:
    common_raw = Path(_git_output(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, root=root))
    _ensure_no_redirect_components(common_raw, label="common Git directory")
    archive_parent = common_raw.resolve(strict=True) / "ai-router-worktree-archives"
    if not archive_parent.exists():
        return None
    _ensure_no_redirect_components(archive_parent, label="archive root")
    if not archive_parent.is_dir():
        raise RuntimeError(f"refusing redirected or invalid archive parent: {archive_parent}")
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(archive_parent.glob(f"pr-{pr_number}-*/recovery.json")):
        _ensure_no_redirect_components(path, label="recovery manifest")
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"archive recovery manifest is not a regular file: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"could not read candidate recovery manifest {path}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("pr_number") != pr_number:
            raise RuntimeError(f"candidate archive manifest is malformed or mismatched: {path}")
        _manifest_paths(
            path,
            payload,
            branch=branch,
            pr_number=pr_number,
            merge_oid=merge_oid,
            head_ref_oid=head_ref_oid,
            root=root,
        )
        matches.append((path, payload))
    if len(matches) > 1:
        raise RuntimeError(f"multiple recovery archives match PR #{pr_number}; preserving all: " + ", ".join(str(p[0]) for p in matches))
    return matches[0] if matches else None


def _inspect_archive_transaction(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    branch: str,
    pr_number: int,
    merge_oid: str,
    head_ref_oid: str,
    root: Path,
) -> dict[str, Any]:
    """Read-only validation used by cleanup preview before offering recovery."""
    paths = _manifest_paths(
        manifest_path,
        manifest,
        branch=branch,
        pr_number=pr_number,
        merge_oid=merge_oid,
        head_ref_oid=head_ref_oid,
        root=root,
    )
    checkout_original = paths["checkout_original"]
    checkout_archive = paths["checkout_archive"]
    gitdir_original = paths["gitdir_original"]
    gitdir_archive = paths["gitdir_archive"]
    checkout_original_exists = checkout_original.is_dir() and not checkout_original.is_symlink()
    checkout_archive_exists = checkout_archive.is_dir() and not checkout_archive.is_symlink()
    admin_original_exists = gitdir_original.is_dir() and not gitdir_original.is_symlink()
    admin_archive_exists = gitdir_archive.is_dir() and not gitdir_archive.is_symlink()
    if not (checkout_original_exists or checkout_archive_exists):
        raise RuntimeError("pending archive has no valid checkout directory")
    if admin_original_exists == admin_archive_exists:
        raise RuntimeError("pending archive has zero or multiple Git admin directories")

    checkout_current = checkout_archive if checkout_archive_exists else checkout_original
    admin_current = gitdir_archive if admin_archive_exists else gitdir_original
    _assert_worktree_metadata_state(admin_current, manifest, root=root)
    head_state = _archive_head_state(
        admin_current,
        branch=branch,
        head_oid=manifest["head_oid"],
        root=root,
    )
    ref_present = _validate_archive_ref(
        manifest["archive_ref"],
        manifest["head_oid"],
        root=root,
        allow_missing=(
            head_state == "symbolic"
            and not manifest["archive_ref_created"]
            and manifest.get("state") in {"prepared", "recovery_required"}
        ),
    )
    if not ref_present and (
        manifest["archive_ref_created"]
        or head_state != "symbolic"
        or manifest.get("state") not in {"prepared", "recovery_required"}
    ):
        raise RuntimeError("archive transaction advanced without its persistent commit ref")
    if manifest.get("state") == "complete" and head_state != "detached":
        raise RuntimeError("completed archive HEAD is not detached at its recorded commit")
    _ensure_same_volume(
        [
            paths["common"],
            paths["archive"],
            checkout_original.parent,
            gitdir_original.parent,
            checkout_current,
            admin_current,
        ]
    )
    original_git_pointer = manifest["original_checkout_git_pointer"].strip()
    original_admin_pointer = manifest["original_gitdir_pointer"].strip()
    original_common_pointer = manifest["original_commondir_pointer"].strip()
    target_git_pointer = f"gitdir: {gitdir_archive.as_posix()}"
    target_admin_pointer = (checkout_archive / ".git").as_posix()
    target_common_pointer = os.path.relpath(paths["common"], gitdir_archive).replace(os.sep, "/")
    for pointer, accepted, label in (
        (checkout_current / ".git", (original_git_pointer, target_git_pointer), "checkout gitdir"),
        (admin_current / "gitdir", (original_admin_pointer, target_admin_pointer), "admin gitdir"),
        (admin_current / "commondir", (original_common_pointer, target_common_pointer), "admin commondir"),
    ):
        if pointer.is_symlink() or not pointer.is_file() or pointer.read_text(encoding="utf-8").strip() not in accepted:
            raise RuntimeError(f"pending archive {label} pointer is ambiguous: {pointer}")

    lock_file = admin_current / "locked"
    _ensure_no_redirect_components(lock_file, label="worktree lock")
    if admin_archive_exists:
        if not lock_file.is_file() or lock_file.read_text(encoding="utf-8").strip() != manifest["lock_reason"]:
            raise RuntimeError(f"pending archive lock is missing or changed: {lock_file}")
    elif os.path.lexists(lock_file) and (
        not lock_file.is_file() or lock_file.read_text(encoding="utf-8").strip() != manifest["lock_reason"]
    ):
        raise RuntimeError(f"pending archive lock belongs to another operation: {lock_file}")

    if checkout_original_exists and not checkout_archive_exists and admin_original_exists:
        if head_state == "symbolic":
            original_admin = _verified_worktree_admin(checkout_original, branch, root=root)
            if not _same_path(original_admin["gitdir"], gitdir_original) or original_admin["head_oid"] != manifest["head_oid"]:
                raise RuntimeError("pending checkout or admin identity changed; preserving both paths")
        else:
            resolved_gitdir = Path(_git_output(["rev-parse", "--absolute-git-dir"], cwd=checkout_original, root=root))
            top_level = Path(_git_output(["rev-parse", "--show-toplevel"], cwd=checkout_original, root=root))
            checkout_head = _git_output(["rev-parse", "HEAD"], cwd=checkout_original, root=root)
            if (
                not _same_path(resolved_gitdir, gitdir_original)
                or not _same_path(top_level, checkout_original)
                or checkout_head != manifest["head_oid"]
            ):
                raise RuntimeError("pending detached checkout identity changed; preserving both paths")
        _ensure_no_initialized_submodules(checkout_original, root=root)
        local_data = _status_entries(checkout_original, root=root)
        if local_data:
            raise RuntimeError("pending checkout acquired local data; preserving it: " + _render_local_data(local_data))

    registrations = registered_worktrees(root)
    if registrations is None:
        raise RuntimeError("could not inspect registrations while previewing pending archive")
    branch_entries = [item for item in registrations if item.get("branch") == f"refs/heads/{branch}"]
    original_path_entries = [item for item in registrations if _same_path(Path(item["path"]), checkout_original)]
    if admin_original_exists:
        if len(original_path_entries) != 1:
            raise RuntimeError("pending archive no longer matches one exact registered worktree")
        if head_state == "symbolic" and (
            len(branch_entries) != 1 or not _same_path(Path(branch_entries[0]["path"]), checkout_original)
        ):
            raise RuntimeError("pending symbolic HEAD no longer matches its exact branch registration")
    elif original_path_entries:
        raise RuntimeError("original checkout path is registered again; preserving archive and registration")
    elif head_state == "symbolic" and branch_entries:
        raise RuntimeError("pending archive branch has been registered elsewhere; preserving archive")

    if manifest.get("state") == "complete":
        top_level = Path(_git_output(["rev-parse", "--show-toplevel"], cwd=checkout_archive, root=root))
        if not _same_path(top_level, checkout_archive):
            raise RuntimeError(f"archived checkout resolves to an unexpected top-level: {top_level}")
        active_shared_index = _shared_index_relative_path(checkout_archive, gitdir_archive, root=root)
        if active_shared_index != manifest.get("shared_index_relative_path"):
            raise RuntimeError("completed archive split-index state does not match its recovery manifest")

    if head_state == "symbolic":
        branch_oid = run_git(["show-ref", "--verify", "--hash", f"refs/heads/{branch}"], root=root, check=False)
        if branch_oid.returncode != 0 or branch_oid.stdout.strip() != manifest["head_oid"]:
            raise RuntimeError("pending archive local branch ref changed; preserving archive")
    return {
        **{key: str(value) for key, value in paths.items()},
        "state": str(manifest.get("state", "unknown")),
        "archive_ref": str(manifest["archive_ref"]),
        "checkout_archived": checkout_archive_exists,
        "admin_metadata_archived": admin_archive_exists,
        "original_path_recreated": checkout_original_exists and checkout_archive_exists,
    }


def _set_archive_pointer(path: Path, *, original: str, target: str, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"cannot verify {label} pointer in archive: {path}")
    current = path.read_text(encoding="utf-8").strip()
    if current == target.strip():
        return
    if current != original.strip():
        raise RuntimeError(f"{label} pointer changed outside the archive transaction: {path}")
    _write_pointer(path, target)


def _archive_head_state(gitdir: Path, *, branch: str, head_oid: str, root: Path) -> str:
    head_file = gitdir / "HEAD"
    _ensure_no_redirect_components(head_file, label="archive HEAD")
    if head_file.is_symlink() or not head_file.is_file():
        raise RuntimeError(f"archive HEAD is missing or redirected: {head_file}")
    value = head_file.read_text(encoding="utf-8").strip()
    symbolic = f"ref: refs/heads/{branch}"
    if value == symbolic:
        branch_oid = run_git(["show-ref", "--verify", "--hash", f"refs/heads/{branch}"], root=root, check=False)
        if branch_oid.returncode != 0 or branch_oid.stdout.strip() != head_oid:
            raise RuntimeError("symbolic archive HEAD no longer matches the recorded checkout commit")
        return "symbolic"
    if value == head_oid:
        return "detached"
    raise RuntimeError(f"archive HEAD is neither the recorded branch nor commit: {head_file}")


def _set_archive_head(gitdir: Path, *, branch: str, head_oid: str, root: Path) -> None:
    state = _archive_head_state(gitdir, branch=branch, head_oid=head_oid, root=root)
    if state == "symbolic":
        _write_pointer(gitdir / "HEAD", head_oid)


def _registered_checkout(path: Path, *, root: Path) -> dict[str, str]:
    registrations = registered_worktrees(root)
    if registrations is None:
        raise RuntimeError("could not inspect Git worktree registrations")
    matches = [item for item in registrations if _same_path(Path(item["path"]), path)]
    if len(matches) != 1:
        raise RuntimeError(f"checkout path does not have one exact Git registration: {path}")
    return matches[0]


def _resume_archive_transaction(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    branch: str,
    pr_number: int,
    merge_oid: str,
    head_ref_oid: str,
    root: Path,
) -> dict[str, Any]:
    """Idempotently roll a journal forward without replacing an occupied path."""
    paths = _manifest_paths(
        manifest_path,
        manifest,
        branch=branch,
        pr_number=pr_number,
        merge_oid=merge_oid,
        head_ref_oid=head_ref_oid,
        root=root,
    )
    checkout_original = paths["checkout_original"]
    checkout_archive = paths["checkout_archive"]
    gitdir_original = paths["gitdir_original"]
    gitdir_archive = paths["gitdir_archive"]
    common = paths["common"]
    archive = paths["archive"]
    branch_ref = f"refs/heads/{branch}"
    lock_reason = manifest["lock_reason"]
    original_git_pointer = manifest["original_checkout_git_pointer"].strip()
    original_admin_pointer = manifest["original_gitdir_pointer"].strip()
    original_common_pointer = manifest["original_commondir_pointer"].strip()
    target_git_pointer = f"gitdir: {gitdir_archive.as_posix()}"
    target_admin_pointer = (checkout_archive / ".git").as_posix()
    try:
        target_common_pointer = os.path.relpath(common, gitdir_archive).replace(os.sep, "/")
    except ValueError as exc:
        raise RuntimeError("archive Git metadata cannot reach the common Git directory") from exc

    checkout_at_original = checkout_original.is_dir() and not checkout_original.is_symlink()
    checkout_at_archive = checkout_archive.is_dir() and not checkout_archive.is_symlink()
    if checkout_at_original and checkout_at_archive:
        # The original path was recreated after the archive move. Keep it untouched;
        # the manifest and admin pointers still identify the archived checkout.
        pass
    elif checkout_at_original == checkout_at_archive:
        raise RuntimeError("recovery has zero or two valid checkout locations; preserving both paths")

    admin_at_original = gitdir_original.is_dir() and not gitdir_original.is_symlink()
    admin_at_archive = gitdir_archive.is_dir() and not gitdir_archive.is_symlink()
    if admin_at_original == admin_at_archive:
        raise RuntimeError("recovery has zero or two valid Git admin locations; preserving both paths")

    checkout_current = checkout_archive if checkout_at_archive else checkout_original
    admin_current = gitdir_archive if admin_at_archive else gitdir_original
    _assert_worktree_metadata_state(admin_current, manifest, root=root)
    head_state = _archive_head_state(
        admin_current,
        branch=branch,
        head_oid=manifest["head_oid"],
        root=root,
    )
    ref_present = _validate_archive_ref(
        manifest["archive_ref"],
        manifest["head_oid"],
        root=root,
        allow_missing=(
            head_state == "symbolic"
            and not manifest["archive_ref_created"]
            and manifest.get("state") in {"prepared", "recovery_required"}
        ),
    )
    if not ref_present and (
        manifest["archive_ref_created"]
        or head_state != "symbolic"
        or manifest.get("state") not in {"prepared", "recovery_required"}
    ):
        raise RuntimeError("archive transaction advanced without its persistent commit ref")
    if manifest.get("state") == "complete" and head_state != "detached":
        raise RuntimeError("completed archive HEAD is not detached at its recorded commit")
    if not _same_pointer_text(checkout_current / ".git", original_git_pointer) and not _same_pointer_text(
        checkout_current / ".git", target_git_pointer
    ):
        raise RuntimeError(f"checkout .git pointer is neither the recorded original nor archive target: {checkout_current}")
    if not _same_pointer_text(admin_current / "gitdir", original_admin_pointer) and not _same_pointer_text(
        admin_current / "gitdir", target_admin_pointer
    ):
        raise RuntimeError(f"admin gitdir pointer is neither the recorded original nor archive target: {admin_current}")
    if not _same_pointer_text(admin_current / "commondir", original_common_pointer) and not _same_pointer_text(
        admin_current / "commondir", target_common_pointer
    ):
        raise RuntimeError(f"admin commondir pointer is neither the recorded original nor archive target: {admin_current}")

    _ensure_same_volume([common, archive, checkout_current.parent, admin_current.parent])
    if admin_at_original:
        checkout_gitdir = _git_output(["rev-parse", "--absolute-git-dir"], cwd=checkout_current, root=root)
        if not _same_path(Path(checkout_gitdir), admin_current):
            raise RuntimeError("checkout currently resolves to a different Git admin directory; preserving archive")
        if _git_output(["rev-parse", "HEAD"], cwd=checkout_current, root=root) != manifest["head_oid"]:
            raise RuntimeError("checkout HEAD changed during archive recovery; preserving archive")
        symbolic_head = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=checkout_current, root=root, check=False)
        if head_state == "symbolic" and (symbolic_head.returncode != 0 or symbolic_head.stdout.strip() != branch):
            raise RuntimeError(f"checkout does not resolve to the verified PR branch {branch}")
        if head_state == "detached" and symbolic_head.returncode == 0:
            raise RuntimeError("checkout HEAD unexpectedly became symbolic during archive recovery")
        _ensure_no_initialized_submodules(checkout_current, root=root)
    elif manifest.get("submodules_checked") is not True:
        raise RuntimeError("archive manifest does not prove submodules were inspected before admin relocation")

    registrations = registered_worktrees(root)
    if registrations is None:
        raise RuntimeError("could not inspect worktree registrations during archive recovery")
    branch_entries = [item for item in registrations if item.get("branch") == branch_ref]
    original_path_entries = [item for item in registrations if _same_path(Path(item["path"]), checkout_original)]
    archive_path_entries = [item for item in registrations if _same_path(Path(item["path"]), checkout_archive)]
    if manifest.get("state") == "complete":
        if original_path_entries or archive_path_entries:
            raise RuntimeError("completed archive checkout path has been registered again")
    elif admin_at_original:
        lock_file = gitdir_original / "locked"
        if lock_file.exists():
            if lock_file.is_symlink() or not lock_file.is_file() or lock_file.read_text(encoding="utf-8").strip() != lock_reason:
                raise RuntimeError(f"worktree lock is not owned by this recovery transaction: {lock_file}")
        else:
            lock = run_git(["worktree", "lock", "--reason", lock_reason, str(checkout_original)], root=root, check=False)
            if lock.returncode != 0 or not lock_file.is_file() or lock_file.read_text(encoding="utf-8").strip() != lock_reason:
                detail = (lock.stderr or lock.stdout or "Git did not create the expected worktree lock").strip()
                raise RuntimeError(f"could not lock exact worktree before archive: {detail}")

        original_path_entries = [item for item in registrations if _same_path(Path(item["path"]), checkout_original)]
        if len(original_path_entries) != 1:
            raise RuntimeError("registered checkout path changed; preserving archive")
        if head_state == "symbolic" and (
            len(branch_entries) != 1 or not _same_path(Path(branch_entries[0]["path"]), checkout_original)
        ):
            raise RuntimeError("registered branch-to-checkout association changed; preserving archive")
    else:
        lock_file = gitdir_archive / "locked"
        if lock_file.is_symlink() or not lock_file.is_file() or lock_file.read_text(encoding="utf-8").strip() != lock_reason:
            raise RuntimeError(f"archived worktree lock is missing or changed: {lock_file}")
        if original_path_entries or archive_path_entries:
            raise RuntimeError("archived checkout path has been registered again")
        if head_state == "symbolic" and branch_entries:
            raise RuntimeError("symbolic archive branch was registered elsewhere while pending")

    if head_state == "symbolic":
        # Pin the archive before moving the checkout, so reuse of the branch can
        # never retarget the retained snapshot. The custom common ref keeps the
        # commit reachable even after branch deletion and reflog expiry.
        _ensure_archive_ref(manifest["archive_ref"], manifest["head_oid"], root=root)
        manifest["archive_ref_created"] = True
        manifest["state"] = "archive_ref_created"
        _write_recovery_manifest(manifest_path, manifest)
        _set_archive_head(admin_current, branch=branch, head_oid=manifest["head_oid"], root=root)
        head_state = "detached"
        manifest["state"] = "head_detached"
        _write_recovery_manifest(manifest_path, manifest)
    else:
        _validate_archive_ref(manifest["archive_ref"], manifest["head_oid"], root=root)

    if checkout_at_original and not checkout_at_archive:
        if admin_at_original:
            _registered_checkout(checkout_original, root=root)
            if _status_entries(checkout_original, root=root):
                raise RuntimeError("worktree acquired local data while recovery was pending; preserving checkout")
        elif not _same_pointer_text(checkout_original / ".git", original_git_pointer):
            raise RuntimeError("original checkout pointer changed during pending archive; preserving it")
        _ensure_same_volume([checkout_original, archive])
        _move_directory(checkout_original, checkout_archive)
        checkout_at_archive = True
        checkout_current = checkout_archive
        manifest["state"] = "checkout_archived"
        _write_recovery_manifest(manifest_path, manifest)

    if admin_at_original:
        # A new directory at the old checkout path is never opened, overwritten, or removed.
        _ensure_same_volume([gitdir_original, archive])
        _move_directory(gitdir_original, gitdir_archive)
        admin_at_archive = True
        admin_current = gitdir_archive
        manifest["state"] = "admin_metadata_archived"
        _write_recovery_manifest(manifest_path, manifest)

    _set_archive_pointer(
        checkout_archive / ".git",
        original=original_git_pointer,
        target=target_git_pointer,
        label="checkout gitdir",
    )
    manifest["state"] = "checkout_pointer_rewritten"
    _write_recovery_manifest(manifest_path, manifest)
    _set_archive_pointer(
        gitdir_archive / "gitdir",
        original=original_admin_pointer,
        target=target_admin_pointer,
        label="admin gitdir",
    )
    manifest["state"] = "admin_pointer_rewritten"
    _write_recovery_manifest(manifest_path, manifest)
    _set_archive_pointer(
        gitdir_archive / "commondir",
        original=original_common_pointer,
        target=target_common_pointer,
        label="admin commondir",
    )
    manifest["state"] = "pointers_rewritten"
    _write_recovery_manifest(manifest_path, manifest)

    archived_gitdir = Path(_git_output(["rev-parse", "--absolute-git-dir"], cwd=checkout_archive, root=root)).resolve(strict=True)
    archived_common = Path(
        _git_output(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=checkout_archive, root=root)
    ).resolve(strict=True)
    if not _same_path(archived_gitdir, gitdir_archive) or not _same_path(archived_common, common):
        raise RuntimeError("archived checkout Git pointers did not resolve to their verified destinations")
    archived_top_level = Path(_git_output(["rev-parse", "--show-toplevel"], cwd=checkout_archive, root=root))
    if not _same_path(archived_top_level, checkout_archive):
        raise RuntimeError(f"archived checkout resolves to an unexpected top-level: {archived_top_level}")
    archived_shared_index = _shared_index_relative_path(checkout_archive, gitdir_archive, root=root)
    if archived_shared_index != manifest.get("shared_index_relative_path"):
        raise RuntimeError("archived split-index state changed while relocating Git metadata")
    if not _same_pointer_text(gitdir_archive / "HEAD", manifest["head_oid"]):
        raise RuntimeError("archived checkout HEAD was not detached at its exact PR head SHA")
    if _git_output(["rev-parse", "HEAD"], cwd=checkout_archive, root=root) != manifest["head_oid"]:
        raise RuntimeError("archived checkout HEAD changed during archive; preserving it")

    remaining = registered_worktrees(root)
    if remaining is None or any(
        _same_path(Path(item["path"]), checkout_original) or _same_path(Path(item["path"]), checkout_archive)
        for item in remaining
    ):
        raise RuntimeError(f"Git still registers an archive checkout path after exact admin metadata relocation")

    late_entries = _status_entries(checkout_archive, root=root)
    manifest["state"] = "complete"
    manifest["late_local_data"] = [{"status": code, "path": item} for code, item in late_entries]
    manifest["original_path_recreated"] = checkout_original.exists()
    _write_recovery_manifest(manifest_path, manifest)
    return {
        "archive_path": str(archive),
        "archived_checkout_path": str(checkout_archive),
        "archived_gitdir_path": str(gitdir_archive),
        "recovery_manifest_path": str(manifest_path),
        "archive_ref": str(manifest["archive_ref"]),
        "late_local_data": manifest["late_local_data"],
        "original_path_recreated": manifest["original_path_recreated"],
    }


def _create_archive_manifest(
    path: Path,
    *,
    branch: str,
    pr_number: int,
    pr_url: str,
    default_branch: str,
    merge_oid: str,
    head_ref_oid: str,
    root: Path,
) -> tuple[Path, dict[str, Any]]:
    admin = _archive_preflight(path, branch, head_ref_oid=head_ref_oid, root=root)
    checkout = admin["checkout"]
    archive_parent = admin["archive_parent"]
    archive_parent.mkdir(parents=True, exist_ok=True)
    _ensure_no_redirect_components(archive_parent, label="archive root")
    if not archive_parent.is_dir():
        raise RuntimeError(f"refusing redirected or invalid archive parent: {archive_parent}")
    resolved_parent = archive_parent.resolve(strict=True)
    if not _same_path(resolved_parent, admin["common"] / "ai-router-worktree-archives"):
        raise RuntimeError(f"archive parent does not resolve to the validated common Git directory: {resolved_parent}")
    admin_root = (admin["common"] / "worktrees").resolve()
    if resolved_parent == admin_root or resolved_parent.is_relative_to(admin_root):
        raise RuntimeError("archive destination must be outside Git's registered worktrees directory")
    _ensure_same_volume([checkout, admin["gitdir"], admin["common"], resolved_parent])

    archive_ref = _archive_ref_name(pr_number, admin["head_oid"])
    _validate_archive_ref(archive_ref, admin["head_oid"], root=root, allow_missing=True)
    archive = resolved_parent / f"pr-{pr_number}-{branch.split('/', 1)[1]}-{uuid.uuid4().hex[:12]}"
    archive.mkdir(exist_ok=False)
    _ensure_no_redirect_components(archive, label="recovery archive")
    _ensure_same_volume([checkout, admin["gitdir"], admin["common"], archive])
    archive_checkout = archive / "checkout"
    archive_gitdir = archive / "git-admin"
    manifest_path = archive / "recovery.json"
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "state": "prepared",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pr_number": pr_number,
        "pr_url": pr_url,
        "default_branch": default_branch,
        "merge_commit": merge_oid,
        "branch": branch,
        "head_oid": admin["head_oid"],
        "head_ref_oid": head_ref_oid,
        "archive_ref": archive_ref,
        "archive_ref_created": False,
        "original_checkout_path": str(checkout),
        "archive_path": str(archive),
        "archived_checkout_path": str(archive_checkout),
        "original_gitdir_path": str(admin["gitdir"]),
        "archived_gitdir_path": str(archive_gitdir),
        "common_gitdir_path": str(admin["common"]),
        "original_checkout_git_pointer": admin["checkout_git_pointer"],
        "original_gitdir_pointer": admin["gitdir_pointer"],
        "original_commondir_pointer": admin["commondir_pointer"],
        "submodules_checked": True,
        "worktree_config_enabled": admin["worktree_config_enabled"],
        "shared_index_relative_path": admin["shared_index_relative_path"],
        "lock_reason": f"harness archive for merged PR #{pr_number}",
        "recovery_manifest_path": str(manifest_path),
    }
    _write_recovery_manifest(manifest_path, manifest, create=True)
    return manifest_path, manifest


def _archive_worktree(
    path: Path,
    *,
    branch: str,
    pr_number: int,
    pr_url: str,
    default_branch: str,
    merge_oid: str,
    head_ref_oid: str,
    root: Path,
) -> dict[str, Any]:
    manifest_path, manifest = _create_archive_manifest(
        path,
        branch=branch,
        pr_number=pr_number,
        pr_url=pr_url,
        default_branch=default_branch,
        merge_oid=merge_oid,
        head_ref_oid=head_ref_oid,
        root=root,
    )
    try:
        return _resume_archive_transaction(
            manifest_path,
            manifest,
            branch=branch,
            pr_number=pr_number,
            merge_oid=merge_oid,
            head_ref_oid=head_ref_oid,
            root=root,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        manifest["state"] = "recovery_required"
        manifest["detail"] = str(exc)
        try:
            _write_recovery_manifest(manifest_path, manifest)
        except OSError:
            pass
        raise RuntimeError(
            f"archive transaction stopped with all moved data preserved; inspect {manifest['archive_path']} "
            f"and recovery manifest {manifest_path}: {exc}"
        ) from exc


def cmd_cleanup(
    branch: str | None,
    pr_number: int,
    *,
    dry_run: bool = True,
    as_json: bool = False,
    root: Path | None = None,
) -> int:
    repo_root = root or PRIMARY_ROOT
    try:
        if pr_number <= 0:
            raise RuntimeError("--pr must be a positive PR number")

        verification = _verify_merged_pr(branch, pr_number, root=repo_root)
        branch, default_branch, merge_oid, head_ref_oid, pr_url = verification
        verified_again = _verify_merged_pr(branch, pr_number, root=repo_root)
        if verified_again != verification:
            raise RuntimeError(f"PR #{pr_number} verification changed during cleanup")

        pending = _load_archive_manifest(branch, pr_number, merge_oid, head_ref_oid, root=repo_root)
        if pending is not None:
            manifest_path, manifest = pending
            snapshot = _inspect_archive_transaction(
                manifest_path,
                manifest,
                branch=branch,
                pr_number=pr_number,
                merge_oid=merge_oid,
                head_ref_oid=head_ref_oid,
                root=repo_root,
            )
            payload = {
                "ok": True,
                "dry_run": dry_run,
                "branch": branch,
                "pr": pr_url,
                "default_branch": default_branch,
                "merge_commit": merge_oid,
                "head_ref_oid": head_ref_oid,
                "branch_retained": True,
                "archive_path": snapshot["archive"],
                "archived_checkout_path": snapshot["checkout_archive"],
                "archived_gitdir_path": snapshot["gitdir_archive"],
                "recovery_manifest_path": snapshot["manifest"],
                "archive_ref": snapshot["archive_ref"],
                "archive_state": snapshot["state"],
                "original_path_recreated": snapshot["original_path_recreated"],
            }
            if dry_run:
                payload["action"] = (
                    "archive is already complete; no change needed"
                    if snapshot["state"] == "complete"
                    else "would resume the verified archive transaction; archived data remains on disk"
                )
                _print_payload(payload, as_json)
                return 0

            _move_cwd_outside_worktree(Path(snapshot["checkout_archive"]), repo_root)
            try:
                archived = _resume_archive_transaction(
                    manifest_path,
                    manifest,
                    branch=branch,
                    pr_number=pr_number,
                    merge_oid=merge_oid,
                    head_ref_oid=head_ref_oid,
                    root=repo_root,
                )
            except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                manifest["state"] = "recovery_required"
                manifest["detail"] = str(exc)
                try:
                    _write_recovery_manifest(manifest_path, manifest)
                except OSError:
                    pass
                raise RuntimeError(
                    f"archive recovery stopped with data preserved; inspect {snapshot['archive']} "
                    f"and recovery manifest {manifest_path}: {exc}"
                ) from exc
            payload.update(archived)
            payload["archive_state"] = "complete"
            payload["action"] = "resumed and completed exact worktree unregistration; archive retained on disk"
            _print_payload(payload, as_json)
            return 0

        path = _worktree_for_branch(branch, root=repo_root)
        before = _status_entries(path, root=repo_root)
        if before:
            print(f"error: {_render_local_data(before)}", file=sys.stderr)
            return 1

        verified_after_status = _verify_merged_pr(branch, pr_number, root=repo_root)
        if verified_after_status != verification:
            raise RuntimeError(f"PR #{pr_number} verification changed during cleanup; preserving {path}")
        if _worktree_for_branch(branch, root=repo_root) != path:
            raise RuntimeError(f"worktree association for {branch} changed during cleanup; preserving {path}")
        after = _status_entries(path, root=repo_root)
        if after:
            print(f"error: {_render_local_data(after)}", file=sys.stderr)
            return 1

        archive_plan = _archive_preflight(path, branch, head_ref_oid=head_ref_oid, root=repo_root)
        archive_ref = _archive_ref_name(pr_number, head_ref_oid)
        _validate_archive_ref(archive_ref, head_ref_oid, root=repo_root, allow_missing=True)

        payload = {
            "ok": True,
            "dry_run": dry_run,
            "branch": branch,
            "path": str(path),
            "pr": pr_url,
            "default_branch": default_branch,
            "merge_commit": merge_oid,
            "head_ref_oid": head_ref_oid,
            "archive_ref": archive_ref,
            "branch_retained": True,
        }
        if dry_run:
            payload["action"] = (
                "would pin the PR head SHA under refs/ai-router/worktree-archives/, then move this checkout and its exact "
                "Git admin metadata to a retained archive detached at the PR head SHA, "
                "then unregister only this worktree; the local branch is retained"
            )
            payload["archive_parent"] = str(archive_plan["archive_parent"])
            _print_payload(payload, as_json)
            return 0
        _move_cwd_outside_worktree(path, repo_root)
        if _worktree_for_branch(branch, root=repo_root) != path:
            raise RuntimeError(f"worktree association for {branch} changed immediately before archiving; preserving {path}")
        immediately_before = _status_entries(path, root=repo_root)
        if immediately_before:
            print(f"error: {_render_local_data(immediately_before)}", file=sys.stderr)
            return 1
        verified_immediately = _verify_merged_pr(branch, pr_number, root=repo_root)
        if verified_immediately != verification:
            raise RuntimeError(f"PR #{pr_number} verification changed immediately before archive; preserving {path}")

        archived = _archive_worktree(
            path,
            branch=branch,
            pr_number=pr_number,
            pr_url=pr_url,
            default_branch=default_branch,
            merge_oid=merge_oid,
            head_ref_oid=head_ref_oid,
            root=repo_root,
        )
        payload.update(archived)
        payload["archive_state"] = "complete"
        payload["action"] = (
            "pinned the PR head SHA under refs/ai-router/worktree-archives/, archived the checkout detached at that SHA, "
            "unregistered only this worktree, and retained the archive and reusable local branch"
        )
        _print_payload(payload, as_json)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create task worktrees and archive verified post-merge checkouts safely.")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a unique branch and worktree for one task")
    create.add_argument("--slug", required=True, help="Kebab-case task name")
    create.add_argument("--dry-run", action="store_true", help="Print the planned worktree without creating it")
    create.add_argument("--json", action="store_true", help="Emit JSON")

    listing = sub.add_parser("list", help="List Git worktrees")
    listing.add_argument("--json", action="store_true", help="Emit JSON")

    cleanup = sub.add_parser(
        "cleanup",
        help="Preview verified worktree archiving by default; --apply retains an archive and unregisters the worktree",
    )
    cleanup.add_argument("--branch", help="Task branch; omit to derive it from the merged PR")
    cleanup.add_argument("--pr", type=int, required=True, help="Merged PR number in this repository")
    cleanup.add_argument("--dry-run", action="store_true", help="Verify conditions without moving or unregistering")
    cleanup.add_argument(
        "--apply",
        action="store_true",
        help="Pin the exact PR head commit, archive it and unregister; retain the archive, ref, and reusable local branch",
    )
    cleanup.add_argument("--json", action="store_true", help="Emit JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "create":
        return cmd_create(args.slug, dry_run=args.dry_run, as_json=args.json)
    if args.command == "list":
        return cmd_list(as_json=args.json)
    if args.command == "cleanup":
        if args.pr <= 0:
            print("error: --pr must be a positive PR number", file=sys.stderr)
            return 2
        if args.apply and args.dry_run:
            print("error: --apply and --dry-run cannot be used together", file=sys.stderr)
            return 2
        return cmd_cleanup(args.branch, args.pr, dry_run=not args.apply, as_json=args.json)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
