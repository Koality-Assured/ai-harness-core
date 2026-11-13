"""Deterministic anti-rot auditor for the AI harness and router.

tags: [harness, audit, rot, hygiene, control-plane]
routing_hints: [harness-rot, audit-rot, dead-code, stale-worktrees, branch-pruning, anti-rot]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


DEPRECATED_MODEL_PATTERNS = [
    (re.compile(r"\bgemini-1\.5-(?:pro|flash)\b", re.IGNORECASE), "gemini-1.5 (use Gemini 4 Hydrogen / Gemini 3.8 Pro)"),
    (re.compile(r"\bgemini-3\.[167]\b", re.IGNORECASE), "gemini-3.1/3.6/3.7 (retired per GEMINI.md, use Gemini 4 Hydrogen / Gemini 3.8 Pro)"),
    (re.compile(r"\bgemini[- ]3\.8[- ]flash\b", re.IGNORECASE), "gemini-3.8-flash / Gemini 3.8 Flash (superseded by Gemini 4 Hydrogen)"),
    (re.compile(r"\bclaude-3-(?:opus|sonnet|haiku)\b", re.IGNORECASE), "claude-3 series (retired, use platform-native or Claude 5.5)"),
]

ROT_EXEMPT_PATTERN = re.compile(r"(?:#\s*rot:\s*exempt|rot_exempt:\s*true)", re.IGNORECASE)


def resolve_primary_repo_root(override: str | Path | None = None) -> Path:
    """Return the primary git repository root where .git and scratch/worktrees live."""
    if override:
        return Path(override).resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            top = proc.stdout.strip()
            if top:
                p = Path(top).resolve()
                return p.parent if p.name == ".git" else p
    except Exception:
        pass
    return Path(__file__).resolve().parents[2]


def run_git(cmd: List[str], cwd: Path, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def get_default_branch(repo_root: Path) -> str:
    """Resolve the default branch (main or master)."""
    try:
        res = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_root, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().split("/")[-1]
    except Exception:
        pass
    for b in ("main", "master"):
        res = run_git(["rev-parse", "--verify", b], cwd=repo_root, timeout=5)
        if res.returncode == 0:
            return b
    return "main"


def fetch_pr_map(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    """Fetch GitHub PR statuses in a single bulk call to avoid N+1 blocking calls."""
    pr_map: Dict[str, Dict[str, Any]] = {}
    try:
        res = subprocess.run(
            ["gh", "pr", "list", "--state", "all", "--json", "number,state,headRefName,title", "--limit", "100"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=8,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            if isinstance(data, list):
                for item in data:
                    head = item.get("headRefName")
                    if head:
                        pr_map[head] = item
    except Exception:
        pass
    return pr_map


@dataclass
class WorktreeRotItem:
    path: str
    branch: str
    status: str  # "merged_ready_to_clean", "stale_unmerged", "active_fresh"
    pr_number: Optional[int] = None
    pr_state: Optional[str] = None
    last_commit_date: Optional[str] = None
    recommendation: str = ""


@dataclass
class BranchRotItem:
    name: str
    merged_to_base: bool
    checked_out_in_worktree: bool = False
    recommendation: str = ""


@dataclass
class AgentRotItem:
    agent_id: str
    rel_path: str
    skills_owned: int
    areas_owned: int
    recommendation: str = ""


@dataclass
class ScriptRotItem:
    rel_path: str
    name: str
    references_found: int
    recommendation: str = ""


@dataclass
class ModelDeprecationItem:
    file_path: str
    line_number: int
    matched_text: str
    guidance: str


@dataclass
class RotAuditReport:
    timestamp_utc: str
    repo_root: str
    default_branch: str
    worktrees: List[WorktreeRotItem] = field(default_factory=list)
    merged_branches: List[BranchRotItem] = field(default_factory=list)
    orphaned_scripts: List[ScriptRotItem] = field(default_factory=list)
    unowned_agents: List[AgentRotItem] = field(default_factory=list)
    deprecated_model_mentions: List[ModelDeprecationItem] = field(default_factory=list)
    actionable_count: int = 0
    ok: bool = True


def audit_worktrees(repo_root: Path, pr_map: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[List[WorktreeRotItem], Set[str]]:
    items: List[WorktreeRotItem] = []
    checked_out_branches: Set[str] = set()

    res = run_git(["worktree", "list", "--porcelain"], cwd=repo_root)
    if res.returncode != 0:
        return items, checked_out_branches

    lines = res.stdout.splitlines()
    current_entry: Dict[str, str] = {}
    parsed_worktrees: List[Dict[str, str]] = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_entry:
                parsed_worktrees.append(current_entry)
                current_entry = {}
            continue
        parts = line.split(" ", 1)
        key = parts[0]
        val = parts[1] if len(parts) > 1 else "true"
        current_entry[key] = val
    if current_entry:
        parsed_worktrees.append(current_entry)

    default_branch = get_default_branch(repo_root)
    base_commit_res = run_git(["rev-parse", default_branch], cwd=repo_root)
    base_commit = base_commit_res.stdout.strip() if base_commit_res.returncode == 0 else ""

    if pr_map is None:
        pr_map = fetch_pr_map(repo_root)

    for wt in parsed_worktrees:
        path_str = wt.get("worktree", "")
        wt_path = Path(path_str).resolve()
        branch_ref = wt.get("branch", "")
        branch_name = branch_ref.replace("refs/heads/", "") if branch_ref else ""

        if branch_name:
            checked_out_branches.add(branch_name)

        # Skip primary repo and detached qmd checkouts
        if wt_path == repo_root or "scratch/qmd-main" in path_str.replace("\\", "/"):
            continue

        if not branch_name:
            continue

        # Check commit ancestry against default_branch
        ancestor_res = run_git(["merge-base", "--is-ancestor", branch_ref, default_branch], cwd=repo_root)
        is_ancestor = (ancestor_res.returncode == 0)

        branch_commit_res = run_git(["rev-parse", branch_ref], cwd=repo_root)
        branch_commit = branch_commit_res.stdout.strip() if branch_commit_res.returncode == 0 else ""

        # Query PR metadata from map
        pr_info = pr_map.get(branch_name)
        pr_number: Optional[int] = pr_info.get("number") if pr_info else None
        pr_state: Optional[str] = pr_info.get("state") if pr_info else None

        commit_res = run_git(["log", "-1", "--format=%cI", branch_ref], cwd=repo_root)
        commit_date = commit_res.stdout.strip() if commit_res.returncode == 0 else ""

        rel_path = str(wt_path.relative_to(repo_root)).replace("\\", "/") if wt_path.is_relative_to(repo_root) else str(wt_path)

        is_pr_merged = bool(pr_state and pr_state.upper() == "MERGED")
        is_branch_merged_to_base = bool(is_ancestor and branch_commit and base_commit and branch_commit != base_commit)

        if is_pr_merged or is_branch_merged_to_base or (is_ancestor and pr_number is not None):
            rec = f"python scripts/cli/harness.py clean --pr {pr_number} --apply (clean untracked cache first if present)" if pr_number else f"Archive and remove worktree {rel_path} (merged into {default_branch})"
            items.append(WorktreeRotItem(
                path=rel_path,
                branch=branch_name,
                status="merged_ready_to_clean",
                pr_number=pr_number,
                pr_state=pr_state or "MERGED",
                last_commit_date=commit_date,
                recommendation=rec,
            ))
        elif branch_commit == base_commit and not pr_number:
            items.append(WorktreeRotItem(
                path=rel_path,
                branch=branch_name,
                status="active_fresh",
                pr_number=None,
                pr_state="FRESH",
                last_commit_date=commit_date,
                recommendation=f"Active fresh worktree on branch {branch_name} (in progress)",
            ))
        else:
            items.append(WorktreeRotItem(
                path=rel_path,
                branch=branch_name,
                status="stale_unmerged",
                pr_number=pr_number,
                pr_state=pr_state or "NO_PR",
                last_commit_date=commit_date,
                recommendation=f"Review active status or resume work on branch {branch_name}",
            ))

    return items, checked_out_branches


def audit_merged_branches(repo_root: Path, checked_out_branches: Optional[Set[str]] = None) -> List[BranchRotItem]:
    items: List[BranchRotItem] = []
    default_branch = get_default_branch(repo_root)
    res = run_git(["branch", "--merged", default_branch, "--format=%(refname:short)"], cwd=repo_root)
    if res.returncode != 0:
        return items

    cur_branch_res = run_git(["branch", "--show-current"], cwd=repo_root)
    cur_branch = cur_branch_res.stdout.strip()

    active_set = checked_out_branches or set()
    if cur_branch:
        active_set.add(cur_branch)

    for line in res.stdout.splitlines():
        b = line.strip()
        if not b or b in {"main", "master", default_branch}:
            continue

        is_checked_out = (b in active_set)
        rec = "Cannot prune: branch currently checked out in an active worktree" if is_checked_out else f"git branch -d {b}"

        items.append(BranchRotItem(
            name=b,
            merged_to_base=True,
            checked_out_in_worktree=is_checked_out,
            recommendation=rec,
        ))
    return items


def audit_scripts_graph(repo_root: Path) -> List[ScriptRotItem]:
    items: List[ScriptRotItem] = []
    scripts_dir = repo_root / "scripts"
    if not scripts_dir.is_dir():
        return items

    all_scripts = [
        p for p in scripts_dir.rglob("*.py")
        if not p.name.startswith("_") and "_lib" not in p.parts
    ]

    scan_dirs = [
        repo_root / "ai-tooling" / "skills",
        repo_root / "ai-tooling" / "agents",
        repo_root / "scripts" / "tests",
        repo_root / "scripts" / "cli",
        repo_root / "scripts" / "routing",
        repo_root / ".github" / "workflows",
        repo_root / "docs",
        repo_root / "supporting",
    ]

    corpus_texts: List[str] = []
    for d in scan_dirs:
        if not d.exists():
            continue
        if d.is_file():
            try:
                corpus_texts.append(d.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
        else:
            for f in d.rglob("*"):
                if f.is_file() and f.suffix in {".py", ".md", ".yml", ".yaml", ".json"}:
                    try:
                        corpus_texts.append(f.read_text(encoding="utf-8", errors="ignore"))
                    except Exception:
                        pass

    # Note: script-index.md is intentionally excluded so auto-indexed scripts are not masked as orphans.

    script_texts = {p: p.read_text(encoding="utf-8", errors="ignore") for p in all_scripts}

    for s in all_scripts:
        rel_posix = s.relative_to(scripts_dir).as_posix()
        name = s.stem
        content = script_texts.get(s, "")

        if ROT_EXEMPT_PATTERN.search(content):
            continue

        if "tests" in s.parts:
            continue

        # Use word-boundary token matching to avoid substring false positives
        pattern_stem = re.compile(r"\b" + re.escape(name) + r"\b")

        in_corpus = sum(1 for t in corpus_texts if rel_posix in t or s.name in t or pattern_stem.search(t))
        in_other = sum(1 for p, t in script_texts.items() if p != s and (pattern_stem.search(t) or rel_posix in t))

        total_refs = in_corpus + in_other

        if total_refs == 0:
            items.append(ScriptRotItem(
                rel_path=f"scripts/{rel_posix}",
                name=s.name,
                references_found=0,
                recommendation=f"Review scripts/{rel_posix} for deprecation, removal, or add '# rot: exempt <reason>'",
            ))

    return items


def audit_agents_graph(repo_root: Path) -> List[AgentRotItem]:
    """Flag any non-router agent in ai-tooling/agents/ that owns 0 skills and 0 areas."""
    items: List[AgentRotItem] = []
    agents_dir = repo_root / "ai-tooling" / "agents"
    if not agents_dir.is_dir():
        return items

    skills_dir = repo_root / "ai-tooling" / "skills"
    skill_owners: Set[str] = set()
    if skills_dir.is_dir():
        for skill_file in skills_dir.rglob("SKILL.md"):
            try:
                stext = skill_file.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"^owner_agent:\s*([A-Za-z0-9_-]+)", stext, re.MULTILINE)
                if m:
                    skill_owners.add(m.group(1).strip())
            except Exception:
                pass

    area_owners: Set[str] = set()
    areas_yaml = repo_root / "routing" / "areas.yaml"
    if areas_yaml.is_file():
        try:
            import yaml
            data = yaml.safe_load(areas_yaml.read_text(encoding="utf-8", errors="ignore")) or {}
            for a in data.get("areas", []):
                owner = a.get("default_agent")
                if owner and owner not in {"—", "none"}:
                    area_owners.add(owner)
            for n in data.get("nested_defaults", []):
                owner = n.get("default_agent")
                if owner and owner not in {"—", "none"}:
                    area_owners.add(owner)
        except Exception:
            atext = areas_yaml.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"default_agent:\s*([A-Za-z0-9_-]+)", atext):
                val = m.group(1).strip()
                if val not in {"—", "none"}:
                    area_owners.add(val)

    for agent_dir in sorted(agents_dir.iterdir(), key=lambda p: p.name):
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        if agent_id in {"router", ".git"}:
            continue
        agent_file = agent_dir / "AGENT.md"
        if not agent_file.is_file():
            continue

        skills_count = 1 if agent_id in skill_owners else 0
        areas_count = 1 if agent_id in area_owners else 0

        if skills_count == 0 and areas_count == 0:
            rel_path = f"ai-tooling/agents/{agent_id}/AGENT.md"
            items.append(
                AgentRotItem(
                    agent_id=agent_id,
                    rel_path=rel_path,
                    skills_owned=0,
                    areas_owned=0,
                    recommendation=f"Review agent '{agent_id}' for consolidation, skill/area assignment, or retirement",
                )
            )
    return items


def audit_deprecated_models(repo_root: Path) -> List[ModelDeprecationItem]:
    items: List[ModelDeprecationItem] = []
    scan_roots = [
        repo_root / "docs",
        repo_root / "ai-tooling",
        repo_root / "supporting",
    ]

    for root_dir in scan_roots:
        if not root_dir.is_dir():
            continue
        for md_file in root_dir.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_str = str(md_file.relative_to(repo_root)).replace("\\", "/")
            if "change-history" in rel_str or "results" in rel_str or ROT_EXEMPT_PATTERN.search(text):
                continue

            for idx, line in enumerate(text.splitlines(), start=1):
                if ROT_EXEMPT_PATTERN.search(line) or any(w in line.lower() for w in ("retired", "legacy", "older", "historical", "superseded")):
                    continue
                for pattern, guidance in DEPRECATED_MODEL_PATTERNS:
                    m = pattern.search(line)
                    if m:
                        items.append(ModelDeprecationItem(
                            file_path=rel_str,
                            line_number=idx,
                            matched_text=m.group(0),
                            guidance=guidance,
                        ))
    return items


def run_audit(repo_root: Optional[Path] = None) -> RotAuditReport:
    root = resolve_primary_repo_root(repo_root)
    default_branch = get_default_branch(root)
    pr_map = fetch_pr_map(root)

    worktrees, checked_out_branches = audit_worktrees(root, pr_map=pr_map)
    branches = audit_merged_branches(root, checked_out_branches=checked_out_branches)
    scripts = audit_scripts_graph(root)
    unowned_agents = audit_agents_graph(root)
    models = audit_deprecated_models(root)

    # Actionable issues that cause gate failure:
    # 1. Merged worktrees needing clean
    # 2. Orphaned scripts with 0 references
    # 3. Active deprecation mentions
    # 4. Unowned / inactive agents (0 skills and 0 areas)
    # NOTE: Merged branches are retained by harness policy for provenance and are informational candidates unless --fix-branches is used.
    ready_worktrees = [w for w in worktrees if w.status == "merged_ready_to_clean"]
    actionable = len(ready_worktrees) + len(scripts) + len(unowned_agents) + len(models)

    return RotAuditReport(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        default_branch=default_branch,
        worktrees=worktrees,
        merged_branches=branches,
        orphaned_scripts=scripts,
        unowned_agents=unowned_agents,
        deprecated_model_mentions=models,
        actionable_count=actionable,
        ok=(actionable == 0),
    )


def fix_merged_branches(repo_root: Path, dry_run: bool = True) -> Tuple[List[str], List[str]]:
    """Safely prune merged branches, strictly ignoring branches checked out in any worktree."""
    _, checked_out_branches = audit_worktrees(repo_root)
    branches = audit_merged_branches(repo_root, checked_out_branches=checked_out_branches)
    pruned = []
    skipped = []

    for b in branches:
        if b.checked_out_in_worktree:
            skipped.append(b.name)
            continue
        if not dry_run:
            res = run_git(["branch", "-d", b.name], cwd=repo_root)
            if res.returncode == 0:
                pruned.append(b.name)
            else:
                skipped.append(b.name)
        else:
            pruned.append(b.name)
    return pruned, skipped


def format_report(report: RotAuditReport) -> str:
    lines = [
        f"=== AI Harness & Router Anti-Rot Audit ({report.timestamp_utc}) ===",
        f"Repository Root: {report.repo_root}",
        f"Default Branch:  {report.default_branch}\n",
        f"1. Worktrees ({len(report.worktrees)} registered):",
    ]

    ready_wts = [w for w in report.worktrees if w.status == "merged_ready_to_clean"]
    if ready_wts:
        for w in ready_wts:
            pr_str = f" [PR #{w.pr_number} {w.pr_state}]" if w.pr_number else ""
            lines.append(f"  [MERGED READY TO CLEAN] {w.path} ({w.branch}){pr_str}")
            lines.append(f"    Action: {w.recommendation}")
    else:
        lines.append("  None ready to clean.")

    active_fresh = [w for w in report.worktrees if w.status == "active_fresh"]
    if active_fresh:
        lines.append(f"  Active In-Progress Worktrees ({len(active_fresh)}):")
        for w in active_fresh:
            lines.append(f"    - {w.path} ({w.branch})")

    stale_wts = [w for w in report.worktrees if w.status == "stale_unmerged"]
    if stale_wts:
        lines.append(f"  Unmerged/In-Flight Worktrees ({len(stale_wts)}):")
        for w in stale_wts:
            lines.append(f"    - {w.path} ({w.branch})")

    lines.append(f"\n2. Merged Local Branches ({len(report.merged_branches)}):")
    prunable = [b for b in report.merged_branches if not b.checked_out_in_worktree]
    checked_out = [b for b in report.merged_branches if b.checked_out_in_worktree]
    if prunable:
        lines.append(f"  Prunable candidates ({len(prunable)}):")
        for b in prunable:
            lines.append(f"    - {b.name} -> {b.recommendation}")
    if checked_out:
        lines.append(f"  Retained (Active in worktree, {len(checked_out)}):")
        for b in checked_out:
            lines.append(f"    - {b.name} (checked out)")
    if not report.merged_branches:
        lines.append("  None.")

    lines.append(f"\n3. Orphaned Script Candidates ({len(report.orphaned_scripts)}):")
    if report.orphaned_scripts:
        for s in report.orphaned_scripts:
            lines.append(f"  - {s.rel_path} (0 references)")
            lines.append(f"    Action: {s.recommendation}")
    else:
        lines.append("  None.")

    lines.append(f"\n4. Unowned Agents ({len(report.unowned_agents)}):")
    if report.unowned_agents:
        for a in report.unowned_agents:
            lines.append(f"  - {a.agent_id} ({a.rel_path}): 0 skills, 0 areas")
            lines.append(f"    Action: {a.recommendation}")
    else:
        lines.append("  None.")

    lines.append(f"\n5. Deprecated Model Mentions ({len(report.deprecated_model_mentions)}):")
    if report.deprecated_model_mentions:
        for m in report.deprecated_model_mentions:
            lines.append(f"  - {m.file_path}:{m.line_number} -> '{m.matched_text}' ({m.guidance})")
    else:
        lines.append("  None.")

    lines.append(f"\nSummary: {report.actionable_count} actionable rot issue(s) detected.")
    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit AI harness & router for rot, dead code, stale worktrees, and deprecations."
    )
    parser.add_argument("--repo-root", type=Path, default=None, help="Repository root path.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--check", action="store_true", help="Exit code 1 if actionable rot is detected.")
    parser.add_argument("--fix-branches", action="store_true", help="Prune local branches already merged to default branch (skips active worktrees).")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for --fix-branches.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = resolve_primary_repo_root(args.repo_root)

    if args.fix_branches:
        dry_run = args.dry_run
        pruned, skipped = fix_merged_branches(repo_root, dry_run=dry_run)
        if args.json:
            print(json.dumps({"pruned_branches": pruned, "skipped_branches": skipped, "dry_run": dry_run}, indent=2))
        else:
            action = "Would prune" if dry_run else "Pruned"
            print(f"{action} {len(pruned)} merged branch(es): {', '.join(pruned) if pruned else 'none'}")
            if skipped:
                print(f"Skipped {len(skipped)} active worktree branch(es): {', '.join(skipped)}")
        return 0

    report = run_audit(repo_root)

    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_report(report))

    if args.check and not report.ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
