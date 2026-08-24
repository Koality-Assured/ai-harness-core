"""Worktree isolation, claim tracking, concurrency checking, and cleanup lifecycle.

Ensures concurrent agents do not collide on shared checkouts or overlapping areas.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from ..config import HarnessConfig, load_harness_config
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import HarnessConfig, load_harness_config

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorktreeError(RuntimeError):
    """Base error for worktree isolation operations."""


class WorktreeConcurrencyError(WorktreeError):
    """Raised when an area overlap is detected with an active claim."""


class WorktreeExistsError(WorktreeError):
    """Raised when a worktree or claim already exists."""


class WorktreeNotFoundError(WorktreeError):
    """Raised when a specified worktree or claim cannot be found."""


@dataclass
class WorktreeClaim:
    """Represents an active area claim and branch reservation."""

    slug: str
    branch: str
    path: str
    areas: list[str]
    agent: str
    created: str = field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert claim to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorktreeClaim:
        """Create a WorktreeClaim from a dictionary."""
        return cls(
            slug=str(data.get("slug", "")),
            branch=str(data.get("branch", "")),
            path=str(data.get("path", "")),
            areas=list(data.get("areas", [])),
            agent=str(data.get("agent", "router")),
            created=str(data.get("created", "")),
            metadata=dict(data.get("metadata", {})),
        )


class WorktreeManager:
    """Lifecycle manager for isolated git worktrees and area claims."""

    def __init__(
        self,
        config: HarnessConfig | None = None,
        repo_root: Path | str | None = None,
        worktrees_dir: Path | str | None = None,
    ) -> None:
        self.config = config or load_harness_config(repo_root=repo_root)
        self.repo_root = Path(repo_root).resolve() if repo_root else self.config.repo_root

        if worktrees_dir:
            self.worktrees_dir = Path(worktrees_dir).resolve()
        else:
            self.worktrees_dir = self.config.paths.resolve("worktrees", self.repo_root)

        self.git_cmd = self.config.adapters.git.command
        self.timeout_sec = self.config.adapters.git.timeout_sec
        self.branch_prefix = self.config.adapters.git.branch_prefix

    def claim_path(self, slug: str) -> Path:
        """Return the claim JSON path for a slug."""
        return self.worktrees_dir / f"{slug}.claim.json"

    def worktree_path(self, slug: str) -> Path:
        """Return the worktree checkout directory for a slug."""
        return self.worktrees_dir / slug

    def run_git(self, args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Execute a git command within the repo root or specified cwd."""
        target_cwd = cwd or self.repo_root
        try:
            return subprocess.run(
                [self.git_cmd, *args],
                cwd=target_cwd,
                check=check,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_sec,
            )
        except subprocess.CalledProcessError as exc:
            msg = (exc.stderr or exc.stdout or f"git exit code {exc.returncode}").strip()
            raise WorktreeError(f"Git command failed: {msg}") from exc
        except subprocess.TimeoutExpired as exc:
            raise WorktreeError(f"Git command timed out after {self.timeout_sec}s: {' '.join(args)}") from exc
        except OSError as exc:
            raise WorktreeError(f"Failed to execute git '{self.git_cmd}': {exc}") from exc

    def load_claims(self) -> list[WorktreeClaim]:
        """Load all valid claim files in the worktrees directory."""
        if not self.worktrees_dir.exists():
            return []
        claims: list[WorktreeClaim] = []
        for path in sorted(self.worktrees_dir.glob("*.claim.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                claims.append(WorktreeClaim.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue
        return claims

    def get_claim(self, slug: str) -> WorktreeClaim | None:
        """Fetch claim details for a specific slug if present."""
        path = self.claim_path(slug)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return WorktreeClaim.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return None

    def check_concurrency(
        self,
        areas: list[str],
        ignore_slug: str | None = None,
    ) -> list[WorktreeClaim]:
        """Return any active claims that overlap with the requested areas."""
        want = set(areas)
        overlapping: list[WorktreeClaim] = []
        for claim in self.load_claims():
            if ignore_slug and claim.slug == ignore_slug:
                continue
            claimed_areas = set(claim.areas)
            if want & claimed_areas:
                overlapping.append(claim)
        return overlapping

    def create_worktree(
        self,
        slug: str,
        areas: list[str],
        agent: str = "router",
        force: bool = False,
        dry_run: bool = False,
        base_branch: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorktreeClaim:
        """Create a new isolated git worktree, branch, and claim record."""
        if not SLUG_PATTERN.match(slug):
            raise WorktreeError(f"Invalid slug '{slug}'. Must be kebab-case matching [a-z0-9-]+.")
        if not areas:
            raise WorktreeError("Cannot claim an empty area list. Specify at least one top-level area.")

        dest = self.worktree_path(slug)
        claim_file = self.claim_path(slug)
        branch = f"{self.branch_prefix}/{dt.date.today().isoformat()}-{slug}"

        # Check concurrency overlap
        overlaps = self.check_concurrency(areas, ignore_slug=slug)
        if overlaps and not force:
            overlapping_slugs = ", ".join(f"{c.slug} ({', '.join(c.areas)})" for c in overlaps)
            raise WorktreeConcurrencyError(
                f"Cannot create worktree '{slug}': requested areas {areas} overlap with active claims: {overlapping_slugs}. Use force=True if human-authorized."
            )

        if dest.exists() and not force:
            raise WorktreeExistsError(f"Worktree path already exists: {dest}")
        if claim_file.exists() and not force:
            raise WorktreeExistsError(f"Claim file already exists: {claim_file}")

        claim = WorktreeClaim(
            slug=slug,
            branch=branch,
            path=str(dest),
            areas=areas,
            agent=agent,
            metadata=metadata or {},
        )

        if dry_run:
            return claim

        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        git_args = ["worktree", "add", "-b", branch, str(dest)]
        if base_branch:
            git_args.append(base_branch)

        self.run_git(git_args)
        claim_file.write_text(json.dumps(claim.to_dict(), indent=2) + "\n", encoding="utf-8")

        return claim

    def remove_worktree(
        self,
        slug: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> bool:
        """Remove a worktree and its claim file."""
        dest = self.worktree_path(slug)
        claim_file = self.claim_path(slug)

        if not dest.exists() and not claim_file.exists():
            raise WorktreeNotFoundError(f"Worktree or claim for '{slug}' does not exist.")

        if dry_run:
            return True

        if dest.exists():
            git_args = ["worktree", "remove", str(dest)]
            if force:
                git_args.append("--force")
            try:
                self.run_git(git_args)
            except WorktreeError:
                if dest.exists() and not force:
                    raise

        if claim_file.exists():
            claim_file.unlink()

        return True

    def list_worktrees(self) -> list[dict[str, Any]]:
        """List all git worktrees joined with their claim metadata."""
        claims_by_slug = {c.slug: c for c in self.load_claims()}
        results: list[dict[str, Any]] = []

        try:
            res = self.run_git(["worktree", "list", "--porcelain"])
            entries: list[dict[str, str]] = []
            curr: dict[str, str] = {}
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    if curr:
                        entries.append(curr)
                        curr = {}
                    continue
                if line.startswith("worktree "):
                    curr["worktree"] = line[len("worktree ") :].strip()
                elif line.startswith("branch "):
                    curr["branch"] = line[len("branch ") :].strip()
                elif line.startswith("HEAD "):
                    curr["head"] = line[len("HEAD ") :].strip()
            if curr:
                entries.append(curr)

            for entry in entries:
                wt_path = Path(entry.get("worktree", ""))
                slug = wt_path.name
                claim = claims_by_slug.get(slug)
                results.append({
                    "worktree": str(wt_path),
                    "branch": entry.get("branch", ""),
                    "head": entry.get("head", ""),
                    "slug": slug,
                    "claim": claim.to_dict() if claim else None,
                })
        except WorktreeError:
            # If git worktree list fails, return just claim info
            for claim in claims_by_slug.values():
                results.append({
                    "worktree": claim.path,
                    "branch": claim.branch,
                    "head": "",
                    "slug": claim.slug,
                    "claim": claim.to_dict(),
                })

        return results

    def cleanup_stale(
        self,
        dry_run: bool = False,
        max_age_seconds: float | None = None,
    ) -> list[str]:
        """Clean up dangling claim files whose worktree path is gone, or claims exceeding max age."""
        cleaned: list[str] = []
        now = dt.datetime.now(dt.timezone.utc)

        for claim in self.load_claims():
            target_path = Path(claim.path)
            is_stale = not target_path.exists()

            if max_age_seconds is not None and not is_stale:
                try:
                    created_dt = dt.datetime.fromisoformat(claim.created.replace("Z", "+00:00"))
                    if (now - created_dt).total_seconds() > max_age_seconds:
                        is_stale = True
                except (ValueError, TypeError):
                    pass

            if is_stale:
                cleaned.append(claim.slug)
                if not dry_run:
                    self.remove_worktree(claim.slug, force=True)

        return cleaned
