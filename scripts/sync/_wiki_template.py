"""Wiki-template include/exclude rules for the generic ai-harness-core export.

Not indexed (leading underscore). Used by sync_public_repos.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
_ROUTING = Path(__file__).resolve().parents[1] / "routing"
for _p in (_LIB, _ROUTING):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from md import load_skill_record, skill_paths  # noqa: E402
from areas import AreasYamlError  # noqa: E402
from generate_routing_index import render_agent_dispatch, render_area_map  # noqa: E402
from generate_script_index import render_script_index  # noqa: E402

WIKI_TEMPLATE_MODE = "wiki_template"

WIKI_TEMPLATE_ALLOWED_DOT_DIRS: frozenset[str] = frozenset({".harness"})

WIKI_TEMPLATE_ROOT_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "naming-conventions.md",
        ".gitignore",
        ".markdownlint-cli2.jsonc",
        "sgconfig.yml",
    }
)

WIKI_TEMPLATE_KEEP_SKILLS: frozenset[str] = frozenset(
    {
        "agent-builder",
        "antagonistic-review",
        "anti-slop",
        "architecture-diagram",
        "as-code-builder",
        "ast-grep",
        "code-review-report",
        "corpus-draft",
        "cost-layer-dry-run",
        "deep-research",
        "doc-builder",
        "executive-report",
        "git-basics",
        "github-paths",
        "github-workflow",
        "guidance-draft",
        "headroom",
        "humanizer",
        "isolate-work",
        "markdownlint",
        "memory-adjust",
        "memory-cleanup",
        "memory-create",
        "mermaid-diagram",
        "proposal-report",
        "qmd-efficiency",
        "qmd-usage",
        "reference-maintain",
        "scratch-cleanup",
        "script-builder",
        "skill-builder",
        "skill-dry-run",
        "sync-downstream-repos",
        "router-structure",
    }
)

WIKI_TEMPLATE_DROP_SKILL_PREFIXES: tuple[str, ...] = ("aws-", "azure-", "gcp-")

WIKI_TEMPLATE_DROP_SKILLS: frozenset[str] = frozenset(
    {
        "framework-mapper",
        "threat-model",
        "noir-scan",
        "foundation-site",
        "tabler-dashboard",
    }
)

# Domain-tied specialists whose skills were dropped (aws/azure/gcp, STRIDE, etc.).
WIKI_TEMPLATE_DROP_AGENTS: frozenset[str] = frozenset(
    {
        "cloud-operator",
        "cloud-admin-agent",
        "assessment-agent",
    }
)

# Leftover dest-root engine packaging from older ai-harness-core releases.
# Do not prune `.harness/` (that is the template engine).
WIKI_TEMPLATE_PRUNE_DEST_NAMES: frozenset[str] = frozenset(
    {
        "harness",
        "pyproject.toml",
        "tests",
    }
)

WIKI_TEMPLATE_KEEP_SCRIPT_DIRS: frozenset[str] = frozenset(
    {
        "_lib",
        "routing",
        "qmd",
        "cost-layers",
        "change-history",
        "sync",
        "repos",
        "tests",
        "docs",
        "github",
        "ai-tooling",
    }
)

# Dest-relative paths that must not be copied. Export-redaction self-tests hold
# fake secrets; redaction rewrites them into invalid Python (unquoted
# [REDACTED_*] / quote-injecting assignment replacements) and dest CI compileall
# fails. Keep those tests in the private router only.
#
# Catalog-size / instance-skill tests stay in dest when the source file is
# template-safe (skip or use a kept skill). Do not add hybrid/skill-graph/
# validate-agent here unless a file cannot be made template-safe.
WIKI_TEMPLATE_DEST_EXCLUDE_RELS: frozenset[str] = frozenset(
    {
        "scripts/tests/test_sync_public_repos.py",
        "scripts/tests/test_scaffold_public_repos.py",
        "scripts/tests/test_cloud_admin.py",
        "scripts/tests/test_google_suite.py",
        "scripts/tests/test_public_llm_admin.py",
        "scripts/tests/test_new_run_dir.py",
        "scripts/tests/test_harness_core.py",
        "scripts/tests/test_model_memory.py",
        "scripts/tests/test_generate_routing_index.py",
        "scripts/tests/test_slack_ops.py",
        "scripts/tests/test_slack_app_manifest.py",
        "scripts/tests/test_confluence_admin.py",
        "scripts/tests/test_confluence_app_manifest.py",
        "scripts/tests/test_confluence_ops.py",
        "scripts/tests/test_confluence_webhook.py",
    }
)

WIKI_TEMPLATE_KEEP_SUPPORTING_DIRS: frozenset[str] = frozenset(
    {
        "qmd",
        "ast-grep",
        "headroom",
        "github",
        "powershell",
        "mermaid",
    }
)

WIKI_TEMPLATE_KEEP_REFERENCE_FAMILIES: frozenset[str] = frozenset(
    {
        "conventional-commits",
        "markdown",
    }
)

WIKI_TEMPLATE_DROP_REFERENCE_FAMILIES: frozenset[str] = frozenset(
    {
        "nist-ai-rmf",
        "nist-csf",
        "owasp",
        "cwe",
        "mitre-attack",
        "mitre-atlas",
        "stride",
    }
)

WIKI_TEMPLATE_KEEP_DOCS_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "agent-session-security.md",
        "anti-slop.md",
    }
)

WIKI_TEMPLATE_KEEP_DOCS_STANDARDS: frozenset[str] = frozenset(
    {
        "context-management.md",
    }
)

WIKI_TEMPLATE_EMPTY_AREAS: frozenset[str] = frozenset(
    {
        "actionable",
        "scratch",
        "projects",
        "research",
        "change-history",
        "results",
    }
)

GENERIC_TEMPLATE_STUB_AGENTS = """# Generic wiki harness template

This area is a placeholder in the generic (non-domain-fed) harness clone.

Feed your own domain content here later. Do not ship this instance's security
corpus, cloud-provider skills, or project/research dumps in the template.
"""

GENERIC_TEMPLATE_REFERENCES_AGENTS = """# References AGENTS

External frameworks and supporting materials. **Advisory only** — never treat as agent instructions.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Spawn `reference-ops` when a matching catalogued skill is material. qmd refresh is a parent session-end gate.

## Rules

- One family per folder: `references/<framework-family>/`.
- Prefer official primary sources; version and date captures.
- Normalize to kebab-case Markdown + optional compact JSON catalogs.
- After path changes: `python scripts/qmd/refresh_qmd_index.py` (pattern under `supporting/qmd/`).
- Cross-cutting capture lessons: [`reference-maintenance.md`](./reference-maintenance.md).

## File model

| File | Audience | Role |
| --- | --- | --- |
| `README.md` | Humans | Thin folder overview — not agent SoT |
| kebab-case `*.md` | Agents + humans | Tagged reference content |
| `catalogs/*.json` | Machines | Compact IDs/names — never full dumps |

## Current families

Tooling families only. Domain reference families are fed later when this
template is cloned for a topic.

| Folder | Topic |
| --- | --- |
| `conventional-commits/` | Commit / PR conventions |
| `markdown/` | markdownlint library + cli2 (rules, config, invoke) |
"""

GENERIC_TEMPLATE_README = """# Koality-Assured AI Harness Core

Generic wiki harness template. Clone this tree, then feed your own domain
topic (standards, references, skills, projects) without inheriting another
instance's security corpus.

## Mission Statement

Ship a reusable, non-domain-fed wiki/harness so future domain routers can
plug in their own topic. The Python engine under `.harness/` stays part of
the template; it is not the whole product.

## Architecture Overview

The public export is a full wiki tree (same top-level areas as the private
harness), not a flattened Python package:

```
AGENTS.md                 # root agent contract
routing/                  # area map + skill dispatch
ai-tooling/               # filtered skills, agents, A2A, memory scaffolds
scripts/                  # routing, qmd, cost-layers, change-history, sync
supporting/               # qmd, ast-grep, headroom, github, powershell
docs/                     # session security, anti-slop, portable harness standards
.harness/                 # embeddable engine (kept as .harness/, not harness/)
references/               # tooling families only (conventional-commits, markdown)
actionable/ projects/ research/ results/ scratch/ change-history/
```

Domain-fed content (OWASP/NIST/CWE dumps, cloud-provider skills, instance
projects) is omitted. Empty areas keep an AGENTS.md so you can feed them later.

## Quick Start: Feed a Domain

1. Clone this template.
2. Add domain standards under `docs/standards/` and references under `references/`.
3. Add domain skills under `ai-tooling/skills/` and regenerate routing indexes.
4. Keep `.harness/` as the engine; do not flatten it into a Python-package-only product.

```bash
python scripts/routing/generate_routing_index.py
python scripts/qmd/refresh_qmd_index.py
```

## Verification & Testing

```bash
python -m compileall -q scripts .harness
python -m unittest discover -s scripts/tests -v
```

## Security Notice

Public export still runs redaction/audit. Never commit secrets, home paths, or
tokens. Session security MUST lives in `docs/agent-session-security.md`.

## License

MIT License Copyright (c) 2026 Koality-Assured.
"""

GENERIC_TEMPLATE_CI = """name: Wiki harness template CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Compile kept Python
        run: python -m compileall -q -f scripts .harness
      - name: Script tests
        run: |
          python -m pip install --quiet pyyaml
          if [ -d scripts/tests ]; then python -m unittest discover -s scripts/tests -v; fi
"""


def _posix_parts(rel: str) -> list[str]:
    return [p for p in rel.replace("\\", "/").split("/") if p and p != "."]


def skill_is_kept(skill_name: str) -> bool:
    """Return True if a skill directory should be copied into the wiki template."""
    if skill_name.startswith(WIKI_TEMPLATE_DROP_SKILL_PREFIXES):
        return False
    if skill_name in WIKI_TEMPLATE_DROP_SKILLS:
        return False
    return skill_name in WIKI_TEMPLATE_KEEP_SKILLS


def agent_is_kept(agent_name: str) -> bool:
    """Return True if an agent directory should be copied into the wiki template."""
    if agent_name in WIKI_TEMPLATE_DROP_AGENTS:
        return False
    if agent_name in {"AGENTS.md", "model-tiers.md", "README.md"}:
        return True
    return True


def is_wiki_template_rel_kept(rel: str) -> bool:
    """Return True if a source-root-relative file belongs in ai-harness-core."""
    parts = _posix_parts(rel)
    if not parts:
        return False
    if "/".join(parts) in WIKI_TEMPLATE_DEST_EXCLUDE_RELS:
        return False
    top = parts[0]
    if top in {".git", ".github", ".cursor"}:
        return False
    if len(parts) == 1 and top in WIKI_TEMPLATE_ROOT_FILES:
        return True
    if top in {"routing", "config", ".harness"}:
        if top == "routing" and len(parts) == 2 and parts[1] in {
            "skill-dispatch.md",
            "area-map.md",
            "agent-dispatch.md",
        }:
            return False
        return True
    if top == "scripts":
        return _keep_scripts(parts)
    if top == "supporting":
        return _keep_supporting(parts)
    if top == "docs":
        return _keep_docs(parts)
    if top == "references":
        return _keep_references(parts)
    if top == "ai-tooling":
        return _keep_ai_tooling(parts)
    if top in WIKI_TEMPLATE_EMPTY_AREAS:
        return _keep_empty_area(parts)
    return False


def wiki_template_dir_may_contain_kept(rel_dir: str) -> bool:
    """Return True if os.walk should descend into this source-root-relative dir."""
    parts = _posix_parts(rel_dir)
    if not parts:
        return True
    top = parts[0]
    if top in {".git", ".github", ".cursor"}:
        return False
    if top in WIKI_TEMPLATE_ROOT_FILES:
        return False
    if top in {"routing", "config", ".harness"}:
        return True
    if top == "scripts":
        if len(parts) == 1:
            return True
        return parts[1] in WIKI_TEMPLATE_KEEP_SCRIPT_DIRS
    if top == "supporting":
        if len(parts) == 1:
            return True
        return parts[1] in WIKI_TEMPLATE_KEEP_SUPPORTING_DIRS
    if top == "docs":
        if len(parts) == 1:
            return True
        return parts[1] == "standards" and len(parts) == 2
    if top == "references":
        if len(parts) == 1:
            return True
        return parts[1] in WIKI_TEMPLATE_KEEP_REFERENCE_FAMILIES
    if top == "ai-tooling":
        return _ai_tooling_dir_may_contain_kept(parts)
    if top in WIKI_TEMPLATE_EMPTY_AREAS:
        if len(parts) == 1:
            return True
        if top == "projects" and parts[1] == "notes" and len(parts) <= 2:
            return True
        return False
    return False


def wiki_template_stub_files() -> dict[str, str]:
    """Dest-relative files written after copy when the source has no equivalent."""
    return {
        "docs/standards/AGENTS.md": GENERIC_TEMPLATE_STUB_AGENTS,
        "references/AGENTS.md": GENERIC_TEMPLATE_REFERENCES_AGENTS,
    }


def wiki_template_post_copy_files(dest_root: Path) -> dict[str, str]:
    """Dest-relative files generated after the filtered copy (stubs + dest indexes)."""
    files = dict(wiki_template_stub_files())
    files["routing/skill-dispatch.md"] = render_dest_skill_dispatch(dest_root)
    files["routing/area-map.md"] = render_dest_area_map(dest_root)
    files["routing/agent-dispatch.md"] = render_dest_agent_dispatch(dest_root)
    files["scripts/script-index.md"] = render_dest_script_index(dest_root)
    files["README.md"] = GENERIC_TEMPLATE_README
    files[".github/workflows/ci.yml"] = GENERIC_TEMPLATE_CI
    return files


def render_dest_agent_dispatch(dest_root: Path) -> str:
    """Build agent-dispatch.md from dest ai-tooling/agents (kept agents only)."""
    try:
        return render_agent_dispatch(dest_root, now="export")
    except Exception:
        return ""


def render_dest_area_map(dest_root: Path) -> str:
    """Build area-map.md from dest routing/areas.yaml (no source catalog copy)."""
    try:
        return render_area_map(dest_root, now="export")
    except AreasYamlError:
        # Dry-run / first pass before dest areas.yaml exists on disk.
        return (
            "---\n"
            "doc_kind: routing_map\n"
            "canonical_id: area-map\n"
            "topics: [routing, write-back, structure]\n"
            "generated_at_utc: export\n"
            "generator: scripts/sync/_wiki_template.py (dest routing/areas.yaml)\n"
            "---\n\n"
            "# Area map\n\n"
            "Generated from dest [`areas.yaml`](./areas.yaml) after wiki-template export. "
            "Do not hand-edit — run `python scripts/routing/generate_routing_index.py` "
            "from the dest checkout.\n\n"
            "Match [`skill-dispatch.md`](./skill-dispatch.md) first. Use this table only when no skill row applies.\n\n"
            "## Areas\n\n"
            "| Area | Purpose | Default agent | Load | Write-back |\n"
            "| --- | --- | --- | --- | --- |\n"
        )


def render_dest_script_index(dest_root: Path) -> str:
    """Build script-index.md from dest scripts/ (kept trees only)."""
    text = render_script_index(dest_root / "scripts", now="export")
    # Clarify this index is dest-side after filter, not a copy of source catalog.
    return text.replace(
        "Generated from Python docstring `tags:` / `routing_hints:`. Do not hand-edit — run `python scripts/routing/generate_script_index.py`.",
        "Generated from dest `scripts/` after wiki-template export (kept trees only). "
        "Do not hand-edit — run `python scripts/routing/generate_script_index.py` "
        "from the dest checkout after feeding scripts.",
    )


def wiki_template_prune_dest_leftovers(dest_root: Path) -> list[str]:
    """Remove dest-root engine leftovers that are not part of the wiki template.

    Never deletes `.harness/` or `.git/`. Returns pruned relative names.
    """
    pruned: list[str] = []
    for name in sorted(WIKI_TEMPLATE_PRUNE_DEST_NAMES):
        if name.startswith("."):
            continue
        target = dest_root / name
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        pruned.append(name)

    # Prune excluded test files and specific rels
    for rel in sorted(WIKI_TEMPLATE_DEST_EXCLUDE_RELS):
        target = dest_root / rel
        if target.exists():
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            pruned.append(rel)

    # Prune dropped agents
    agents_root = dest_root / "ai-tooling" / "agents"
    if agents_root.is_dir():
        for agent_dir in sorted(agents_root.iterdir()):
            if agent_dir.is_dir() and (agent_dir.name in WIKI_TEMPLATE_DROP_AGENTS or not agent_is_kept(agent_dir.name)):
                shutil.rmtree(agent_dir)
                pruned.append(f"ai-tooling/agents/{agent_dir.name}")

    # Prune dropped skills
    skills_root = dest_root / "ai-tooling" / "skills"
    if skills_root.is_dir():
        for family_dir in sorted(skills_root.iterdir()):
            if family_dir.is_dir():
                for skill_dir in sorted(family_dir.iterdir()):
                    if skill_dir.is_dir() and not skill_is_kept(skill_dir.name):
                        shutil.rmtree(skill_dir)
                        pruned.append(f"ai-tooling/skills/{family_dir.name}/{skill_dir.name}")

    return pruned


def wiki_template_sanitize_file_content(rel: str, raw_text: str) -> str:
    """Sanitize file contents for wiki template export (e.g. drop unkept delegation targets)."""
    parts = _posix_parts(rel)
    if len(parts) >= 3 and parts[0] == "ai-tooling" and parts[1] == "agents" and parts[-1] == "AGENT.md":
        lines = raw_text.splitlines()
        out: list[str] = []
        in_delegation_targets = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("delegation_targets:"):
                in_delegation_targets = True
                out.append(line)
                continue
            if in_delegation_targets:
                if stripped.startswith("- "):
                    target_agent = stripped[2:].strip().strip("'\"")
                    if target_agent in WIKI_TEMPLATE_DROP_AGENTS or not agent_is_kept(target_agent):
                        continue
                elif stripped and not stripped.startswith("#"):
                    in_delegation_targets = False
            out.append(line)
        return "\n".join(out) + ("\n" if raw_text.endswith("\n") else "")
    return raw_text


def render_dest_skill_dispatch(dest_root: Path) -> str:
    """Build skill-dispatch.md from dest skill frontmatter (kept skills only)."""
    rows: list[dict[str, Any]] = []
    skills_root = dest_root / "ai-tooling" / "skills"
    if skills_root.is_dir():
        for path in skill_paths(dest_root):
            rows.append(load_skill_record(path))
    rows.sort(key=lambda r: str(r.get("name", "")))

    def _md_cell(value: str) -> str:
        return value.replace("|", "\\|")

    def _agent_cell(owner: str) -> str:
        if owner in {"", "—", "none"}:
            return "`none`" if owner == "none" else (owner or "—")
        return f"[`{owner}`](../ai-tooling/agents/{owner}/AGENT.md)"

    skill_link_map = {}
    for r in rows:
        p = r.get("path")
        if isinstance(p, Path):
            skill_link_map[r["name"]] = (Path("..") / p.relative_to(dest_root)).as_posix()
        else:
            skill_link_map[r["name"]] = f"../ai-tooling/skills/{r['name']}/SKILL.md"

    lines = [
        "---",
        "doc_kind: routing_map",
        "canonical_id: skill-dispatch",
        "topics: [routing, skills, agents]",
        "generated_at_utc: export",
        "generator: scripts/sync/_wiki_template.py (dest skill frontmatter)",
        "---",
        "",
        "# Skill dispatch",
        "",
        "Generated from dest `ai-tooling/skills/*/SKILL.md` frontmatter after wiki-template export. "
        "Do not hand-edit — re-export or run `python scripts/routing/generate_routing_index.py` "
        "from the dest checkout after feeding skills.",
        "",
        "| Skill | Owner agent | Rank | Isolation | When |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        link_target = skill_link_map.get(row["name"], f"../ai-tooling/skills/{row['name']}/SKILL.md")
        skill_link = f"[`{row['name']}`]({link_target})"
        lines.append(
            f"| {skill_link} | {_agent_cell(row['owner_agent'])} | `{row['rank']}` | "
            f"`{row['isolation']}` | {_md_cell(row['description'])} |"
        )

    lines.extend(
        [
            "",
            "## Composite skill prerequisites and failure policies",
            "",
            "| Skill | Required skills | Delegated skills | In-session skills | Binary prerequisites | Failure policy |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        link_target = skill_link_map.get(row["name"], f"../ai-tooling/skills/{row['name']}/SKILL.md")
        skill_link = f"[`{row['name']}`]({link_target})"
        deps = row.get("dependencies", {})
        req_list = deps.get("required_skills", [])
        del_list = deps.get("delegated_skills", [])
        ins_list = deps.get("in_session_skills", [])
        prereqs_list = row.get("prerequisites", [])

        req_str = (
            ", ".join(f"[`{s}`]({skill_link_map.get(s, f'../ai-tooling/skills/{s}/SKILL.md')})" for s in req_list)
            if req_list
            else "—"
        )
        del_str = (
            ", ".join(f"[`{s}`]({skill_link_map.get(s, f'../ai-tooling/skills/{s}/SKILL.md')})" for s in del_list)
            if del_list
            else "—"
        )
        ins_str = (
            ", ".join(f"[`{s}`]({skill_link_map.get(s, f'../ai-tooling/skills/{s}/SKILL.md')})" for s in ins_list)
            if ins_list
            else "—"
        )
        prereqs_str = ", ".join(f"`{p}`" for p in prereqs_list) if prereqs_list else "—"
        fail_str = f"`{row.get('on_failure', 'abort_and_rollback')}`"

        lines.append(
            f"| {skill_link} | {req_str} | {del_str} | {ins_str} | {prereqs_str} | {fail_str} |"
        )

    lines.append("")
    return "\n".join(lines)


def _keep_scripts(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] == "AGENTS.md":
        return True
    if len(parts) == 2 and parts[1] == "script-index.md":
        return False
    if len(parts) >= 2 and parts[1] in WIKI_TEMPLATE_KEEP_SCRIPT_DIRS:
        return True
    return False


def _keep_supporting(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] in {"AGENTS.md", "workstation-onboarding.md"}:
        return True
    if len(parts) >= 2 and parts[1] in WIKI_TEMPLATE_KEEP_SUPPORTING_DIRS:
        return True
    return False


def _keep_docs(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] in WIKI_TEMPLATE_KEEP_DOCS_FILES:
        return True
    if len(parts) == 3 and parts[1] == "standards" and parts[2] in WIKI_TEMPLATE_KEEP_DOCS_STANDARDS:
        return True
    return False


def _keep_references(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] == "AGENTS.md":
        return False
    if len(parts) == 2 and parts[1] == "reference-maintenance.md":
        return True
    if len(parts) >= 2 and parts[1] in WIKI_TEMPLATE_KEEP_REFERENCE_FAMILIES:
        return True
    if len(parts) >= 2 and parts[1] in WIKI_TEMPLATE_DROP_REFERENCE_FAMILIES:
        return False
    return False


def _keep_ai_tooling(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] == "AGENTS.md":
        return True
    if len(parts) >= 2 and parts[1] == "a2a":
        return True
    if len(parts) >= 2 and parts[1] == "agents":
        if len(parts) == 2:
            return True
        if len(parts) == 3 and parts[2] in {"AGENTS.md", "model-tiers.md", "README.md"}:
            return True
        if len(parts) >= 3:
            return agent_is_kept(parts[2])
        return False
    if len(parts) >= 2 and parts[1] == "skills":
        if len(parts) == 3 and parts[2] in {"AGENTS.md", "skill-conventions.md", "README.md"}:
            return True
        for p in parts[2:]:
            if p in WIKI_TEMPLATE_DROP_SKILLS or p.startswith(WIKI_TEMPLATE_DROP_SKILL_PREFIXES):
                return False
        return any(skill_is_kept(p) for p in parts[2:]) or len(parts) == 3
    if len(parts) >= 2 and parts[1] == "memory":
        if parts[-1] in {"AGENTS.md", ".gitkeep"}:
            if len(parts) >= 4 and parts[2] == "user":
                return False
            return True
        return False
    return False


def _keep_empty_area(parts: list[str]) -> bool:
    if parts[-1] == "AGENTS.md":
        return True
    if len(parts) == 2 and parts[0] == "results" and parts[1] == "results-conventions.md":
        return True
    return False


def _ai_tooling_dir_may_contain_kept(parts: list[str]) -> bool:
    if len(parts) == 1:
        return True
    if parts[1] in {"a2a"}:
        return True
    if parts[1] == "agents":
        if len(parts) == 2:
            return True
        if parts[2] in {"AGENTS.md", "model-tiers.md", "README.md"}:
            return True
        return agent_is_kept(parts[2])
    if parts[1] == "skills":
        if len(parts) == 2:
            return True
        for p in parts[2:]:
            if p in WIKI_TEMPLATE_DROP_SKILLS or p.startswith(WIKI_TEMPLATE_DROP_SKILL_PREFIXES):
                return False
        return True
    if parts[1] == "memory":
        if len(parts) >= 4 and parts[2] == "user":
            return False
        return True
    return False
