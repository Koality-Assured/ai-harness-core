"""In-repo Python CLI control plane for ai-router.

tags: [harness, cli, routing, isolation, auth, keyring]
routing_hints: [harness, cli, status, branch, agent, pr, clean, auth, login, logout]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Ensure _lib and scripts are in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from areas import AreasYamlError, load_area_ids, load_area_records  # noqa: E402
from md import agent_paths, load_agent_record  # noqa: E402
from paths import REPO_ROOT  # noqa: E402

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\([a-zA-Z0-9_\-\./]+\))?(!)?:\s*.+"
)


def get_primary_repo_root(cwd: Path | None = None) -> Path:
    """Return the primary git repository root where .git and scratch/worktrees live."""
    target_cwd = cwd or Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            common_git = Path(proc.stdout.strip())
            if not common_git.is_absolute():
                common_git = (target_cwd / common_git).resolve()
            return common_git.parent.resolve()
    except Exception:
        pass
    try:
        proc2 = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc2.returncode == 0 and proc2.stdout.strip():
            return Path(proc2.stdout.strip()).resolve()
    except Exception:
        pass
    return target_cwd.resolve()


def get_checkout_root(cwd: Path | None = None) -> Path:
    """Return the current working tree top-level checkout directory."""
    target_cwd = cwd or Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=target_cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except Exception:
        pass
    return target_cwd.resolve()


def get_worktrees_dir(primary_root: Path | None = None) -> Path:
    root = primary_root or get_primary_repo_root()
    return root / "scratch" / "worktrees"


def load_claims(primary_root: Path | None = None) -> list[dict[str, Any]]:
    wt_dir = get_worktrees_dir(primary_root)
    if not wt_dir.exists():
        return []
    claims = []
    for path in sorted(wt_dir.glob("*.claim.json")):
        try:
            claim_data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(claim_data, dict):
                claims.append(claim_data)
        except Exception:
            claims.append({"slug": path.stem, "error": "invalid json", "path": str(path)})
    return claims


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or get_checkout_root(),
        check=check,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def format_branch_name(slug: str, branch_type: str = "agent") -> str:
    """Generate Conventional branch name."""
    if branch_type == "feat":
        return f"feat/{slug}"
    today = dt.date.today().isoformat()
    return f"agent/{today}-{slug}"


def is_conventional_commit(msg: str) -> bool:
    """Validate whether a commit subject conforms to Conventional Commits."""
    return bool(CONVENTIONAL_COMMIT_PATTERN.match(msg.strip()))


# --- Command Handlers ---


def cmd_status(args: argparse.Namespace) -> int:
    target_harness = getattr(args, "harness", None)
    if target_harness:
        from cli.schema_adapter import resolve_harness_root
        try:
            target_root = resolve_harness_root(target_harness)
            primary_root = get_primary_repo_root(target_root)
            checkout_root = get_checkout_root(target_root)
        except Exception as exc:
            print(f"error: failed to resolve target harness '{target_harness}': {exc}", file=sys.stderr)
            return 1
    else:
        primary_root = get_primary_repo_root()
        checkout_root = get_checkout_root()

    # Current branch
    try:
        branch_proc = run_git(["branch", "--show-current"], cwd=checkout_root, check=False)
        current_branch = branch_proc.stdout.strip()
        if not current_branch:
            head_proc = run_git(["rev-parse", "--short", "HEAD"], cwd=checkout_root, check=False)
            current_branch = f"detached-at-{head_proc.stdout.strip()}"
    except Exception:
        current_branch = "unknown"

    # Dirtiness
    try:
        status_proc = run_git(["status", "--porcelain"], cwd=checkout_root, check=False)
        dirty_lines = [ln.rstrip() for ln in status_proc.stdout.splitlines() if ln.strip()]
        is_clean = len(dirty_lines) == 0
    except Exception:
        dirty_lines = []
        is_clean = False

    # Active claims
    claims = load_claims(primary_root)
    enriched_claims = []
    for c in claims:
        claim_slug = c.get("slug", "")
        claim_path_str = c.get("path", "")
        claim_path = Path(claim_path_str) if claim_path_str else (get_worktrees_dir(primary_root) / claim_slug)
        exists_on_disk = claim_path.exists()
        item = dict(c)
        item["exists_on_disk"] = exists_on_disk
        enriched_claims.append(item)

    active_harness = None
    try:
        from cli.registry import get_registry
        active_harness = get_registry().get_active_harness()
    except Exception:
        pass

    if args.json:
        payload = {
            "primary_root": str(primary_root),
            "checkout_root": str(checkout_root),
            "branch": current_branch,
            "is_clean": is_clean,
            "uncommitted_files": dirty_lines,
            "active_claims": enriched_claims,
        }
        if active_harness:
            payload["active_harness"] = active_harness
        print(json.dumps(payload, indent=2))
        return 0

    repo_title = primary_root.name if primary_root else "Harness"
    print(f"=== {repo_title} Harness Status ===")
    if active_harness:
        print(f"Active Harness: {active_harness['id']} ({active_harness['path']})")
    print(f"Primary Root:   {primary_root}")
    print(f"Checkout Root:  {checkout_root}")
    print(f"Current Branch: {current_branch}")
    print(f"Working Tree:   {'CLEAN' if is_clean else f'DIRTY ({len(dirty_lines)} uncommitted file(s))'}")
    if not is_clean:
        for f in dirty_lines[:10]:
            print(f"  {f}")
        if len(dirty_lines) > 10:
            print(f"  ... and {len(dirty_lines) - 10} more")

    print("\nActive Worktree Claims:")
    if not enriched_claims:
        print("  (no active claims)")
    else:
        for c in enriched_claims:
            slug = c.get("slug", "unknown")
            branch = c.get("branch", "unknown")
            areas = ",".join(c.get("areas") or [])
            agent = c.get("agent", "unknown")
            status_tag = "OK" if c.get("exists_on_disk") else "STALE (missing folder)"
            print(f"  [{status_tag}] {slug}")
            print(f"         branch: {branch}")
            print(f"         areas:  {areas}")
            print(f"         agent:  {agent}")
            print(f"         path:   {c.get('path')}")

    return 0


def cmd_branch(args: argparse.Namespace) -> int:
    slug = args.slug.strip()
    if not SLUG_PATTERN.match(slug):
        print(f"error: slug must be kebab-case [a-z0-9-], got '{slug}'", file=sys.stderr)
        return 2

    target_harness = getattr(args, "harness", None)
    if target_harness:
        from cli.schema_adapter import resolve_harness_root
        try:
            target_root = resolve_harness_root(target_harness)
            primary_root = get_primary_repo_root(target_root)
        except Exception as exc:
            print(f"error: failed to resolve target harness '{target_harness}': {exc}", file=sys.stderr)
            return 1
    else:
        primary_root = get_primary_repo_root()

    # 1. Verify primary root tree is clean before branching
    status_proc = run_git(["status", "--porcelain"], cwd=primary_root, check=False)
    allow_dirty = getattr(args, "allow_dirty", False) or args.force
    if status_proc.returncode == 0 and status_proc.stdout.strip():
        if allow_dirty:
            print("warning: primary repository has uncommitted changes (proceeding via --allow-dirty).", file=sys.stderr)
        else:
            print(
                "error: primary repository has uncommitted changes. Stash or commit before branching (or pass --allow-dirty / --force).",
                file=sys.stderr,
            )
            return 1

    # 2. Determine target areas
    areas_list: list[str] = []
    if args.areas:
        areas_list = [a.strip() for a in args.areas.split(",") if a.strip()]
    elif args.agent:
        # Infer default areas for agent
        try:
            records = load_area_records(primary_root)
            areas_list = [r["id"] for r in records if r.get("default_agent") == args.agent]
        except Exception:
            areas_list = []

    if not areas_list:
        print("error: provide --areas (comma-separated top-level folders)", file=sys.stderr)
        return 2

    # Validate areas
    try:
        valid_areas = load_area_ids(primary_root)
        unknown = [a for a in areas_list if a not in valid_areas]
        if unknown:
            print(f"error: unknown areas: {unknown} (from routing/areas.yaml)", file=sys.stderr)
            return 2
    except AreasYamlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # 3. Check for claim collisions
    from routing.spawn_worktree import cmd_add, overlapping  # noqa: E402

    active_claims = load_claims(primary_root)
    hits = overlapping(areas_list, active_claims, ignore_slug=slug)
    if hits and not args.force:
        print("error: overlapping areas with active claims (pass --force to override):", file=sys.stderr)
        for claim in hits:
            print(f"  {claim.get('slug')} areas={claim.get('areas')} agent={claim.get('agent')}", file=sys.stderr)
        return 3

    # 4. Generate branch name
    branch_type = getattr(args, "type", "agent") or "agent"
    branch_name = args.branch if getattr(args, "branch", None) else format_branch_name(slug, branch_type)

    # 5. Invoke spawn_worktree add
    ret = cmd_add(
        slug=slug,
        areas=areas_list,
        agent=args.agent or "harness-operator",
        force=args.force,
        dry_run=args.dry_run,
        as_json=args.json,
        branch=branch_name,
    )
    return ret


def cmd_agent(args: argparse.Namespace) -> int:
    target_harness = getattr(args, "harness", None)
    if target_harness:
        from cli.schema_adapter import resolve_harness_root
        try:
            target_root = resolve_harness_root(target_harness)
            primary_root = get_primary_repo_root(target_root)
        except Exception as exc:
            print(f"error: failed to resolve target harness '{target_harness}': {exc}", file=sys.stderr)
            return 1
    else:
        primary_root = get_primary_repo_root()

    agent_id = args.agent_id

    # Pre-fetch area defaults mapping
    area_map: dict[str, list[str]] = {}
    try:
        for r in load_area_records(primary_root):
            owner = r.get("default_agent")
            if owner:
                area_map.setdefault(owner, []).append(r["id"])
    except Exception:
        pass

    if not agent_id:
        # List all agents
        agent_file_paths = agent_paths(primary_root)
        agents = []
        for p in agent_file_paths:
            rec = load_agent_record(p)
            aid = rec.get("agent_id", p.parent.name)
            rec["ownership_areas"] = area_map.get(aid, [])
            if "path" in rec and isinstance(rec["path"], Path):
                rec["path"] = rec["path"].as_posix()
            agents.append(rec)

        if args.json:
            print(json.dumps(agents, indent=2, default=str))
            return 0

        print(f"=== Available Agents ({len(agents)}) ===\n")
        print(f"{'Agent ID':<26} {'Model Tier':<12} {'Ownership Areas':<22} {'Allowed Tools'}")
        print(f"{'-'*26} {'-'*12} {'-'*22} {'-'*30}")
        for a in agents:
            aid = a.get("agent_id", "")
            tier = a.get("model_tier", "standard")
            areas = ",".join(a.get("ownership_areas") or []) or "-"
            tools = ", ".join(a.get("allowed_tools", [])[:3])
            if len(a.get("allowed_tools", [])) > 3:
                tools += f" (+{len(a.get('allowed_tools')) - 3})"
            print(f"{aid:<26} {tier:<12} {areas:<22} {tools}")
        print("\nRun 'harness agent <agent_id>' for detailed inspection.")
        return 0

    # Specific agent inspection
    target_path = primary_root / "ai-tooling" / "agents" / agent_id / "AGENT.md"
    if not target_path.exists():
        print(f"error: agent '{agent_id}' not found at {target_path}", file=sys.stderr)
        return 2

    rec = load_agent_record(target_path)
    rec["ownership_areas"] = area_map.get(agent_id, [])
    if "path" in rec and isinstance(rec["path"], Path):
        rec["path"] = rec["path"].as_posix()

    if args.json:
        print(json.dumps(rec, indent=2, default=str))
        return 0

    print(f"=== Agent Specification: {rec.get('name', agent_id)} ({agent_id}) ===")
    print(f"Model Tier:        {rec.get('model_tier')}")
    print(f"Isolation Modes:   {', '.join(rec.get('isolation_modes', []))}")
    print(f"Ownership Areas:   {', '.join(rec.get('ownership_areas', [])) or '—'}")
    print(f"Description:       {rec.get('description')}")
    print(f"\nCapabilities ({len(rec.get('capabilities', []))}):")
    for cap in rec.get("capabilities", []):
        print(f"  - {cap}")
    print(f"\nAllowed Tools ({len(rec.get('allowed_tools', []))}):")
    for tool in rec.get("allowed_tools", []):
        print(f"  - {tool}")
    print(f"\nDelegation Targets ({len(rec.get('delegation_targets', []))}):")
    for dt_target in rec.get("delegation_targets", []):
        print(f"  - {dt_target}")

    # Prompt overview (first 600 chars of body)
    body = rec.get("body", "").strip()
    if body:
        print("\nPrompt Overview:")
        lines = [ln for ln in body.splitlines() if ln.strip()]
        preview = "\n".join(lines[:8])
        print(f"  {preview}")
        if len(lines) > 8:
            print("  ...")

    return 0


def cmd_pr(args: argparse.Namespace) -> int:
    # 0. Check gh binary existence
    if not shutil.which("gh"):
        print("error: GitHub CLI ('gh') is not installed or not found in PATH.", file=sys.stderr)
        return 1

    primary_root = get_primary_repo_root()
    checkout_root = get_checkout_root()
    base_branch = args.base or "main"

    # 1. Identify current branch
    branch_proc = run_git(["branch", "--show-current"], cwd=checkout_root, check=False)
    current_branch = branch_proc.stdout.strip()
    if not current_branch or current_branch.startswith("detached-at-"):
        print("error: cannot create PR from detached HEAD. Please checkout a named branch first.", file=sys.stderr)
        return 1
    if current_branch == base_branch:
        print(f"error: cannot create PR from base branch '{base_branch}'. Checkout a feature or agent branch.", file=sys.stderr)
        return 1

    print(f"Preparing PR for branch '{current_branch}' targeting '{base_branch}'...")

    # 2. Run preflight validations
    fast_validator = primary_root / "scripts" / "docs" / "validate_structure_fast.py"
    router_validator = primary_root / "scripts" / "docs" / "validate_router_structure.py"

    print("Running preflight validation: validate_structure_fast.py --all...")
    v1 = subprocess.run(
        [sys.executable, str(fast_validator), "--all", "--repo-root", str(checkout_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if v1.returncode != 0:
        print(f"error: validate_structure_fast.py failed:\n{v1.stderr or v1.stdout}", file=sys.stderr)
        return 1

    print("Running preflight validation: validate_router_structure.py...")
    v2 = subprocess.run(
        [sys.executable, str(router_validator)],
        cwd=checkout_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if v2.returncode != 0:
        print(f"error: validate_router_structure.py failed:\n{v2.stderr or v2.stdout}", file=sys.stderr)
        return 1

    print("Preflight validations PASSED.")

    # 3. Verify Conventional Commits
    log_proc = run_git(["log", f"{base_branch}..HEAD", "--format=%s"], cwd=checkout_root, check=False)
    commit_messages = [m.strip() for m in log_proc.stdout.splitlines() if m.strip()]
    if not commit_messages:
        print(f"error: no commits found on branch '{current_branch}' relative to '{base_branch}'. Please commit your changes before opening a PR.", file=sys.stderr)
        return 1

    non_conforming = [m for m in commit_messages if not is_conventional_commit(m)]
    if non_conforming:
        print("error: commits do not conform to Conventional Commits:", file=sys.stderr)
        for m in non_conforming:
            print(f"  - '{m}'", file=sys.stderr)
        print("Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.", file=sys.stderr)
        return 1

    print(f"Conventional Commits verified ({len(commit_messages)} commit(s)).")

    # 4. Generate PR Title & Body
    pr_title = args.title or (commit_messages[0] if commit_messages else f"feat: {current_branch}")
    if args.body:
        pr_body = args.body
    else:
        commits_bullets = "\n".join(f"- {m}" for m in commit_messages)
        pr_body = f"""## Summary
{commits_bullets}

## Verification Checklist
- [x] Fast structural validation (`validate_structure_fast.py --all`) passed
- [x] Router structure validation (`validate_router_structure.py`) passed
- [x] Conventional Commits verified across branch history
"""

    # 5. gh pr create
    cmd = ["gh", "pr", "create", "--base", base_branch, "--title", pr_title, "--body", pr_body]
    if args.draft:
        cmd.append("--draft")

    if args.dry_run:
        print("\n[dry-run] Would execute:")
        print(" ".join(cmd))
        print(f"\n[dry-run] PR Title: {pr_title}")
        print(f"[dry-run] PR Body:\n{pr_body}")
        return 0

    print("\nExecuting gh pr create...")
    gh_proc = subprocess.run(cmd, cwd=checkout_root, text=True, capture_output=True, encoding="utf-8")
    if gh_proc.returncode != 0:
        print(f"error: gh pr create failed:\n{gh_proc.stderr or gh_proc.stdout}", file=sys.stderr)
        return gh_proc.returncode

    print(gh_proc.stdout.strip())
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    primary_root = get_primary_repo_root()
    claims = load_claims(primary_root)

    # Determine merged branches
    try:
        merged_proc = run_git(["branch", "--merged", "main"], cwd=primary_root, check=False)
        merged_branches = {
            re.sub(r"^[*+\s]+", "", b).strip()
            for b in merged_proc.stdout.splitlines()
            if b.strip()
        }
    except Exception:
        merged_branches = set()

    # Classify claims
    targets: list[str] = []
    for c in claims:
        slug = c.get("slug", "")
        branch = c.get("branch", "")
        c_path = Path(c.get("path", "")) if c.get("path") else (get_worktrees_dir(primary_root) / slug)
        is_stale = not c_path.exists()
        is_merged = branch in merged_branches

        if args.slug and slug == args.slug:
            targets.append(slug)
        elif args.all:
            targets.append(slug)
        elif args.merged and is_merged:
            targets.append(slug)
        elif args.stale and is_stale:
            targets.append(slug)

    if not args.slug and not args.all and not args.merged and not args.stale:
        # Display candidates
        print("=== Worktree Cleanup Candidates ===")
        if not claims:
            print("  (no active worktrees or claims)")
            return 0
        for c in claims:
            slug = c.get("slug", "")
            branch = c.get("branch", "")
            c_path = Path(c.get("path", "")) if c.get("path") else (get_worktrees_dir(primary_root) / slug)
            is_stale = not c_path.exists()
            is_merged = branch in merged_branches
            status_tags = []
            if is_stale:
                status_tags.append("STALE")
            if is_merged:
                status_tags.append("MERGED")
            if not status_tags:
                status_tags.append("ACTIVE")
            print(f"  [{'/'.join(status_tags)}] {slug} ({branch})")
        print("\nSpecify --merged, --stale, --slug <slug>, or --all to clean.")
        return 0

    if not targets:
        print("No matching worktrees found to clean.")
        return 0

    from routing.spawn_worktree import cmd_remove  # noqa: E402

    print(f"Cleaning {len(targets)} worktree(s): {', '.join(targets)}")
    for slug in targets:
        cmd_remove(slug=slug, dry_run=args.dry_run, force=args.force)

    return 0


PROVIDER_ALIASES: dict[str, str] = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "cursor": "cursor",
    "gemini": "gemini",
    "google": "gemini",
    "openai": "openai",
    "gpt": "openai",
}
SUPPORTED_PROVIDERS: list[str] = ["anthropic", "cursor", "gemini", "openai"]


def cmd_auth(args: argparse.Namespace) -> int:
    if args.auth_cmd == "login":
        return cmd_auth_login(args)
    if args.auth_cmd == "status":
        return cmd_auth_status(args)
    if args.auth_cmd == "logout":
        return cmd_auth_logout(args)
    return 2


def cmd_auth_login(args: argparse.Namespace) -> int:
    from cli.auth import (
        AnthropicOAuthFlow,
        CursorAuthFlow,
        GeminiOAuthFlow,
        OpenAIAuthFlow,
    )

    raw_provider = getattr(args, "provider", "").lower().strip()
    provider = PROVIDER_ALIASES.get(raw_provider)
    if not provider:
        print(f"error: unsupported provider '{raw_provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}", file=sys.stderr)
        return 2

    no_browser = getattr(args, "no_browser", False)
    device_code = getattr(args, "device_code", False)
    api_key = getattr(args, "api_key", None)

    if api_key:
        print(
            "warning: providing secrets via the '--api-key' CLI argument can expose credentials "
            "to process table inspection (ps, Task Manager, /proc). "
            "Consider using interactive masked input instead.",
            file=sys.stderr,
        )

    try:
        if provider == "anthropic":
            AnthropicOAuthFlow.login(no_browser=no_browser, api_key=api_key)
        elif provider == "cursor":
            CursorAuthFlow.login(no_browser=no_browser, api_key=api_key)
        elif provider == "gemini":
            GeminiOAuthFlow.login(no_browser=no_browser, device_code=device_code, api_key=api_key)
        elif provider == "openai":
            OpenAIAuthFlow.login(api_key=api_key, no_browser=no_browser, device_code=device_code)
        return 0
    except (KeyboardInterrupt, SystemExit, EOFError):
        print("\nAuthentication aborted.", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: authentication failed for '{provider}': {exc}", file=sys.stderr)
        return 1


def cmd_auth_status(args: argparse.Namespace) -> int:
    from cli.auth import get_vault, is_token_expired, mask_token

    vault = get_vault()
    active_backend = vault.active_backend_name
    statuses: list[dict[str, Any]] = []

    for prov in SUPPORTED_PROVIDERS:
        cred = vault.get_credential(prov)
        if cred:
            expired = is_token_expired(cred)
            exp_val = cred.get("expires_at")
            if exp_val is None:
                exp_str = "Never (API Key)"
            elif isinstance(exp_val, (int, float)):
                exp_str = dt.datetime.fromtimestamp(exp_val, dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                exp_str = str(exp_val)

            status_str = "EXPIRED" if expired else "VALID"
            token_masked = mask_token(cred.get("access_token"))
            profile_str = cred.get("profile") or "-"
            statuses.append({
                "provider": prov,
                "authenticated": True,
                "status": status_str,
                "profile": profile_str,
                "expires": exp_str,
                "token_masked": token_masked,
                "token_type": cred.get("token_type", "Bearer"),
            })
        else:
            statuses.append({
                "provider": prov,
                "authenticated": False,
                "status": "NOT AUTHENTICATED",
                "profile": "-",
                "expires": "-",
                "token_masked": "-",
                "token_type": "-",
            })

    if args.json:
        payload = {
            "active_vault_backend": active_backend,
            "providers": statuses,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("=== Harness Credential Vault Status ===")
    print(f"Active Vault Backend: {active_backend}\n")
    print(f"{'Provider':<14} {'Status':<18} {'Profile':<16} {'Expires':<24} {'Token Masked'}")
    print(f"{'-'*14} {'-'*18} {'-'*16} {'-'*24} {'-'*20}")
    for s in statuses:
        print(f"{s['provider']:<14} {s['status']:<18} {s['profile']:<16} {s['expires']:<24} {s['token_masked']}")

    return 0


def cmd_auth_logout(args: argparse.Namespace) -> int:
    from cli.auth import get_vault

    vault = get_vault()

    if getattr(args, "all", False):
        providers = vault.list_providers()
        if not providers:
            print("No stored credentials found in vault.")
            return 0
        for p in providers:
            vault.delete_credential(p)
        print(f"Successfully purged all credentials from vault ({len(providers)} provider(s)).")
        return 0

    raw_provider = getattr(args, "provider", None)
    if not raw_provider:
        print("error: specify a provider to logout or pass --all to clear all credentials.", file=sys.stderr)
        return 2

    provider = PROVIDER_ALIASES.get(raw_provider.lower().strip())
    if not provider:
        print(f"error: unsupported provider '{raw_provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}", file=sys.stderr)
        return 2

    deleted = vault.delete_credential(provider)
    if deleted:
        print(f"Logged out from '{provider}'. Credential purged from vault.")
    else:
        print(f"No stored credentials found for '{provider}'.")

    return 0


# --- Registry and Multi-Harness Switcher Commands ---


def cmd_register(args: argparse.Namespace) -> int:
    from cli.registry import get_registry

    reg = get_registry()
    path_str = getattr(args, "path", None)
    if not path_str:
        print("error: specify a repository path to register.", file=sys.stderr)
        return 2

    target_path = Path(path_str).resolve()
    if not target_path.exists():
        print(f"error: path '{target_path}' does not exist.", file=sys.stderr)
        return 1
    if not target_path.is_dir():
        print(f"error: path '{target_path}' is not a directory.", file=sys.stderr)
        return 1

    name = getattr(args, "name", None)
    domain = getattr(args, "domain", None)
    make_active = getattr(args, "active", False)
    force = getattr(args, "force", False)

    try:
        record = reg.register(
            path=target_path,
            name=name,
            domain=domain,
            make_active=make_active,
            force=force,
        )
    except Exception as exc:
        print(f"error: failed to register harness: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps(record, indent=2))
        return 0

    print(f"Registered harness '{record['id']}' successfully.")
    print(f"  Name:   {record['name']}")
    print(f"  Domain: {record['domain']}")
    print(f"  Path:   {record['path']}")
    if make_active:
        print("  Status: Active harness")
    return 0


def cmd_deregister(args: argparse.Namespace) -> int:
    from cli.registry import get_registry

    reg = get_registry()
    target = getattr(args, "id_or_path", None)
    if not target:
        print("error: specify a harness ID or path to deregister.", file=sys.stderr)
        return 2

    deleted = reg.deregister(target)
    if not deleted:
        print(f"error: harness '{target}' not found in registry.", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"deregistered": target, "success": True}, indent=2))
        return 0

    print(f"Deregistered harness '{target}' successfully.")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from cli.registry import get_registry
    from cli.tui import format_harnesses_table

    reg = get_registry()
    harnesses = reg.list_harnesses()

    if getattr(args, "json", False):
        payload = {
            "count": len(harnesses),
            "harnesses": harnesses,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(format_harnesses_table(harnesses))
    return 0


def cmd_switch(args: argparse.Namespace) -> int:
    from cli.registry import get_registry

    reg = get_registry()
    target = getattr(args, "id_or_path", None)
    if not target:
        print("error: specify a harness ID or path to switch to.", file=sys.stderr)
        return 2

    try:
        record = reg.switch(target)
    except KeyError:
        print(
            f"error: harness '{target}' not found in registry. "
            "Use 'harness scan' or 'harness register <path>' first.",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError as fnf:
        print(f"error: {fnf}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: failed to switch harness: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"active_harness": record["id"], "record": record}, indent=2))
        return 0

    print(f"Switched active harness to '{record['id']}'.")
    print(f"  Path:   {record['path']}")
    print(f"  Domain: {record['domain']}")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from cli.registry import get_registry

    reg = get_registry()
    target_dir = getattr(args, "directory", None)
    auto_reg = not getattr(args, "no_register", False)

    discovered = reg.scan_siblings(parent_dir=target_dir, auto_register=auto_reg)

    if getattr(args, "json", False):
        print(json.dumps({"scanned_count": len(discovered), "discovered": discovered}, indent=2))
        return 0

    print(f"=== Sibling Harness Auto-Discovery ({len(discovered)} found) ===")
    if not discovered:
        print("  No sibling domain harnesses found matching router markers.")
        return 0

    for d in discovered:
        status_reg = "registered" if d.get("registered") else "found"
        print(f"  [{status_reg.upper()}] {d['name']:<24} ({d.get('branch', 'unknown')}) -> {d['path']}")
        print(f"         Domain: {d['domain']}")

    return 0


def cmd_tui(args: argparse.Namespace) -> int:
    from cli.registry import get_registry
    from cli.tui import run_switcher_tui

    reg = get_registry()
    return run_switcher_tui(reg)


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true", help="Format output as machine-readable JSON")
    shared.add_argument("--dry-run", action="store_true", help="Simulate operation without mutating state")
    shared.add_argument("--force", action="store_true", help="Override safety checks")
    shared.add_argument("--harness", help="Target specific registered domain harness by ID or path")

    parser = argparse.ArgumentParser(
        prog="harness",
        description="Unified Harness CLI Control Plane for domain harnesses and spokes.",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="cmd")

    # status
    sub.add_parser("status", help="Inspect git branch, cleanliness, and active worktree claims", parents=[shared])

    # branch
    p_branch = sub.add_parser("branch", help="Create isolated git worktree and area claim", parents=[shared])
    p_branch.add_argument("slug", help="Kebab-case slug for the worktree and branch")
    p_branch.add_argument("--areas", help="Comma-separated top-level directory claims")
    p_branch.add_argument("--agent", default="harness-operator", help="Owner agent ID")
    p_branch.add_argument("--type", choices=["agent", "feat"], default="agent", help="Branch prefix type")
    p_branch.add_argument("--branch", help="Explicit branch name override")
    p_branch.add_argument("--allow-dirty", action="store_true", help="Allow branching even if primary repository has uncommitted changes")

    # agent
    p_agent = sub.add_parser("agent", help="Inspect available agents or view detailed agent spec", parents=[shared])
    p_agent.add_argument("agent_id", nargs="?", default=None, help="Agent ID to inspect")

    # pr
    p_pr = sub.add_parser("pr", help="Run preflight validations, verify commits, and open PR", parents=[shared])
    p_pr.add_argument("--base", default="main", help="Target base branch (default: main)")
    p_pr.add_argument("--title", help="PR title (defaults to last commit message)")
    p_pr.add_argument("--body", help="PR description markdown")
    p_pr.add_argument("--draft", action="store_true", help="Create as a draft PR")

    # clean
    p_clean = sub.add_parser("clean", help="Prune merged worktrees and delete stale claims", parents=[shared])
    p_clean.add_argument("--slug", help="Specific worktree slug to clean")
    p_clean.add_argument("--merged", action="store_true", help="Clean all merged worktrees")
    p_clean.add_argument("--stale", action="store_true", help="Clean all stale claims")
    p_clean.add_argument("--all", action="store_true", help="Clean all worktrees and claims")

    # auth
    p_auth = sub.add_parser("auth", help="Manage authentication and secure credential vaults", parents=[shared])
    auth_sub = p_auth.add_subparsers(dest="auth_cmd", required=True)

    # auth login
    p_login = auth_sub.add_parser("login", help="Authenticate with an AI model provider", parents=[shared])
    p_login.add_argument("provider", choices=["anthropic", "claude", "cursor", "gemini", "google", "openai", "gpt"], help="Target model provider")
    p_login.add_argument("--no-browser", action="store_true", help="Use terminal/manual code entry instead of launching browser")
    p_login.add_argument("--device-code", action="store_true", help="Use RFC 8628 Device Authorization Grant")
    p_login.add_argument("--api-key", help="Direct API key onboarding into secure vault")

    # auth status
    auth_sub.add_parser("status", help="Inspect token validity, expiration, and active credential profiles", parents=[shared])

    # auth logout
    p_logout = auth_sub.add_parser("logout", help="Safely delete credentials from OS vault and encrypted fallback", parents=[shared])
    p_logout.add_argument("provider", nargs="?", choices=["anthropic", "claude", "cursor", "gemini", "google", "openai", "gpt"], default=None, help="Provider to log out from")
    p_logout.add_argument("--all", action="store_true", help="Purge all credentials across all providers")

    # register
    p_reg = sub.add_parser("register", help="Register a local repository checkout as a domain harness", parents=[shared])
    p_reg.add_argument("path", help="Path to repository to register")
    p_reg.add_argument("--name", help="Friendly name for the harness")
    p_reg.add_argument("--domain", help="Explicit domain description")
    p_reg.add_argument("--active", action="store_true", help="Set as active harness immediately")

    # deregister
    p_dereg = sub.add_parser("deregister", aliases=["rm", "remove"], help="Deregister a harness from the local catalog", parents=[shared])
    p_dereg.add_argument("id_or_path", help="Harness ID or path to deregister")

    # list
    sub.add_parser("list", aliases=["ls"], help="List all registered domain harnesses", parents=[shared])

    # switch
    p_switch = sub.add_parser("switch", help="Switch active harness to target ID or path", parents=[shared])
    p_switch.add_argument("id_or_path", help="Target harness ID or directory path")

    # scan
    p_scan = sub.add_parser("scan", help="Auto-discover sibling harness repositories", parents=[shared])
    p_scan.add_argument("directory", nargs="?", default=None, help="Parent directory to scan (defaults to sibling directory)")
    p_scan.add_argument("--no-register", action="store_true", help="Discover without auto-registering")

    # tui
    sub.add_parser("tui", aliases=["switcher"], help="Launch interactive terminal UI switcher", parents=[shared])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            return cmd_tui(args)
        if getattr(args, "json", False):
            return cmd_list(args)
        parser.error("the following arguments are required: cmd")

    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "branch":
        return cmd_branch(args)
    if args.cmd == "agent":
        return cmd_agent(args)
    if args.cmd == "pr":
        return cmd_pr(args)
    if args.cmd == "clean":
        return cmd_clean(args)
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.cmd == "register":
        return cmd_register(args)
    if args.cmd in ("deregister", "rm", "remove"):
        return cmd_deregister(args)
    if args.cmd in ("list", "ls"):
        return cmd_list(args)
    if args.cmd == "switch":
        return cmd_switch(args)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd in ("tui", "switcher"):
        return cmd_tui(args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
