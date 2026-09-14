"""Shared core-spoke protocol helpers for harness template sync.

Not indexed (leading underscore). Used by scaffold_harness, pull_harness_core,
and propose_core_update.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from _harness_template import (
    HARNESS_TEMPLATE_DEST_EXCLUDE_RELS,
    HARNESS_TEMPLATE_DOMAIN_MARKERS,
    HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES,
    HARNESS_TEMPLATE_DROP_SKILL_FAMILIES,
    HARNESS_TEMPLATE_KEEP_DOCS_STANDARDS,
    HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES,
    agent_is_kept,
    is_harness_template_rel_kept,
    rel_has_instance_leak_name,
    script_test_is_kept,
)

DEFAULT_ORG = "Koality-Assured"
CORE_REPO_NAME = "ai-harness-core"
CORE_REMOTE_NAME = "harness-core"
ORIGIN_REMOTE_NAME = "origin"
DOMAIN_CHOICES: tuple[str, ...] = ("legal", "ui-ux", "financial", "game-dev", "none")
VISIBILITY_CHOICES: tuple[str, ...] = ("public", "private")
CORE_SOURCE_CHOICES: tuple[str, ...] = ("export", "clone", "path")

DOMAIN_DEFAULT_REPO_NAMES: dict[str, str | None] = {
    "legal": "legal-router",
    "ui-ux": "ui-ux-router",
    "financial": "financial-advisement-router",
    "game-dev": "game-dev-router",
    "none": None,
}

# Private is first-class. Public domains still default public to match empty remotes.
DOMAIN_DEFAULT_VISIBILITY: dict[str, str] = {
    "legal": "public",
    "ui-ux": "public",
    "financial": "public",
    "game-dev": "private",
    "none": "private",
}

REPO_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ORG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")

COPY_SKIP_DIR_NAMES: frozenset[str] = frozenset({"__pycache__", ".git"})
COPY_SKIP_FILE_NAMES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})

# Files a real ai-harness-core checkout has after template post-copy, but which
# is_harness_template_rel_kept rejects (they are generated, not source-copied).
CORE_CHECKOUT_EXTRA_RELS: frozenset[str] = frozenset(
    {
        "README.md",
        "LICENSE",
        ".editorconfig",
        ".github/workflows/ci.yml",
        "routing/skill-dispatch.md",
        "routing/area-map.md",
        "routing/agent-dispatch.md",
        "routing/by-task.md",
        "scripts/script-index.md",
        "docs/standards/AGENTS.md",
        "references/AGENTS.md",
        "projects/project-prompts/README.md",
    }
)

INSTANCE_LEAK_MARKERS: tuple[str, ...] = (
    "references/owasp",
    "references/nist-csf",
    "references/cwe",
    "docs/standards/identity-and-access.md",
    "ai-tooling/skills/aws",
    "ai-tooling/skills/slack",
    "ai-tooling/skills/confluence",
    "ai-tooling/skills/google",
    "projects/secpanic-idler",
    "research/secpanic-idler",
)

GAME_DEV_PUBLIC_REFUSED = (
    "refusing --visibility public for --domain game-dev; game-dev defaults to "
    "private. Pass --allow-public-game-dev only as an off-by-default break-glass."
)

GitRunner = Callable[..., tuple[int, str, str]]


def posix_rel(rel: str | Path) -> str:
    """Normalize a repo-relative path to posix (no leading ./)."""
    text = str(rel).replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return text.strip("/")


def github_https_url(org: str, name: str) -> str:
    """Return an https GitHub remote URL with no embedded credentials."""
    return f"https://github.com/{org}/{name}.git"


def core_remote_url(org: str = DEFAULT_ORG) -> str:
    return github_https_url(org, CORE_REPO_NAME)


def validate_repo_name(name: str) -> str:
    if not REPO_NAME_RE.fullmatch(name):
        raise ValueError(
            f"invalid --name {name!r}: expected kebab-case like legal-router"
        )
    return name


def validate_org(org: str) -> str:
    if not ORG_RE.fullmatch(org):
        raise ValueError(f"invalid --org {org!r}")
    return org


def validate_visibility(visibility: str) -> str:
    if visibility not in VISIBILITY_CHOICES:
        raise ValueError(f"invalid --visibility {visibility!r}: expected public|private")
    return visibility


def default_visibility(domain: str, override: str | None) -> str:
    if override:
        return validate_visibility(override)
    return DOMAIN_DEFAULT_VISIBILITY.get(domain, "private")


def refuse_public_game_dev(
    domain: str,
    visibility: str,
    *,
    allow_public_game_dev: bool = False,
) -> None:
    """Refuse public game-dev unless the explicit break-glass flag is on."""
    if domain == "game-dev" and visibility == "public" and not allow_public_game_dev:
        raise ValueError(GAME_DEV_PUBLIC_REFUSED)


def is_domain_marker(rel: str) -> bool:
    path = posix_rel(rel)
    if rel_has_instance_leak_name(path):
        return True
    if path in HARNESS_TEMPLATE_DOMAIN_MARKERS:
        return True
    if path.endswith("-overlay.md") and path.startswith("docs/standards/"):
        return True
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "ai-tooling" and parts[1] == "skills":
        if parts[2] in HARNESS_TEMPLATE_DROP_SKILL_FAMILIES:
            return True
    if len(parts) >= 3 and parts[0] == "ai-tooling" and parts[1] == "agents":
        if parts[2] not in {"AGENTS.md", "model-tiers.md", "README.md"} and not agent_is_kept(parts[2]):
            return True
    if len(parts) >= 3 and parts[0] == "scripts" and parts[1] == "tests":
        if path in HARNESS_TEMPLATE_DEST_EXCLUDE_RELS:
            return True
        if len(parts) != 3 or not script_test_is_kept(parts[2]):
            return True
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "standards":
        if len(parts) >= 3 and parts[2] not in HARNESS_TEMPLATE_KEEP_DOCS_STANDARDS:
            return True
    return False


def is_ignorable_copy_rel(rel: str) -> bool:
    """True for cache/junk paths that are neither copied nor a leak refusal."""
    parts = [p for p in posix_rel(rel).split("/") if p]
    if any(p in COPY_SKIP_DIR_NAMES for p in parts):
        return True
    if parts and parts[-1] in COPY_SKIP_FILE_NAMES:
        return True
    if parts and parts[-1].endswith((".pyc", ".pyo")):
        return True
    return False


def may_copy_core_source_rel(rel: str) -> bool:
    """True when a core-source file may be copied into a spoke."""
    path = posix_rel(rel)
    if not path or is_ignorable_copy_rel(path):
        return False
    parts = [p for p in path.split("/") if p]
    if not parts or parts[0] == ".git" or ".git" in parts:
        return False
    if is_domain_marker(path):
        return False
    if is_harness_template_rel_kept(path):
        return True
    return path in CORE_CHECKOUT_EXTRA_RELS


def is_instance_corpus_rel(rel: str) -> bool:
    """True when a path is fed-instance corpus that must not be copied."""
    path = posix_rel(rel)
    if rel_has_instance_leak_name(path):
        return True
    if is_domain_marker(path):
        return True
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    if len(parts) >= 3 and parts[0] == "ai-tooling" and parts[1] == "skills":
        if parts[2] in HARNESS_TEMPLATE_DROP_SKILL_FAMILIES:
            return True
    if len(parts) >= 2 and parts[0] == "references":
        fam = parts[1]
        if fam in HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES:
            return True
        if (
            fam not in HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES
            and fam not in {"AGENTS.md", "reference-maintenance.md"}
        ):
            return True
    if len(parts) >= 2 and parts[0] == "projects" and parts[1] not in {
        "notes",
        "project-prompts",
        "AGENTS.md",
    }:
        return True
    if len(parts) >= 4 and parts[0] == "ai-tooling" and parts[1] == "memory":
        if parts[2] in {"user", "agent", "model"} and parts[3] not in {"AGENTS.md", ".gitkeep"}:
            return True
    return False


def instance_corpus_rels(root: Path) -> list[str]:
    """Return dest-relative instance corpus paths under root."""
    hits = detect_instance_leakage(root)
    seen = set(hits)
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = posix_rel(path.relative_to(root).as_posix())
        if is_ignorable_copy_rel(rel):
            continue
        if is_instance_corpus_rel(rel) and rel not in seen:
            seen.add(rel)
            hits.append(rel)
    return hits


def is_allowlisted_core_path(rel: str) -> bool:
    """True when a spoke-relative path may be pulled from or proposed to core."""
    path = posix_rel(rel)
    if is_domain_marker(path):
        return False
    return is_harness_template_rel_kept(path)


def classify_spoke_path(rel: str) -> str:
    """Classify a path as core or domain."""
    path = posix_rel(rel)
    if is_domain_marker(path):
        return "domain"
    if is_harness_template_rel_kept(path):
        return "core"
    return "domain"


def read_domain_marker(root: Path) -> dict[str, object] | None:
    """Return parsed `.harness/domain.json` or None when missing/invalid."""
    path = root / ".harness" / "domain.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def spoke_visibility(root: Path) -> str | None:
    marker = read_domain_marker(root)
    if not marker:
        return None
    value = marker.get("visibility")
    return value if isinstance(value, str) else None


def detect_instance_leakage(root: Path) -> list[str]:
    """Return dest-relative markers that mean a fed instance was used as source."""
    hits: list[str] = []
    seen: set[str] = set()

    def _add(rel: str) -> None:
        path = posix_rel(rel)
        if path and path not in seen:
            seen.add(path)
            hits.append(path)

    for rel in INSTANCE_LEAK_MARKERS:
        target = root / Path(*rel.split("/"))
        if target.exists():
            _add(rel)
    memory_user = root / "ai-tooling" / "memory" / "user"
    if memory_user.is_dir():
        for child in memory_user.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                _add(f"ai-tooling/memory/user/{child.name}")
    projects = root / "projects"
    if projects.is_dir():
        for child in projects.iterdir():
            if child.is_dir() and child.name not in {"notes", "project-prompts"}:
                _add(f"projects/{child.name}")
    research = root / "research"
    if research.is_dir():
        for child in research.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                _add(f"research/{child.name}")
    if root.is_dir():
        for path in root.rglob("*"):
            if ".git" in path.parts:
                continue
            rel = posix_rel(path.relative_to(root).as_posix())
            if rel_has_instance_leak_name(rel):
                _add(rel)
    return hits


def domain_overlay_files(
    *,
    domain: str,
    name: str,
    org: str,
    visibility: str,
) -> dict[str, str]:
    """Return dest-relative stub files for a domain spoke."""
    origin = github_https_url(org, name)
    core = core_remote_url(DEFAULT_ORG)
    marker = {
        "schema": "harness-spoke/v1",
        "domain": domain,
        "name": name,
        "org": org,
        "visibility": visibility,
        "core_repo": f"{DEFAULT_ORG}/{CORE_REPO_NAME}",
        "remotes": {
            ORIGIN_REMOTE_NAME: origin,
            CORE_REMOTE_NAME: core,
        },
        "note": "Spoke overlay. Do not propose this file back to ai-harness-core.",
    }
    files: dict[str, str] = {
        ".harness/domain.json": json.dumps(marker, indent=2) + "\n",
    }
    if domain == "none":
        return files
    title = domain.replace("-", " ")
    files[f"docs/standards/{domain}-overlay.md"] = (
        "---\n"
        f"doc_kind: requirement\n"
        f"canonical_id: {domain}-overlay\n"
        f"purpose: [requirement]\n"
        f"rank: medium\n"
        f"topics: [{domain}, overlay]\n"
        f"rag_keywords: [{domain}, domain-overlay, spoke]\n"
        "---\n\n"
        f"# {title} domain overlay\n\n"
        f"This spoke is a `{domain}` harness scaffolded from `ai-harness-core`. "
        f"Feed {title} corpus here. Keep generic machinery in the core.\n\n"
        "Do not copy this overlay, instance `projects/`, `research/`, or "
        "`ai-tooling/memory/` back to the generic core.\n\n"
        "Pull core updates: `python scripts/sync/pull_harness_core.py --dry-run --json`.\n\n"
        "Propose generic core changes: `python scripts/sync/propose_core_update.py --dry-run --json`.\n"
    )
    return files


def run_git(
    args: list[str],
    cwd: Path,
    timeout: int = 60,
) -> tuple[int, str, str]:
    """Run a git subprocess with a list argv (never shell=True)."""
    if not args or args[0] != "git":
        raise ValueError("run_git requires argv starting with git")
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def list_remotes(repo: Path, runner: GitRunner = run_git) -> dict[str, str]:
    code, stdout, stderr = runner(["git", "remote", "-v"], cwd=repo)
    if code != 0:
        raise RuntimeError(stderr or "git remote -v failed")
    remotes: dict[str, str] = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            remotes[parts[0]] = parts[1]
    return remotes


def configure_remotes(
    repo: Path,
    *,
    origin_url: str,
    core_url: str,
    runner: GitRunner = run_git,
    dry_run: bool = False,
) -> dict[str, str]:
    """Set origin=domain repo and harness-core=ai-harness-core. No push."""
    planned = {
        ORIGIN_REMOTE_NAME: origin_url,
        CORE_REMOTE_NAME: core_url,
    }
    if dry_run:
        return planned
    existing = list_remotes(repo, runner=runner)
    for name, url in planned.items():
        if name in existing:
            code, _, err = runner(["git", "remote", "set-url", name, url], cwd=repo)
        else:
            code, _, err = runner(["git", "remote", "add", name, url], cwd=repo)
        if code != 0:
            raise RuntimeError(err or f"failed to set remote {name}")
    return planned


def git_init_if_needed(repo: Path, runner: GitRunner = run_git) -> bool:
    if (repo / ".git").exists():
        return False
    code, _, err = runner(["git", "init", "-b", "main"], cwd=repo)
    if code != 0:
        code, _, err = runner(["git", "init"], cwd=repo)
    if code != 0:
        raise RuntimeError(err or "git init failed")
    return True


def current_branch(repo: Path, runner: GitRunner = run_git) -> str:
    code, stdout, stderr = runner(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if code != 0:
        return "HEAD"
    return stdout or "HEAD"


def git_name_only(
    repo: Path,
    extra_args: list[str],
    runner: GitRunner = run_git,
) -> list[str]:
    code, stdout, stderr = runner(["git", *extra_args], cwd=repo)
    if code != 0:
        raise RuntimeError(stderr or "git name-only failed")
    return [posix_rel(line) for line in stdout.splitlines() if line.strip()]


def write_files(root: Path, files: dict[str, str], dry_run: bool) -> list[str]:
    written = sorted(files)
    if dry_run:
        return written
    for rel, content in files.items():
        dest = root / Path(*posix_rel(rel).split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return written


def ensure_initial_commit(repo: Path, message: str) -> None:
    """Create the first commit so pull_harness_core has HEAD. Never pushes."""
    code, _, err = run_git(["git", "add", "-A"], cwd=repo)
    if code != 0:
        raise RuntimeError(err or "git add failed")
    code, _, err = run_git(
        [
            "git",
            "-c",
            "user.email=harness-scaffold@example.com",
            "-c",
            "user.name=harness-scaffold",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
    )
    if code != 0:
        raise RuntimeError(err or "initial scaffold commit failed")


def copy_tree_filtered(src: Path, dest: Path, dry_run: bool) -> int:
    """Copy template-kept files from src to dest. Never copies .git or instance corpus."""
    count = 0
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    for path in src.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = posix_rel(path.relative_to(src).as_posix())
        if not may_copy_core_source_rel(rel):
            continue
        count += 1
        if dry_run:
            continue
        target = dest / Path(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    return count


def unique_paths(paths: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for rel in paths:
        path = posix_rel(rel)
        if path and path not in seen:
            seen.add(path)
            out.append(path)
    return out
