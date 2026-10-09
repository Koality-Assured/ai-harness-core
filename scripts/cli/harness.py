"""In-repo Python CLI control plane and conversation harness for ai-router.

tags: [harness, cli, routing, isolation, auth, keyring, chat, session]
routing_hints: [harness, cli, status, branch, agent, pr, clean, auth, login, logout, chat, sessions, commands]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

# Ensure _lib and scripts are in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from areas import load_area_records  # noqa: E402
from md import agent_paths, load_agent_record  # noqa: E402
from paths import REPO_ROOT  # noqa: E402

from cli.provider_client import (  # noqa: E402
    ANTHROPIC_DEFAULT_MODEL,
    PROVIDER_ALIASES,
    ProviderError,
    normalize_provider,
)

SUPPORTED_PROVIDERS: tuple[str, ...] = ("anthropic", "openai", "gemini", "cursor")

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


def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or get_checkout_root(),
        check=check,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


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

    # Worktrees are reported from Git's registration database, without area metadata.
    try:
        from routing.spawn_worktree import parse_worktrees  # noqa: E402

        worktree_proc = run_git(["worktree", "list", "--porcelain"], cwd=primary_root, check=False)
        if worktree_proc.returncode != 0:
            raise RuntimeError(worktree_proc.stderr or "git worktree list failed")
        worktrees = parse_worktrees(worktree_proc.stdout or "")
        worktree_error = None
    except Exception as exc:
        worktrees = []
        worktree_error = str(exc)

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
            "worktrees": worktrees,
        }
        if worktree_error:
            payload["worktrees_error"] = worktree_error
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

    print("\nRegistered Git Worktrees:")
    if not worktrees:
        print("  (none found)")
    else:
        for worktree in worktrees:
            print(f"  {worktree.get('branch', '(detached)')}: {worktree.get('path')}")
    if worktree_error:
        print(f"  Error reading Git worktrees: {worktree_error}", file=sys.stderr)

    return 0


def cmd_branch(args: argparse.Namespace) -> int:
    slug = args.slug.strip()
    if not SLUG_PATTERN.fullmatch(slug):
        print(f"error: slug must be kebab-case [a-z0-9-], got {slug!r}", file=sys.stderr)
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

    from routing.spawn_worktree import cmd_create  # noqa: E402

    return cmd_create(
        slug,
        dry_run=getattr(args, "dry_run", False),
        as_json=getattr(args, "json", False),
        root=primary_root,
    )

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

    # 1. Identify current branch
    branch_proc = run_git(["branch", "--show-current"], cwd=checkout_root, check=False)
    current_branch = branch_proc.stdout.strip()
    if not current_branch or current_branch.startswith("detached-at-"):
        print("error: cannot create PR from detached HEAD. Please checkout a named branch first.", file=sys.stderr)
        return 1

    from routing.spawn_worktree import default_branch_name  # noqa: E402

    try:
        base_branch = args.base or default_branch_name(primary_root)
    except (OSError, RuntimeError) as exc:
        print(f"error: could not determine the repository default branch: {exc}", file=sys.stderr)
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
    apply_cleanup = getattr(args, "apply", False)
    dry_run = getattr(args, "dry_run", False)
    if apply_cleanup and dry_run:
        print("error: --apply and --dry-run cannot be used together", file=sys.stderr)
        return 2

    primary_root = get_primary_repo_root()
    from routing.spawn_worktree import cmd_cleanup  # noqa: E402

    return cmd_cleanup(
        args.branch,
        args.pr,
        dry_run=not apply_cleanup,
        as_json=getattr(args, "json", False),
        root=primary_root,
    )

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
    provider = normalize_provider(raw_provider)
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

    provider = normalize_provider(raw_provider.lower().strip())
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


def _resolve_chat_credential(provider: str) -> tuple[str | None, int]:
    """Return (access_token, exit_code). Never prints raw tokens."""
    from cli.auth.keyring_vault import get_vault
    from cli.auth.oauth_flows import ensure_fresh_token

    vault = get_vault()
    cred = ensure_fresh_token(provider, vault=vault)
    if not cred or not cred.get("access_token"):
        print(
            f"error: no credentials for '{provider}'. Run: harness auth login {provider}",
            file=sys.stderr,
        )
        return None, 1
    return str(cred["access_token"]), 0


def _load_query_text(args: argparse.Namespace) -> str | None:
    q = getattr(args, "query", None)
    qf = getattr(args, "query_file", None)
    if q and qf:
        print("error: pass either -q/--query or --query-file, not both", file=sys.stderr)
        return None
    if qf:
        path = Path(qf)
        if not path.is_file():
            print(f"error: query file not found: {qf}", file=sys.stderr)
            return None
        return path.read_text(encoding="utf-8")
    if q is not None:
        return str(q)
    return None


def _open_or_resume_session(args: argparse.Namespace, store: Any) -> tuple[dict[str, Any] | None, int]:
    resume_id = getattr(args, "resume", None)
    cont = getattr(args, "continue_session", False)
    if resume_id and cont:
        print("error: pass either --resume or --continue, not both", file=sys.stderr)
        return None, 2
    if resume_id:
        session = store.get_session(resume_id)
        if session is None:
            print(f"error: session not found: {resume_id}", file=sys.stderr)
            return None, 1
        return session, 0
    if cont:
        session = store.latest_session()
        if session is None:
            print("error: no sessions to continue", file=sys.stderr)
            return None, 1
        return session, 0

    raw_provider = getattr(args, "provider", None) or "anthropic"
    provider = normalize_provider(raw_provider)
    if not provider:
        print(
            f"error: unsupported provider '{raw_provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
            file=sys.stderr,
        )
        return None, 1
    model = getattr(args, "model", None) or ""
    if provider == "anthropic" and not model:
        model = ANTHROPIC_DEFAULT_MODEL
    title = getattr(args, "title", None) or ""
    session = store.create_session(
        title=title,
        cwd=str(Path.cwd()),
        provider=provider,
        model=model,
    )
    return session, 0


def _handle_slash(
    line: str,
    *,
    store: Any,
    session: dict[str, Any],
    model_holder: list[str],
    compact_session_handler: Any = None,
) -> tuple[bool, int | None]:
    """Handle a slash line. Returns (handled, exit_code_or_None)."""
    from cli.command_registry import list_commands, parse_slash
    from cli.conversation import session_status_payload

    parsed = parse_slash(line)
    if parsed is None:
        return False, None
    name, arg = parsed
    if name in ("quit", "exit", "q"):
        return True, 0
    if name in ("help", ""):
        for cmd in list_commands():
            print(f"  /{cmd['name']:<12} {cmd['summary']}")
        return True, None
    if name == "status":
        payload = session_status_payload(store, session["id"])
        print(_format_chat_status(payload, model=model_holder[0]))
        return True, None
    if name == "model":
        if arg:
            model_holder[0] = arg
            store.touch_session(session["id"], model=arg)
            print(f"model set to {arg}")
        else:
            print(f"model={model_holder[0] or session.get('model') or '(unset)'}")
        return True, None
    if name == "sessions":
        for s in store.list_sessions(limit=20):
            print(f"  {s['id']}  {s.get('updated_at', '')}  {s.get('title') or '(untitled)'}")
        return True, None
    if name == "compact":
        if arg:
            print("usage: /compact", file=sys.stderr)
            return True, None
        if compact_session_handler is None:
            print("error: context compression is unavailable", file=sys.stderr)
            return True, None
        try:
            result = compact_session_handler()
        except ProviderError as exc:
            excerpt = f" — {exc.body_excerpt}" if exc.body_excerpt else ""
            print(f"error: context compression failed: {exc}{excerpt}", file=sys.stderr)
            return True, None
        except ValueError as exc:
            print(f"error: context compression failed: {exc}", file=sys.stderr)
            return True, None
        if result is None:
            print("nothing to compact: need at least three complete user-led turns")
            return True, None
        previous_id = session["id"]
        new_session = result["session"]
        session.clear()
        session.update(new_session)
        model_holder[0] = session.get("model") or ""
        print(
            f"compacted {result['compacted_turns']} middle turn(s) from {previous_id}; "
            f"active session={session['id']}"
        )
        return True, None
    if name == "title":
        if not arg:
            print("usage: /title <text>", file=sys.stderr)
            return True, None
        store.rename_session(session["id"], arg)
        session["title"] = arg
        print(f"title set to {arg}")
        return True, None
    if name == "busy":
        from cli.session_store import BUSY_MODES

        if not arg or arg.lower() == "status":
            print(f"busy={session.get('busy_mode') or 'interrupt'}")
            return True, None
        if arg.lower() == "help":
            print(_BUSY_HELP)
            return True, None
        mode = arg.lower()
        if mode not in BUSY_MODES:
            print(_BUSY_HELP, file=sys.stderr)
            return True, None
        store.set_busy_mode(session["id"], mode)
        session["busy_mode"] = mode
        print(f"busy={mode}")
        return True, None
    print(f"unknown command: /{name} (try /help)", file=sys.stderr)
    return True, None


_BUSY_HELP = (
    "usage: /busy [status|interrupt|queue|steer|help]\n"
    "interrupt (default) aborts a turn with Ctrl+C; queue sends waiting lines in order; "
    "steer sends one waiting line after the current answer. True steer-at-tool-boundary "
    "will be available in slice 13."
)


def _format_chat_status(payload: dict[str, Any], *, model: str = "") -> str:
    input_tokens = payload.get("input_tokens")
    output_tokens = payload.get("output_tokens")
    input_display = "n/a" if input_tokens is None else str(input_tokens)
    output_display = "n/a" if output_tokens is None else str(output_tokens)
    return (
        f"session={payload.get('session_id')} provider={payload.get('provider')} "
        f"model={model or payload.get('model')} messages={payload.get('message_count')} "
        f"input_tokens={input_display} output_tokens={output_display} cost=n/a"
    )


class _LinePump:
    """Read terminal lines in the background while a provider stream is active."""

    def __init__(self, source: Any) -> None:
        self._source = source
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._closed = False

    def start(self) -> None:
        threading.Thread(target=self._read, daemon=True, name="harness-chat-input").start()

    def _read(self) -> None:
        try:
            while True:
                line = self._source.readline()
                if not line:
                    self._lines.put(None)
                    return
                self._lines.put(line.rstrip("\r\n"))
        except (EOFError, OSError):
            self._lines.put(None)

    def get(self) -> str | None:
        if self._closed:
            return None
        line = self._lines.get()
        if line is None:
            self._closed = True
        return line

    def take_available(self, limit: int | None = None) -> list[str]:
        lines: list[str] = []
        while limit is None or len(lines) < limit:
            try:
                line = self._lines.get_nowait()
            except queue.Empty:
                break
            if line is None:
                self._closed = True
                break
            lines.append(line)
        return lines


def cmd_chat(
    args: argparse.Namespace,
    transport: Any = None,
    stream_transport: Any = None,
    tool_registry: Any = None,
) -> int:
    from cli.conversation import compact_session, run_turn
    from cli.session_store import SessionStore

    store = SessionStore()
    try:
        session, code = _open_or_resume_session(args, store)
        if session is None:
            return code

        provider = session.get("provider") or "anthropic"
        if getattr(args, "provider", None):
            resolved = normalize_provider(args.provider)
            if not resolved:
                print(
                    f"error: unsupported provider '{args.provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
                    file=sys.stderr,
                )
                return 1
            provider = resolved

        model_holder = [getattr(args, "model", None) or session.get("model") or ""]
        if provider == "anthropic" and not model_holder[0]:
            model_holder[0] = ANTHROPIC_DEFAULT_MODEL
        if provider in ("openai", "gemini") and not model_holder[0]:
            print(
                f"error: provider '{provider}' requires --model "
                "(no safe default confirmed from official docs)",
                file=sys.stderr,
            )
            return 1

        api_key, cred_code = _resolve_chat_credential(provider)
        if api_key is None:
            return cred_code

        if getattr(args, "title", None) and session.get("title") != args.title:
            store.rename_session(session["id"], args.title)

        query = _load_query_text(args)
        if query is None and (getattr(args, "query", None) is not None or getattr(args, "query_file", None)):
            return 1

        if query is not None:
            stream_enabled = not getattr(args, "no_stream", False)
            active_stream_transport = stream_transport or (transport if stream_enabled else None)
            try:
                assistant = run_turn(
                    store,
                    session["id"],
                    query,
                    provider=provider,
                    model=model_holder[0] or None,
                    api_key=api_key,
                    transport=transport,
                    stream=stream_enabled,
                    stream_transport=active_stream_transport,
                    on_delta=lambda delta: print(delta, end="", flush=True),
                    tool_registry=tool_registry,
                )
            except KeyboardInterrupt:
                print("\ninterrupted", file=sys.stderr)
                return 130
            except ProviderError as exc:
                if stream_enabled:
                    print()
                excerpt = f" — {exc.body_excerpt}" if exc.body_excerpt else ""
                print(f"error: {exc}{excerpt}", file=sys.stderr)
                return 1
            if stream_enabled:
                print()
            print(assistant)
            from cli.conversation import session_status_payload

            print(
                _format_chat_status(
                    session_status_payload(store, session["id"]),
                    model=model_holder[0],
                ),
                file=sys.stderr,
            )
            return 0

        if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
            print(
                "error: interactive chat requires a TTY; pass -q/--query or --query-file",
                file=sys.stderr,
            )
            return 1

        from cli.conversation import session_status_payload

        def compact_active_session() -> dict[str, Any] | None:
            return compact_session(
                store,
                session["id"],
                provider,
                model_holder[0] or None,
                api_key,
                transport,
            )

        print(_format_chat_status(session_status_payload(store, session["id"]), model=model_holder[0]))
        print("Type /help for commands, /quit to exit.")
        line_pump = _LinePump(sys.stdin)
        line_pump.start()
        pending_lines: list[str] = []
        while True:
            try:
                if pending_lines:
                    line = pending_lines.pop(0)
                else:
                    print("> ", end="", flush=True)
                    line = line_pump.get()
                if line is None:
                    print()
                    return 0
            except KeyboardInterrupt:
                print()
                return 0
            if not line.strip():
                continue
            handled, exit_code = _handle_slash(
                line,
                store=store,
                session=session,
                model_holder=model_holder,
                compact_session_handler=compact_active_session,
            )
            if handled:
                if exit_code is not None:
                    return exit_code
                continue
            try:
                steered_during_turn: list[str] = []

                def steer_after_tool_batch() -> str | None:
                    if (session.get("busy_mode") or "interrupt") != "steer" or steered_during_turn:
                        return None
                    waiting = line_pump.take_available(limit=1)
                    if waiting and waiting[0].strip():
                        steered_during_turn.append(waiting[0])
                        return waiting[0]
                    return None

                assistant = run_turn(
                    store,
                    session["id"],
                    line,
                    provider=provider,
                    model=model_holder[0] or None,
                    api_key=api_key,
                    transport=transport,
                    stream=not getattr(args, "no_stream", False),
                    stream_transport=stream_transport or transport,
                    on_delta=lambda delta: print(delta, end="", flush=True),
                    tool_registry=tool_registry,
                    on_tool_batch=steer_after_tool_batch,
                )
            except KeyboardInterrupt:
                if "steered_during_turn" in locals() and steered_during_turn:
                    pending_lines[0:0] = steered_during_turn
                print("\nTurn interrupted.")
                continue
            except ProviderError as exc:
                if "steered_during_turn" in locals() and steered_during_turn:
                    pending_lines[0:0] = steered_during_turn
                if not getattr(args, "no_stream", False):
                    print()
                excerpt = f" — {exc.body_excerpt}" if exc.body_excerpt else ""
                print(f"error: {exc}{excerpt}", file=sys.stderr)
                continue
            if not getattr(args, "no_stream", False):
                print()
            else:
                print(assistant)
            busy_mode = session.get("busy_mode") or "interrupt"
            if busy_mode == "queue":
                pending_lines.extend(line_pump.take_available())
            elif busy_mode == "steer":
                if not steered_during_turn:
                    pending_lines.extend(line_pump.take_available(limit=1))
        return 0
    finally:
        store.close()


def cmd_gateway(
    args: argparse.Namespace,
    transport: Any = None,
    stream_transport: Any = None,
    tool_registry: Any = None,
) -> int:
    from cli.adapters import AdapterRuntime, serve_gateway

    runtime = AdapterRuntime(
        provider=args.provider,
        model=args.model,
        transport=transport,
        stream_transport=stream_transport,
        tool_registry=tool_registry,
    )
    serve_gateway(runtime, host=args.host, port=args.port)
    return 0


def cmd_acp(
    args: argparse.Namespace,
    transport: Any = None,
    stream_transport: Any = None,
    tool_registry: Any = None,
) -> int:
    from cli.adapters import AdapterRuntime, run_acp_stdio

    runtime = AdapterRuntime(
        provider=args.provider,
        model=args.model,
        transport=transport,
        stream_transport=stream_transport,
        tool_registry=tool_registry,
    )
    run_acp_stdio(runtime)
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    from cli.session_store import SessionStore

    store = SessionStore()
    try:
        action = getattr(args, "sessions_cmd", None)
        as_json = getattr(args, "json", False)
        if action == "list" or action is None:
            rows = store.list_sessions()
            if as_json:
                print(json.dumps({"sessions": rows}, indent=2))
            else:
                if not rows:
                    print("(no sessions)")
                for s in rows:
                    print(
                        f"{s['id']}  {s.get('updated_at', '')}  "
                        f"{s.get('provider', '')}/{s.get('model', '')}  "
                        f"{s.get('title') or '(untitled)'}"
                    )
            return 0
        if action == "rename":
            sid = args.session_id
            title = args.title_text
            row = store.rename_session(sid, title)
            if row is None:
                print(f"error: session not found: {sid}", file=sys.stderr)
                return 1
            if as_json:
                print(json.dumps(row, indent=2))
            else:
                print(f"renamed {sid} -> {title}")
            return 0
        if action == "search":
            hits = store.search_messages(args.query)
            if as_json:
                print(json.dumps({"matches": hits}, indent=2))
            else:
                if not hits:
                    print("(no matches)")
                for h in hits:
                    snippet = (h.get("content") or "").replace("\n", " ")
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    print(f"{h['session_id']}  {h['role']}  {snippet}")
            return 0
        print(f"error: unknown sessions action '{action}'", file=sys.stderr)
        return 2
    finally:
        store.close()


def cmd_commands(args: argparse.Namespace) -> int:
    from cli.command_registry import list_commands

    cmds = list_commands()
    if getattr(args, "json", False):
        print(json.dumps({"commands": cmds}, indent=2))
    else:
        for c in cmds:
            print(f"/{c['name']:<12} {c['summary']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true", help="Format output as machine-readable JSON")
    shared.add_argument("--dry-run", action="store_true", help="Simulate operation without mutating state")
    shared.add_argument("--harness", help="Target specific registered domain harness by ID or path")

    parser = argparse.ArgumentParser(
        prog="harness",
        description="Unified Harness CLI Control Plane for domain harnesses and spokes.",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="cmd")

    # status
    sub.add_parser("status", help="Inspect git branch, cleanliness, and registered worktrees", parents=[shared])

    # branch
    p_branch = sub.add_parser("branch", help="Create a unique task worktree and branch", parents=[shared])
    p_branch.add_argument("slug", help="Kebab-case task name")

    # agent
    p_agent = sub.add_parser("agent", help="Inspect available agents or view detailed agent spec", parents=[shared])
    p_agent.add_argument("agent_id", nargs="?", default=None, help="Agent ID to inspect")

    # pr
    p_pr = sub.add_parser("pr", help="Run preflight validations, verify commits, and open PR", parents=[shared])
    p_pr.add_argument("--base", default=None, help="Target base branch (defaults to the repository's GitHub default)")
    p_pr.add_argument("--title", help="PR title (defaults to last commit message)")
    p_pr.add_argument("--body", help="PR description markdown")
    p_pr.add_argument("--draft", action="store_true", help="Create as a draft PR")

    # clean
    p_clean = sub.add_parser(
        "clean",
        help="Preview verified worktree archiving by default; --apply retains an archive and unregisters the worktree",
        parents=[shared],
    )
    p_clean.add_argument("--branch", help="Task branch; omit to derive it from the merged PR")
    p_clean.add_argument("--pr", type=int, required=True, help="Merged PR number in this repository")
    p_clean.add_argument(
        "--apply",
        action="store_true",
        help="Archive checkout and Git metadata, then unregister; the archive remains on disk",
    )

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
    p_reg.add_argument("--force", action="store_true", help="Replace an existing harness registration")

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

    # chat
    p_chat = sub.add_parser("chat", help="One-shot or interactive agent conversation", parents=[shared])
    p_chat.add_argument("-q", "--query", dest="query", default=None, help="One-shot user message")
    p_chat.add_argument("--query-file", dest="query_file", default=None, help="Read one-shot user message from file")
    p_chat.add_argument("--resume", dest="resume", default=None, help="Resume session by id")
    p_chat.add_argument("--continue", dest="continue_session", action="store_true", help="Resume latest session")
    p_chat.add_argument("--model", default=None, help="Model id (required for openai/gemini)")
    p_chat.add_argument(
        "--provider",
        default=None,
        choices=["anthropic", "claude", "cursor", "gemini", "google", "openai", "gpt"],
        help="Model provider (default: anthropic)",
    )
    p_chat.add_argument("--title", default=None, help="Session title")
    p_chat.add_argument(
        "--no-stream",
        action="store_true",
        help="Wait for the complete response and print it once",
    )

    # Gateway: documented OpenAI-compatible Chat Completions HTTP/SSE route.
    gateway_help = (
        "Serve a text-only OpenAI-compatible Chat Completions/SSE subset; "
        "uses tools registered by the server and rejects client tools or image content"
    )
    p_gateway = sub.add_parser("gateway", help=gateway_help, description=gateway_help, parents=[shared])
    p_gateway.add_argument("--host", default="127.0.0.1", help="Bind address (default: loopback only)")
    p_gateway.add_argument("--port", type=int, default=8642, help="Listen port (default: 8642)")
    p_gateway.add_argument("--provider", default="anthropic", choices=["anthropic", "gemini", "openai"], help="Provider used by the shared conversation loop")
    p_gateway.add_argument("--model", default=None, help="Default model for the configured provider")

    # ACP v1 stdio JSON-RPC adapter.
    p_acp = sub.add_parser("acp", help="Run the ACP v1 stdio JSON-RPC adapter", parents=[shared])
    p_acp.add_argument("--provider", default="anthropic", choices=["anthropic", "gemini", "openai"], help="Provider used by the shared conversation loop")
    p_acp.add_argument("--model", default=None, help="Model for the configured provider")

    # sessions
    p_sessions = sub.add_parser("sessions", help="List, rename, or search conversation sessions", parents=[shared])
    sess_sub = p_sessions.add_subparsers(dest="sessions_cmd")
    sess_sub.add_parser("list", help="List recent sessions", parents=[shared])
    p_sess_rename = sess_sub.add_parser("rename", help="Rename a session", parents=[shared])
    p_sess_rename.add_argument("session_id", help="Session id")
    p_sess_rename.add_argument("title_text", help="New title")
    p_sess_search = sess_sub.add_parser("search", help="Search message content", parents=[shared])
    p_sess_search.add_argument("query", help="Substring to match (SQL LIKE)")

    # commands
    sub.add_parser("commands", help="List slash commands available in harness chat", parents=[shared])

    return parser


def main(
    argv: list[str] | None = None,
    transport: Any = None,
    stream_transport: Any = None,
    tool_registry: Any = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd is None:
        if getattr(args, "json", False):
            return cmd_list(args)
        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            return cmd_tui(args)
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
    if args.cmd == "chat":
        return cmd_chat(
            args,
            transport=transport,
            stream_transport=stream_transport,
            tool_registry=tool_registry,
        )
    if args.cmd == "gateway":
        return cmd_gateway(args, transport=transport, stream_transport=stream_transport, tool_registry=tool_registry)
    if args.cmd == "acp":
        return cmd_acp(args, transport=transport, stream_transport=stream_transport, tool_registry=tool_registry)
    if args.cmd == "sessions":
        if getattr(args, "sessions_cmd", None) is None:
            args.sessions_cmd = "list"
        return cmd_sessions(args)
    if args.cmd == "commands":
        return cmd_commands(args)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
