"""Spawn, list, and remove isolated git worktrees for concurrent agent work.

tags: [routing, isolation]
routing_hints: [worktree, branch, concurrency, claims]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import AreasYamlError, load_area_ids  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402


def resolve_primary_root() -> Path:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            common_git = Path(proc.stdout.strip())
            if not common_git.is_absolute():
                common_git = (ROOT / common_git).resolve()
            return common_git.parent.resolve()
    except Exception:
        pass
    return ROOT


PRIMARY_ROOT = resolve_primary_root()
WORKTREES = PRIMARY_ROOT / "scratch" / "worktrees"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def allowed_areas() -> set[str]:
    try:
        return load_area_ids(PRIMARY_ROOT)
    except AreasYamlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=PRIMARY_ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def claim_path(slug: str) -> Path:
    return WORKTREES / f"{slug}.claim.json"


def worktree_path(slug: str) -> Path:
    return WORKTREES / slug


def path_exists(path: Path) -> bool | None:
    """Return path presence, or None when filesystem state is uncertain."""
    try:
        path.stat()
        return True
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return None


def write_claim_atomically(path: Path, claim: dict) -> None:
    """Publish a complete claim file atomically before creating its worktree."""
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


from contextlib import contextmanager
import os
import time


@contextmanager
def claim_lock(timeout_sec: float = 10.0, poll_interval: float = 0.05):
    """Atomic cross-platform lockfile protecting worktree claim operations."""
    WORKTREES.mkdir(parents=True, exist_ok=True)
    lock_file = WORKTREES / ".claims.lock"
    start_time = time.time()
    fd = None
    while True:
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            if time.time() - start_time >= timeout_sec:
                # Do not break an old lock based on age alone: the owner may
                # still be removing a slow worktree. Leave recovery explicit.
                raise TimeoutError(f"Timed out after {timeout_sec}s waiting for claim lock: {lock_file}")
            time.sleep(poll_interval)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass


def load_claims() -> list[dict]:
    if not WORKTREES.exists():
        return []
    claims = []
    for path in sorted(WORKTREES.glob("*.claim.json")):
        try:
            claims.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            claims.append({"slug": path.stem, "error": "invalid json", "path": str(path)})
    return claims


def find_harness_binary() -> str | None:
    """Locate the compiled harness CLI binary across Windows and POSIX platforms."""
    bin_name = "harness.exe" if os.name == "nt" else "harness"
    cmd = shutil.which("harness") or shutil.which(bin_name)
    if cmd:
        return cmd
    candidates: list[Path] = [
        # POSIX standard paths
        Path.home() / ".local" / "bin" / bin_name,
        Path("/opt/homebrew/bin") / bin_name,
        Path("/usr/local/bin") / bin_name,
    ]
    if os.name == "nt":
        candidates.extend([
            Path.home() / "scoop" / "shims" / bin_name,
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "harness" / bin_name,
            Path("C:/Code/harness-cli") / bin_name,
        ])
    candidates.append(PRIMARY_ROOT.parent / "harness-cli" / bin_name)

    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def query_active_claims() -> list[dict]:
    """Return unexpired claims and expired claims whose checkout cannot be ruled out."""
    claims = load_claims()
    if not claims:
        return []
    now_utc = dt.datetime.now(dt.timezone.utc)
    registrations: list[dict[str, str]] | None = None
    registrations_checked = False
    active = []
    for c in claims:
        exp_str = c.get("expires_at")
        if exp_str:
            try:
                exp_dt = dt.datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                if now_utc > exp_dt:
                    # Expiry makes an orphan claim stale; it never releases a
                    # claim while its checkout remains on disk or in Git.
                    if not registrations_checked:
                        registrations = registered_worktrees()
                        registrations_checked = True
                    if not claim_worktree_exists(c, registrations):
                        continue
            except Exception:
                pass
        active.append(c)
    return active


def registered_worktrees() -> list[dict[str, str]] | None:
    """Return Git worktree path/branch pairs, or None if state cannot be verified."""
    try:
        proc = run_git(["worktree", "list", "--porcelain"], check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    if not isinstance(proc.stdout, str):
        return None

    entries: list[dict[str, str]] = []
    entry: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            if entry:
                entries.append(entry)
                entry = {}
        elif line.startswith("worktree "):
            entry["path"] = line[len("worktree "):]
        elif line.startswith("branch "):
            entry["branch"] = line[len("branch "):]
    if entry:
        entries.append(entry)
    if not entries or any(not item.get("path") for item in entries):
        return None
    return entries


def claim_worktree_exists(claim: dict, registrations: list[dict[str, str]] | None) -> bool:
    """Check whether a claim's worktree exists by path or Git registration.

    Unknown registration state fails closed for an expired claim.
    """
    raw_path = claim.get("path") or worktree_path(str(claim.get("slug", "")))
    try:
        path = Path(raw_path)
    except (TypeError, ValueError):
        return True
    if path_exists(path) is not False:
        return True

    if registrations is None:
        return True

    try:
        wanted_path = os.path.normcase(str(path.resolve(strict=False)))
    except (OSError, RuntimeError, TypeError, ValueError):
        return True
    wanted_branch = claim.get("branch")
    if wanted_branch and not isinstance(wanted_branch, str):
        return True
    if wanted_branch and not wanted_branch.startswith("refs/heads/"):
        wanted_branch = f"refs/heads/{wanted_branch}"
    for entry in registrations:
        entry_path = entry.get("path")
        if entry_path:
            try:
                registered_path = os.path.normcase(str(Path(entry_path).resolve(strict=False)))
            except (OSError, RuntimeError, TypeError, ValueError):
                return True
            if registered_path == wanted_path:
                return True
        if wanted_branch and entry.get("branch") == wanted_branch:
            return True
    return False


def overlapping(areas: list[str], claims: list[dict], *, ignore_slug: str | None = None) -> list[dict]:
    want = set(areas)
    hits = []
    for claim in claims:
        if ignore_slug and claim.get("slug") == ignore_slug:
            continue
        raw_areas = claim.get("areas")
        if (
            not isinstance(raw_areas, list)
            or not raw_areas
            or any(not isinstance(area, str) or not area.strip() for area in raw_areas)
        ):
            hits.append(claim)
            continue
        other = set(raw_areas)
        if want & other:
            hits.append(claim)
    return hits


def claim_overlap_detail(claim: dict) -> str:
    """Format a collision and give repair guidance for malformed area metadata."""
    slug = claim.get("slug", "unknown")
    areas = claim.get("areas")
    if (
        not isinstance(areas, list)
        or not areas
        or any(not isinstance(area, str) or not area.strip() for area in areas)
    ):
        location = claim.get("path") or str(claim_path(str(slug)))
        return (
            f"{slug}: claim has missing or invalid areas; inspect {location} and repair it "
            "after verifying its worktree path and Git registration"
        )
    return f"{slug} areas={areas}"


def cmd_list(as_json: bool) -> int:
    claims = load_claims()
    try:
        listed = run_git(["worktree", "list", "--porcelain"]).stdout
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps({"claims": claims, "git_worktree_list": listed}, indent=2))
        return 0
    print(listed.rstrip())
    if not claims:
        print("(no claim files)")
        return 0
    print("\nclaims:")
    for claim in claims:
        areas = ",".join(claim.get("areas") or [])
        print(f"  {claim.get('slug')}: branch={claim.get('branch')} areas={areas} agent={claim.get('agent')}")
    return 0


def cmd_check(areas: list[str], as_json: bool) -> int:
    hits = overlapping(areas, query_active_claims())
    payload = {"ok": not hits, "overlap": hits, "areas": areas}
    if as_json:
        print(json.dumps(payload, indent=2))
    elif hits:
        print("overlap with active claims:", file=sys.stderr)
        for claim in hits:
            print(f"  {claim_overlap_detail(claim)}", file=sys.stderr)
    else:
        print("ok: no overlapping claims")
    return 1 if hits else 0


def cmd_add(
    slug: str,
    areas: list[str],
    agent: str,
    force: bool,
    dry_run: bool,
    as_json: bool,
    branch: str | None = None,
    ttl_hours: float = 24.0,
) -> int:
    if not SLUG_RE.match(slug):
        print("error: slug must be kebab-case [a-z0-9-]", file=sys.stderr)
        return 2
    unknown = [a for a in areas if a not in allowed_areas()]
    if unknown:
        print(f"error: unknown areas: {unknown} (from routing/areas.yaml)", file=sys.stderr)
        return 2
    if not areas:
        print("error: provide --areas (comma-separated top-level folders)", file=sys.stderr)
        return 2

    dest = worktree_path(slug)
    if not branch:
        branch = f"agent/{dt.date.today().isoformat()}-{slug}"

    now_utc = dt.datetime.now(dt.timezone.utc)
    created_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_utc = now_utc + dt.timedelta(hours=ttl_hours)
    expires_str = expires_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    if dry_run:
        hits = overlapping(areas, query_active_claims(), ignore_slug=slug)
        if hits and not force:
            print("error: overlapping areas with active claims (pass --force to override):", file=sys.stderr)
            for claim in hits:
                print(f"  {claim_overlap_detail(claim)}", file=sys.stderr)
            return 3
        claim = {
            "slug": slug,
            "branch": branch,
            "path": str(dest),
            "areas": areas,
            "agent": agent,
            "created": created_str,
            "created_at": created_str,
            "ttl_hours": ttl_hours,
            "expires_at": expires_str,
        }
        if as_json:
            print(json.dumps({"dry_run": True, "claim": claim}, indent=2))
        else:
            print(f"dry-run: git worktree add -b {branch} {dest}")
            print(json.dumps(claim, indent=2))
        return 0

    try:
        with claim_lock():
            hits = overlapping(areas, query_active_claims(), ignore_slug=slug)
            if hits and not force:
                print("error: overlapping areas with active claims (pass --force to override):", file=sys.stderr)
                for claim in hits:
                    print(f"  {claim_overlap_detail(claim)}", file=sys.stderr)
                return 3
            if dest.exists():
                print(f"error: worktree path already exists: {dest}", file=sys.stderr)
                return 2
            if claim_path(slug).exists() and not force:
                print(f"error: claim already exists: {claim_path(slug)}", file=sys.stderr)
                return 2

            claim = {
                "slug": slug,
                "branch": branch,
                "path": str(dest),
                "areas": areas,
                "agent": agent,
                "created": created_str,
                "created_at": created_str,
                "ttl_hours": ttl_hours,
                "expires_at": expires_str,
            }
            WORKTREES.mkdir(parents=True, exist_ok=True)
            claim_file = claim_path(slug)
            write_claim_atomically(claim_file, claim)
            try:
                run_git(["worktree", "add", "-b", branch, str(dest)])
            except subprocess.CalledProcessError as exc:
                print(exc.stderr or exc.stdout, file=sys.stderr)
                registrations = registered_worktrees()
                if registrations is None or claim_worktree_exists(claim, registrations):
                    print("error: cannot verify failed worktree add cleanup; preserving claim", file=sys.stderr)
                    return 1
                try:
                    claim_file.unlink(missing_ok=True)
                except OSError as unlink_error:
                    print(f"error: failed to remove unused claim: {unlink_error}", file=sys.stderr)
                return 1
    except TimeoutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except OSError as exc:
        print(f"error: unable to complete worktree add safely: {exc}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps(claim, indent=2))
    else:
        print(f"worktree: {dest}")
        print(f"branch:   {branch}")
        print(f"claim:    {claim_path(slug)}")
    return 0


def cmd_remove(slug: str, dry_run: bool, force: bool) -> int:
    dest = worktree_path(slug)
    if dry_run:
        command = ["git", "worktree", "remove", str(dest)]
        if force:
            command.append("--force")
        print(f"dry-run: {' '.join(command)}")
        print(f"dry-run: delete {claim_path(slug)}")
        return 0
    try:
        with claim_lock():
            claim = claim_path(slug)
            claim_data: dict = {}
            if claim.exists():
                try:
                    loaded = json.loads(claim.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    print(f"error: cannot read claim metadata; preserving claim: {exc}", file=sys.stderr)
                    return 1
                if (
                    not isinstance(loaded, dict)
                    or loaded.get("slug") != slug
                    or not isinstance(loaded.get("path"), str)
                    or not loaded["path"]
                    or not isinstance(loaded.get("branch"), str)
                    or not loaded["branch"]
                ):
                    print("error: invalid claim metadata; preserving claim", file=sys.stderr)
                    return 1
                claim_data = loaded

            identity = {
                "slug": slug,
                "path": claim_data.get("path") or str(dest),
                "branch": claim_data.get("branch"),
            }
            registrations = registered_worktrees()
            if registrations is None:
                print("error: cannot verify Git worktree registration; preserving claim", file=sys.stderr)
                return 1

            dest_state = path_exists(dest)
            if dest_state is None:
                print("error: cannot verify worktree path; preserving claim", file=sys.stderr)
                return 1
            if dest_state is False and not claim_worktree_exists(identity, registrations):
                if claim.exists():
                    claim.unlink()
                print(f"removed {slug}")
                return 0

            args = ["worktree", "remove", str(dest)]
            if force:
                args.append("--force")
            try:
                run_git(args)
            except subprocess.CalledProcessError as exc:
                print(exc.stderr or exc.stdout, file=sys.stderr)
                print("error: worktree removal failed; preserving claim", file=sys.stderr)
                return 1

            registrations = registered_worktrees()
            if registrations is None:
                print("error: cannot verify Git worktree registration; preserving claim", file=sys.stderr)
                return 1

            dest_state = path_exists(dest)
            if dest_state is not False or claim_worktree_exists(identity, registrations):
                print("error: Git reported removal success but worktree remains; preserving claim", file=sys.stderr)
                return 1

            if claim.exists():
                claim.unlink()
    except TimeoutError as exc:
        print(f"error: failed to acquire claim lock; preserving claim: {exc}", file=sys.stderr)
        return 4
    except OSError as exc:
        print(f"error: failed to remove claim: {exc}", file=sys.stderr)
        return 1
    print(f"removed {slug}")
    return 0


def parse_areas(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true", help="Machine-readable output")
    shared.add_argument("--dry-run", action="store_true")
    shared.add_argument("--force", action="store_true", help="Override overlap / existing claim")
    parser = argparse.ArgumentParser(description=__doc__, parents=[shared])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Create branch + worktree + claim", parents=[shared])
    p_add.add_argument("--slug", required=True)
    p_add.add_argument("--areas", required=True, help="Comma-separated top-level areas")
    p_add.add_argument("--agent", default="router", help="Intended owner agent id")
    p_add.add_argument("--branch", default=None, help="Custom branch name (defaults to agent/YYYY-MM-DD-<slug>)")
    p_add.add_argument("--ttl-hours", type=float, default=24.0, help="Lease time-to-live in hours (default: 24.0)")

    sub.add_parser("list", help="Show git worktrees and claim files", parents=[shared])

    p_check = sub.add_parser("check", help="Exit 1 if areas overlap an active claim", parents=[shared])
    p_check.add_argument("--areas", required=True)

    p_rm = sub.add_parser("remove", help="Remove worktree and claim", parents=[shared])
    p_rm.add_argument("--slug", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "list":
        return cmd_list(args.json)
    if args.cmd == "check":
        return cmd_check(parse_areas(args.areas), args.json)
    if args.cmd == "add":
        return cmd_add(
            args.slug,
            parse_areas(args.areas),
            args.agent,
            args.force,
            args.dry_run,
            args.json,
            branch=args.branch,
            ttl_hours=args.ttl_hours,
        )
    if args.cmd == "remove":
        return cmd_remove(args.slug, args.dry_run, args.force)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
