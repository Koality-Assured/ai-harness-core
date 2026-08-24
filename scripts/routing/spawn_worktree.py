"""Spawn, list, and remove isolated git worktrees for concurrent agent work.

tags: [routing, isolation]
routing_hints: [worktree, branch, concurrency, claims]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import AreasYamlError, load_area_ids  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402
WORKTREES = ROOT / "scratch" / "worktrees"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def allowed_areas() -> set[str]:
    try:
        return load_area_ids(ROOT)
    except AreasYamlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def claim_path(slug: str) -> Path:
    return WORKTREES / f"{slug}.claim.json"


def worktree_path(slug: str) -> Path:
    return WORKTREES / slug


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


def overlapping(areas: list[str], claims: list[dict], *, ignore_slug: str | None = None) -> list[dict]:
    want = set(areas)
    hits = []
    for claim in claims:
        if ignore_slug and claim.get("slug") == ignore_slug:
            continue
        other = set(claim.get("areas") or [])
        if want & other:
            hits.append(claim)
    return hits


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
    hits = overlapping(areas, load_claims())
    payload = {"ok": not hits, "overlap": hits, "areas": areas}
    if as_json:
        print(json.dumps(payload, indent=2))
    elif hits:
        print("overlap with active claims:", file=sys.stderr)
        for claim in hits:
            print(f"  {claim.get('slug')} areas={claim.get('areas')}", file=sys.stderr)
    else:
        print("ok: no overlapping claims")
    return 1 if hits else 0


def cmd_add(slug: str, areas: list[str], agent: str, force: bool, dry_run: bool, as_json: bool) -> int:
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
    branch = f"agent/{dt.date.today().isoformat()}-{slug}"
    hits = overlapping(areas, load_claims(), ignore_slug=slug)
    if hits and not force:
        print("error: overlapping areas with active claims (pass --force to override):", file=sys.stderr)
        for claim in hits:
            print(f"  {claim.get('slug')} areas={claim.get('areas')}", file=sys.stderr)
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
        "created": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if dry_run:
        if as_json:
            print(json.dumps({"dry_run": True, "claim": claim}, indent=2))
        else:
            print(f"dry-run: git worktree add -b {branch} {dest}")
            print(json.dumps(claim, indent=2))
        return 0

    WORKTREES.mkdir(parents=True, exist_ok=True)
    try:
        run_git(["worktree", "add", "-b", branch, str(dest)])
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout, file=sys.stderr)
        return 1
    claim_path(slug).write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
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
        print(f"dry-run: git worktree remove {dest}")
        print(f"dry-run: delete {claim_path(slug)}")
        return 0
    args = ["worktree", "remove", str(dest)]
    if force:
        args.append("--force")
    try:
        run_git(args)
    except subprocess.CalledProcessError as exc:
        # Still drop the claim if the worktree is already gone.
        if dest.exists():
            print(exc.stderr or exc.stdout, file=sys.stderr)
            return 1
        print("warning: git worktree remove failed; removing claim anyway", file=sys.stderr)
    claim = claim_path(slug)
    if claim.exists():
        claim.unlink()
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
        return cmd_add(args.slug, parse_areas(args.areas), args.agent, args.force, args.dry_run, args.json)
    if args.cmd == "remove":
        return cmd_remove(args.slug, args.dry_run, args.force)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())