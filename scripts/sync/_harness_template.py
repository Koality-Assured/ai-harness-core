"""Harness-template include/exclude rules for the generic ai-harness-core export.

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

HARNESS_TEMPLATE_MODE = "harness_template"
WIKI_TEMPLATE_MODE = HARNESS_TEMPLATE_MODE  # Backward compatibility alias

HARNESS_TEMPLATE_ALLOWED_DOT_DIRS: frozenset[str] = frozenset(
    {
        ".harness",
        ".claude",
        ".cursor",
        ".github",
    }
)
WIKI_TEMPLATE_ALLOWED_DOT_DIRS = HARNESS_TEMPLATE_ALLOWED_DOT_DIRS

SKILL_FAMILIES: frozenset[str] = frozenset(
    {
        "admin",
        "aws",
        "azure",
        "benchmarks",
        "community",
        "confluence",
        "cost-layers",
        "gcp",
        "git",
        "google",
        "harness-review",
        "memory",
        "meta",
        "model-memory-operate",
        "reporting",
        "research",
        "slack",
    }
)

HARNESS_TEMPLATE_ROOT_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".cursorignore",
        "naming-conventions.md",
        ".gitignore",
        ".markdownlint-cli2.jsonc",
        "sgconfig.yml",
    }
)
WIKI_TEMPLATE_ROOT_FILES = HARNESS_TEMPLATE_ROOT_FILES

HARNESS_TEMPLATE_KEEP_SKILLS: frozenset[str] = frozenset(
    {
        "agent-builder",
        "agent-cost-estimator",
        "agent-fleet-benchmark",
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
        "harness-review",
        "headroom",
        "humanizer",
        "isolate-work",
        "local-webfetch",
        "markdownlint",
        "memory-adjust",
        "memory-cleanup",
        "memory-create",
        "mermaid-diagram",
        "model-memory-operate",
        "proposal-report",
        "qmd-efficiency",
        "qmd-usage",
        "readme-maintain",
        "reference-maintain",
        "retrieval-benchmark",
        "scratch-cleanup",
        "script-builder",
        "skill-builder",
        "skill-dry-run",
        "sync-downstream-repos",
        "task-eval-benchmark",
        "tool-efficiency-benchmark",
        "router-structure",
    }
)
WIKI_TEMPLATE_KEEP_SKILLS = HARNESS_TEMPLATE_KEEP_SKILLS

HARNESS_TEMPLATE_DROP_SKILL_PREFIXES: tuple[str, ...] = ("aws-", "azure-", "gcp-")
WIKI_TEMPLATE_DROP_SKILL_PREFIXES = HARNESS_TEMPLATE_DROP_SKILL_PREFIXES

HARNESS_TEMPLATE_DROP_SKILLS: frozenset[str] = frozenset(
    {
        "framework-mapper",
        "threat-model",
        "noir-scan",
        "foundation-site",
        "tabler-dashboard",
    }
)
WIKI_TEMPLATE_DROP_SKILLS = HARNESS_TEMPLATE_DROP_SKILLS

# Domain-tied specialists whose skills were dropped (aws/azure/gcp, STRIDE, etc.).
HARNESS_TEMPLATE_DROP_AGENTS: frozenset[str] = frozenset(
    {
        "cloud-operator",
        "cloud-admin-agent",
        "assessment-agent",
        "google-suite-operator",
        "google-suite-admin",
        "chat-collab-agent",
        "docs-collab-agent",
        "public-llm-admin",
        "community-analyst",
    }
)
WIKI_TEMPLATE_DROP_AGENTS = HARNESS_TEMPLATE_DROP_AGENTS

# Leftover dest-root engine packaging from older ai-harness-core releases.
# Do not prune `.harness/` (that is the template engine).
HARNESS_TEMPLATE_PRUNE_DEST_NAMES: frozenset[str] = frozenset(
    {
        "harness",
        "pyproject.toml",
        "tests",
    }
)
WIKI_TEMPLATE_PRUNE_DEST_NAMES = HARNESS_TEMPLATE_PRUNE_DEST_NAMES

HARNESS_TEMPLATE_KEEP_SCRIPT_DIRS: frozenset[str] = frozenset(
    {
        "_lib",
        "routing",
        "qmd",
        "cost-layers",
        "change-history",
        "sync",
        "repos",
        "research",
        "tests",
        "docs",
        "github",
        "ai-tooling",
        "benchmarks",
    }
)
WIKI_TEMPLATE_KEEP_SCRIPT_DIRS = HARNESS_TEMPLATE_KEEP_SCRIPT_DIRS

# Dest-relative paths that must not be copied. Export-redaction self-tests hold
# fake secrets; redaction rewrites them into invalid Python (unquoted
# [REDACTED_*] / quote-injecting assignment replacements) and dest CI compileall
# fails. Keep those tests in the private router only.
#
# Catalog-size / instance-skill tests stay in dest when the source file is
# template-safe (skip or use a kept skill).
HARNESS_TEMPLATE_DEST_EXCLUDE_RELS: frozenset[str] = frozenset(
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
        "scripts/tests/test_confluence_mcp_server.py",
        "scripts/tests/test_confluence_oauth.py",
        "scripts/tests/test_confluence_oddities_and_drift.py",
        "scripts/tests/test_confluence_sync.py",
        "scripts/tests/test_validate_wiki_structure.py",
        "scripts/docs/validate_wiki_structure.py",
    }
)
WIKI_TEMPLATE_DEST_EXCLUDE_RELS = HARNESS_TEMPLATE_DEST_EXCLUDE_RELS

HARNESS_TEMPLATE_KEEP_SUPPORTING_DIRS: frozenset[str] = frozenset(
    {
        "qmd",
        "ast-grep",
        "headroom",
        "github",
        "powershell",
        "mermaid",
        "benchmarks",
    }
)
WIKI_TEMPLATE_KEEP_SUPPORTING_DIRS = HARNESS_TEMPLATE_KEEP_SUPPORTING_DIRS

HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES: frozenset[str] = frozenset(
    {
        "conventional-commits",
        "markdown",
        "prompt-engineering",
        "valid-sources",
    }
)
WIKI_TEMPLATE_KEEP_REFERENCE_FAMILIES = HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES

HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES: frozenset[str] = frozenset(
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
WIKI_TEMPLATE_DROP_REFERENCE_FAMILIES = HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES

HARNESS_TEMPLATE_KEEP_DOCS_FILES: frozenset[str] = frozenset(
    {
        "AGENTS.md",
        "agent-session-security.md",
        "anti-slop.md",
    }
)
WIKI_TEMPLATE_KEEP_DOCS_FILES = HARNESS_TEMPLATE_KEEP_DOCS_FILES

HARNESS_TEMPLATE_KEEP_DOCS_STANDARDS: frozenset[str] = frozenset(
    {
        "context-management.md",
        "harness-template.md",
        "wiki-harness-template.md",
    }
)
WIKI_TEMPLATE_KEEP_DOCS_STANDARDS = HARNESS_TEMPLATE_KEEP_DOCS_STANDARDS

HARNESS_TEMPLATE_EMPTY_AREAS: frozenset[str] = frozenset(
    {
        "actionable",
        "scratch",
        "projects",
        "research",
        "change-history",
        "results",
    }
)
WIKI_TEMPLATE_EMPTY_AREAS = HARNESS_TEMPLATE_EMPTY_AREAS

GENERIC_TEMPLATE_STUB_AGENTS = """# Generic harness template

This area is a placeholder in the generic (non-domain-fed) harness clone.

Feed your own domain content here later. Do not ship this instance's security
corpus, cloud-provider skills, or project/research dumps in the template.
"""

GENERIC_TEMPLATE_PROJECT_PROMPTS_README = """# Project Prompts

Library of lean, situational prompt templates for human-initiated follow-up agent sessions.

## Purpose & Constraints

- **When to use:** When human operators need a ready-to-use prompt to launch a follow-up agent on an initiative (e.g. executing live cloud/OAuth tests, running newly built generic tooling against live environments, or completing interactive phases).
- **Non-authoritative:** This folder is strictly advisory and non-normative. It is not an authoritative reference for repository standards or instructions.
- **Lean:** Prompts contain only task-specific parameters and objective prompts without duplicating harness structure, rules, or guidance that agents discover on their own.
- **No autonomous consumption:** Agents must not read or execute files in this directory unless explicitly instructed by the user.

## Prompts Index

| Prompt | Focus Area | Intended Agent |
|---|---|---|
| _(Feed situational follow-up prompts here)_ | | |
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

Tooling and validation families only. Domain reference families are fed later when this
template is cloned for a topic.

| Folder | Topic |
| --- | --- |
| `conventional-commits/` | Commit / PR conventions |
| `markdown/` | markdownlint library + cli2 (rules, config, invoke) |
| `prompt-engineering/` | Prompt engineering principles, cache optimization, and structured framing |
| `valid-sources/` | Authoritative primary sources allowlist |
"""

GENERIC_TEMPLATE_README = r"""# Koality-Assured AI Harness Core

Decoupled AI agent harness engine and generic template for multi-agent routing, 5-tier context hierarchies, multi-vendor prompt caching, precision cost layers, and sandboxed worktree execution.

## Mission Statement

Provide a clean, embeddable, framework-agnostic harness template and execution engine that brings production-grade multi-agent orchestration, worktree isolation, multi-vendor prompt caching, dual-retrieval (BM25 + ast-grep), and token-saving cost layers to any software repository or domain router.

---

## Operating Modes: How It Can Be Used

The harness core is designed to support two primary operating models:

### Mode A: Generic Domain Router Template (Clone & Feed)
Clone this repository as a clean base to create a specialized domain harness (e.g., security router, infrastructure router, legal compliance router) without inheriting another instance's domain corpus:
1. **Clone the template**: Start from `ai-harness-core`.
2. **Feed domain standards**: Place authoritative policies and requirements in `docs/standards/`.
3. **Feed domain references**: Add machine-readable catalogs and industry frameworks in `references/<framework-family>/`.
4. **Feed domain skills & agents**: Add Schema V2 skills in `ai-tooling/skills/<family>/<name>/SKILL.md` and specialists in `ai-tooling/agents/<agent-id>/AGENT.md`.
5. **Regenerate routing indexes**:
   ```bash
   python scripts/routing/generate_routing_index.py
   python scripts/qmd/refresh_qmd_index.py
   ```

### Mode B: Embeddable Engine Scaffolding (`.harness/` & CLI)
Embed the core engine directly into an existing software project to give AI coding agents isolation, caching, and retrieval capabilities:
1. Scaffold configuration and skeleton directories via CLI:
   ```bash
   python scripts/harness_init.py --target /path/to/target-repo
   ```
2. Configure provider thresholds and adapter paths in `config/harness.config.json`.
3. Leverage `.harness/` Python adapters for worktree sandboxing, prompt cache breakpoint planning, and Headroom compression.

---

## Architecture Overview

The public export is a complete, decoupled repository taxonomy (same top-level areas as the private router), not a flattened Python package:

```text
ai-harness-core/
├── AGENTS.md                 # Root normative contract, directive ranking, and cost rules
├── routing/                  # Area map, 3-tier hybrid dispatch, and skill catalog
│   ├── areas.yaml            # Canonical 12-area repository taxonomy configuration
│   ├── AGENTS.md             # Routing hops and context-loading protocols
│   └── skill-dispatch.md     # Generated skill catalog with agent ownership and contracts
├── ai-tooling/               # Filtered generic skills, agents, A2A, and memory scaffolds
│   ├── skills/               # Schema V2 skills (meta/, git/, reporting/, cost-layers/)
│   ├── agents/               # Canonical specialist agent definitions (AGENT.md)
│   ├── a2a/                  # Agent-to-Agent protocol and structured communication cards
│   └── memory/               # Checkpoint partitions (user/, agent/, model/)
├── .harness/                 # Embeddable core engine (kept as .harness/, not harness/)
│   ├── config.py             # Config manifest loader and schema validator
│   ├── isolation/worktree.py # Concurrency-safe Git worktree sandbox manager
│   ├── a2a/protocol.py       # Sandboxed A2A protocol (8-exchange budget & envelope validation)
│   ├── cache/manager.py      # Multi-vendor prompt caching (Anthropic, OpenAI, Gemini)
│   ├── adapters/             # Tool adapters (qmd, ast_grep, headroom)
│   └── cli/harness_init.py   # Bootstrap scaffolding CLI for new repositories
├── scripts/                  # Automation, routing, cost-layers, change-history, and sync
│   ├── _lib/                 # Shared non-indexed helper modules
│   ├── routing/              # Hybrid dispatch, DAG resolver, worktree spawn scripts
│   ├── cost-layers/          # Precision retrieval, prompt cache audit, and benchmark runners
│   └── ai-tooling/           # Fast frontmatter and agent schema validators
├── supporting/               # Universal runtime tool patterns (qmd, ast-grep, headroom, github)
├── docs/                     # Session security MUSTs, anti-slop, and portable harness standards
│   ├── agent-session-security.md
│   ├── anti-slop.md
│   └── standards/            # context-management.md, harness-template.md
├── references/               # Universal tooling families (conventional-commits, markdown, prompt-engineering, valid-sources)
└── actionable/ projects/ research/ results/ scratch/ change-history/ # Managed lifecycle zones
```

---

## Key Elements & Architectural Layers

The harness architecture integrates four core operational layers:

### 1. Context Hierarchy & Multi-Vendor Prompt Caching
* **Normative Standard**: `docs/standards/context-management.md`
* **5-Tier Context Hierarchy**:
  1. `Tier 1: Static Base Prefix` -- Universal MUST rules, system guardrails, immutable tool schemas (Breakpoint 1).
  2. `Tier 2: Static Skill Context` -- Specialist definition (`AGENT.md`) and active `SKILL.md`.
  3. `Tier 3: Monotonic Conversation History` -- Append-only turns 1 to N-1 (Breakpoint 2).
  4. `Tier 4: Ephemeral Turn Context` -- Nearest folder `AGENTS.md` injected dynamically at the turn tail.
  5. `Tier 5: Dynamic Turn Delta` -- Current user prompt and compressed tool execution results.
* **Prefix Invariance**: Guarantees exact byte matching from token 0. Placing JIT area rules in Tier 4 ensures mid-session directory switches never invalidate historical conversation caches (maintaining 92-98% cache hit rates).
* **Multi-Provider Caching**:
  * **Anthropic**: 2-breakpoint allocation (system/tools + penultimate turn; max 4 blocks, 5-min rolling TTL).
  * **OpenAI**: Automatic prefix caching with 128-token boundary alignment (>= 1,024 tokens).
  * **Gemini**: Explicit Context Caching API descriptors for large static corpuses (>= 32k tokens).

### 2. Precision Cost Layers & Context Compression
* **ast-grep (Outline-First Precision Retrieval)**:
  * Symbol discovery via `ast-grep outline` and line-bounded reads (`StartLine`/`EndLine`).
  * Yields **83%-94% token savings** compared to full-file dumps.
  * Mechanical AST batch refactoring via `ast-grep --rewrite`.
* **qmd (BM25 Lexical & Hybrid Search)**:
  * Fast, indexed on-demand snippet search (`qmd search` -> `qmd get`), avoiding costly repo-wide tree walks.
* **Headroom (Context Compression Proxy)**:
  * Local proxy (`http://127.0.0.1:8787`) compressing verbose tool outputs (JSON arrays ~70%+, compiler logs ~30%+) while preserving 100% of structural facts.
  * Automatic fallback to `scripts/_lib/tool_output.py` when the proxy is offline.
* **Web Distillation**:
  * `local_webfetch.py` strips HTML boilerplate and neutralizes hidden prompt injection vectors prior to ingestion.

### 3. Routing, DAG Resolution & Hybrid Dispatch
* **3-Tier Hybrid Dispatch** (`scripts/routing/hybrid_dispatch.py`):
  * *Tier 1*: Fast-path regex / keyword routing (<1ms, 0 tokens).
  * *Tier 2*: In-memory BM25 lexical ranking (~5ms, 0 tokens) over skill and area metadata.
  * *Tier 3*: Structured LLM Ambiguity Gate for multi-intent triage.
* **Skill Dependency DAGs** (`scripts/routing/resolve_skill_graph.py`):
  * Resolves execution order using Kahn's topological sort.
  * Models `required_skills`, `delegated_skills`, and `in_session_skills`.
  * Enforces failure lifecycle policies: `abort_and_rollback`, `fallback_degrade`, `continue_with_partial`.

### 4. Sandboxed Worktree Isolation & Clean-Slate Delegation
* **Git Worktree Isolation** (`scripts/routing/spawn_worktree.py`):
  * Mutating tasks run in isolated worktrees (`scratch/worktrees/<slug>`) on dedicated feature branches, preventing dirty-state contamination.
* **Parent Discovery Bound**:
  * The orchestrator stops context reading once the skill owner agent is identified; specialists spawn with a clean context slate.
* **Structured Result Envelope**:
  * Specialists return standard envelopes containing `task_id`, `status`, `artifacts`, `handoff_requests`, and `metrics`.
  * `handoff_requests` are strictly advisory metadata (preventing autonomous recursive subagent minting).

---

## Empirical Cost Optimization & Benchmark Results

The harness cost layers are validated continuously via automated benchmarks (`python scripts/cost-layers/validate_cost_layers.py`). Measured results from the benchmark suite:

| Cost Layer / Subsystem | Benchmark Payload / Target | Measured Token Reduction | Fact Retention / Accuracy | Economic & Operational Benefit |
| :--- | :--- | :--- | :--- | :--- |
| **`ast-grep` Outline** | Python script inspection (`.py`) | **93.7% reduction** (2,571 tokens saved) | 100% structural symbols | Eliminates full file body dumps |
| **`ast-grep` Kind Match** | Skill frontmatter (`SKILL.md`) | **94.9% reduction** (632 tokens saved) | 100% frontmatter keys | Instant YAML AST parsing via stdin |
| **`ast-grep` Kind Match** | Agent cards (`a2a/*.json`) | **90.5% reduction** (542 tokens saved) | 100% agent card attributes | Surgical schema & metadata reads |
| **`Headroom` Compression** | JSON tool output arrays | **72.2% reduction** (5,901 tokens saved) | 100% match text facts | Intercepts verbose tool responses |
| **`Headroom` Logs & Grep** | Grep hits & compile logs | **5.9% - 30.8% reduction** | 100% error signatures | Compresses repetitive log output |
| **`local_webfetch`** | External web HTML distillation | **77.2% reduction** (448 tokens saved) | **100.0%** (4/4 gold facts) | Strips HTML bloat & neutralizes prompt injections |
| **Prompt Cache Manager** | 25 audited prompt definitions | **0 invariance violations** | 100% byte stability | **~90% input cost discount** (Anthropic/OpenAI KV caches) |
| **`qmd` BM25 Search** | Repository Markdown corpus | **0.67s average search** | High top-1 precision | Eliminates recursive directory tree walks |

### Cost Layer Verification Commands

```bash
# Run full combined cost-layer validation suite (ast-grep + headroom + prompt-caching + webfetch + qmd)
python scripts/cost-layers/validate_cost_layers.py

# Run standalone prompt cache byte invariance linter
python scripts/cost-layers/validate_prompt_caching.py

# Run standalone web retrieval distillation benchmark
python scripts/research/local_webfetch.py --dry-run

# Run standalone Headroom tool output compression benchmark
python scripts/cost-layers/validate_headroom_compression.py

# Run standalone ast-grep precision retrieval benchmark
python scripts/cost-layers/validate_ast_grep.py
```

---

## Frontmatter & Component Conventions

All components adhere to strict machine-readable frontmatter verified by automated validators:

| Component | Standard | Mandatory Fields & Rules | Validation Script |
| :--- | :--- | :--- | :--- |
| **Skills** | **Schema V2** (`ai-tooling/skills/**/SKILL.md`) | `schema_version: "2.0.0"`, `name`, `description` ("Use when..."), `owner_agent`, `rank`, `isolation`, `on_failure`, `prerequisites`, `dependencies`, `contracts` (`inputs`, `outputs`). 9 required sections & mandatory cost-layer inheritance. | `python scripts/ai-tooling/validate_skill.py --all` |
| **Agents** | **Agent Frontmatter** (`ai-tooling/agents/**/AGENT.md`) | `id`, `name`, `model_tier`, `role`, `isolation`, `capabilities`, `allowed_tools`, `constraints`. | `python scripts/ai-tooling/validate_agent.py --all` |
| **Standards & Docs** | **Corpus Frontmatter** (`docs/**`, `supporting/**`) | `doc_kind`, `canonical_id`, `purpose`, `rank`, `topics`, `rag_keywords`. Retrievable `##` headings with topic/intent in opening sentence. | `python scripts/docs/validate_structure_fast.py` |
| **Taxonomy** | **8-Point AGENTS Schema** | 12 top-level areas: Content ownership, Placement, Lifecycle, Relationships, SoT boundaries, Validation, Escalation, Local exceptions. | `python scripts/routing/generate_routing_index.py` |

---

## Verification & Testing Suite

Run the full validation suite to verify syntax, cost layers, skill DAGs, and prompt cache invariance:

```bash
# 1. Compile all Python scripts and .harness engine
python -m compileall -q scripts .harness

# 2. Validate skill schemas and dependency DAGs
python scripts/ai-tooling/validate_skill.py --all
python scripts/routing/resolve_skill_graph.py --validate-all

# 3. Run cost-layer benchmarks and prompt cache verification
python scripts/cost-layers/validate_cost_layers.py

# 4. Execute unit test suite
python -m unittest discover -s scripts/tests -v
```

---

## Security Notice

Public export and template instances run automated redaction audits. Never commit credentials, API keys, private tokens, or real PII. Redacted examples must be obviously fake. Full session security rules live in `docs/agent-session-security.md`.

## License

MIT License Copyright (c) 2026 Koality-Assured.
"""

GENERIC_TEMPLATE_CI = """name: Harness template CI

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
    """Return True if a skill directory should be copied into the harness template."""
    if skill_name.startswith(HARNESS_TEMPLATE_DROP_SKILL_PREFIXES):
        return False
    if skill_name in HARNESS_TEMPLATE_DROP_SKILLS:
        return False
    return skill_name in HARNESS_TEMPLATE_KEEP_SKILLS


def agent_is_kept(agent_name: str) -> bool:
    """Return True if an agent directory should be copied into the harness template."""
    if agent_name in HARNESS_TEMPLATE_DROP_AGENTS:
        return False
    if agent_name in {"AGENTS.md", "model-tiers.md", "README.md"}:
        return True
    return True


def is_harness_template_rel_kept(rel: str) -> bool:
    """Return True if a source-root-relative file belongs in ai-harness-core."""
    parts = _posix_parts(rel)
    if not parts:
        return False
    if "/".join(parts) in HARNESS_TEMPLATE_DEST_EXCLUDE_RELS:
        return False
    top = parts[0]
    if top == ".git":
        return False
    if top == ".claude":
        return parts == [".claude", "settings.json"]
    if top == ".cursor":
        return parts == [".cursor", "rules", "context-boundaries.mdc"]
    if top == ".github":
        return "/".join(parts) in {
            ".github/copilot-instructions.md",
            ".github/instructions/subagents.instructions.md",
        }
    if len(parts) == 1 and top in HARNESS_TEMPLATE_ROOT_FILES:
        return True
    if top in {"routing", "config", ".harness"}:
        if top == "routing" and len(parts) == 2 and parts[1] in {
            "skill-dispatch.md",
            "area-map.md",
            "agent-dispatch.md",
            "by-task.md",
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
    if top in HARNESS_TEMPLATE_EMPTY_AREAS:
        return _keep_empty_area(parts)
    return False


is_wiki_template_rel_kept = is_harness_template_rel_kept  # Backward compatibility alias


def harness_template_dir_may_contain_kept(rel_dir: str) -> bool:
    """Return True if os.walk should descend into this source-root-relative dir."""
    parts = _posix_parts(rel_dir)
    if not parts:
        return True
    top = parts[0]
    if top == ".git":
        return False
    if top == ".claude":
        return len(parts) == 1
    if top == ".cursor":
        return parts == [".cursor"] or parts == [".cursor", "rules"]
    if top == ".github":
        return parts == [".github"] or parts == [".github", "instructions"]
    if top in HARNESS_TEMPLATE_ROOT_FILES:
        return False
    if top in {"routing", "config", ".harness"}:
        return True
    if top == "scripts":
        if len(parts) == 1:
            return True
        return parts[1] in HARNESS_TEMPLATE_KEEP_SCRIPT_DIRS
    if top == "supporting":
        if len(parts) == 1:
            return True
        return parts[1] in HARNESS_TEMPLATE_KEEP_SUPPORTING_DIRS
    if top == "docs":
        if len(parts) == 1:
            return True
        return parts[1] == "standards" and len(parts) == 2
    if top == "references":
        if len(parts) == 1:
            return True
        return parts[1] in HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES
    if top == "ai-tooling":
        return _ai_tooling_dir_may_contain_kept(parts)
    if top in HARNESS_TEMPLATE_EMPTY_AREAS:
        if len(parts) == 1:
            return True
        if top == "projects" and parts[1] in {"notes", "project-prompts"} and len(parts) <= 2:
            return True
        return False
    return False


wiki_template_dir_may_contain_kept = harness_template_dir_may_contain_kept  # Backward compatibility alias


def harness_template_stub_files() -> dict[str, str]:
    """Dest-relative files written after copy when the source has no equivalent."""
    return {
        "docs/standards/AGENTS.md": GENERIC_TEMPLATE_STUB_AGENTS,
        "references/AGENTS.md": GENERIC_TEMPLATE_REFERENCES_AGENTS,
        "projects/project-prompts/README.md": GENERIC_TEMPLATE_PROJECT_PROMPTS_README,
    }


wiki_template_stub_files = harness_template_stub_files  # Backward compatibility alias


def harness_template_post_copy_files(dest_root: Path, source_root: Path | None = None) -> dict[str, str]:
    """Dest-relative files generated after the filtered copy (stubs + dest indexes)."""
    files = dict(harness_template_stub_files())
    files["routing/skill-dispatch.md"] = render_dest_skill_dispatch(dest_root)
    files["routing/area-map.md"] = render_dest_area_map(dest_root)
    files["routing/agent-dispatch.md"] = render_dest_agent_dispatch(dest_root)
    files["routing/by-task.md"] = render_dest_by_task(dest_root, source_root)
    files["scripts/script-index.md"] = render_dest_script_index(dest_root)
    files["README.md"] = GENERIC_TEMPLATE_README
    files[".github/workflows/ci.yml"] = GENERIC_TEMPLATE_CI
    return files


wiki_template_post_copy_files = harness_template_post_copy_files  # Backward compatibility alias


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
        return (
            "---\\n"
            "doc_kind: routing_map\\n"
            "canonical_id: area-map\\n"
            "topics: [routing, write-back, structure]\\n"
            "generated_at_utc: export\\n"
            "generator: scripts/sync/_harness_template.py (dest routing/areas.yaml)\\n"
            "---\\n\\n"
            "# Area map\\n\\n"
            "Generated from dest [`areas.yaml`](./areas.yaml) after harness-template export. "
            "Do not hand-edit — run `python scripts/routing/generate_routing_index.py` "
            "from the dest checkout.\\n\\n"
            "Match [`skill-dispatch.md`](./skill-dispatch.md) first. Use this table only when no skill row applies.\\n\\n"
            "## Areas\\n\\n"
            "| Area | Purpose | Default agent | Load | Write-back |\\n"
            "| --- | --- | --- | --- | --- |\\n"
        )


def render_dest_script_index(dest_root: Path) -> str:
    """Build script-index.md from dest scripts/ (kept trees only)."""
    text = render_script_index(dest_root / "scripts", now="export")
    return text.replace(
        "Generated from Python docstring `tags:` / `routing_hints:`. Do not hand-edit — run `python scripts/routing/generate_script_index.py`.",
        "Generated from dest `scripts/` after harness-template export (kept trees only). "
        "Do not hand-edit — run `python scripts/routing/generate_script_index.py` "
        "from the dest checkout after feeding scripts.",
    )


def render_dest_by_task(dest_root: Path, source_root: Path | None = None) -> str:
    """Build sanitized by-task.md containing only kept agents and skills."""
    src_by_task = (source_root / "routing" / "by-task.md") if source_root else (dest_root / "routing" / "by-task.md")
    if not src_by_task.exists():
        src_by_task = Path(__file__).resolve().parents[2] / "routing" / "by-task.md"
    if not src_by_task.exists():
        return ""

    content = src_by_task.read_text(encoding="utf-8")
    lines = content.splitlines()
    out_lines: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Task / Intent |"):
            in_table = True
            out_lines.append(line)
            continue
        if in_table and stripped.startswith("| ---"):
            out_lines.append(line)
            continue
        if in_table and stripped.startswith("|"):
            cols = [c.strip() for c in stripped.split("|")[1:-1]]
            if len(cols) >= 4:
                agent_col = cols[2]
                skill_col = cols[3]
                has_dropped_agent = any(f"`{da}`" in agent_col for da in HARNESS_TEMPLATE_DROP_AGENTS)
                has_dropped_skill = any(
                    f"`{ds}`" in skill_col for ds in HARNESS_TEMPLATE_DROP_SKILLS
                ) or any(
                    f"`{p}" in skill_col for p in HARNESS_TEMPLATE_DROP_SKILL_PREFIXES
                )
                if has_dropped_agent or has_dropped_skill:
                    continue
                if any(k in skill_col for k in ("benchlm-lookup", "ai-vendor-updates", "cloud-admin-provision", "google-workspace-admin", "slack-message", "confluence-doc-manage", "confluence-admin", "confluence-app-manage")):
                    skill_name_match = [s for s in ("benchlm-lookup", "ai-vendor-updates", "cloud-admin-provision", "google-workspace-admin", "slack-message", "confluence-doc-manage", "confluence-admin", "confluence-app-manage") if s in skill_col]
                    if skill_name_match and not any((dest_root / "ai-tooling" / "skills").rglob(f"{skill_name_match[0]}/SKILL.md")):
                        continue
            out_lines.append(line)
            continue
        if in_table and not stripped.startswith("|"):
            in_table = False
        out_lines.append(line)

    return "\n".join(out_lines) + ("\n" if content.endswith("\n") else "")


def harness_template_prune_dest_leftovers(dest_root: Path) -> list[str]:
    """Remove dest-root engine leftovers and obsolete files not in template.

    Never deletes `.harness/` or `.git/`. Returns pruned relative names.
    """
    pruned: list[str] = []
    for name in sorted(HARNESS_TEMPLATE_PRUNE_DEST_NAMES):
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
    for rel in sorted(HARNESS_TEMPLATE_DEST_EXCLUDE_RELS):
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
            if agent_dir.is_dir() and (agent_dir.name in HARNESS_TEMPLATE_DROP_AGENTS or not agent_is_kept(agent_dir.name)):
                shutil.rmtree(agent_dir)
                pruned.append(f"ai-tooling/agents/{agent_dir.name}")

    # Prune dropped and legacy skills
    skills_root = dest_root / "ai-tooling" / "skills"
    if skills_root.is_dir():
        for child in sorted(skills_root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name not in SKILL_FAMILIES:
                shutil.rmtree(child)
                pruned.append(f"ai-tooling/skills/{child.name}")
            else:
                if (child / "SKILL.md").exists():
                    if not skill_is_kept(child.name):
                        shutil.rmtree(child)
                        pruned.append(f"ai-tooling/skills/{child.name}")
                else:
                    for skill_dir in sorted(child.iterdir()):
                        if skill_dir.is_dir() and not skill_is_kept(skill_dir.name):
                            shutil.rmtree(skill_dir)
                            pruned.append(f"ai-tooling/skills/{child.name}/{skill_dir.name}")
                    remaining = [f for f in child.iterdir() if f.name not in {".gitkeep", ".DS_Store"}]
                    if not remaining:
                        shutil.rmtree(child)
                        pruned.append(f"ai-tooling/skills/{child.name}")

    # Prune dropped reference families
    refs_root = dest_root / "references"
    if refs_root.is_dir():
        for ref_dir in sorted(refs_root.iterdir()):
            if ref_dir.is_dir() and (ref_dir.name in HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES or ref_dir.name not in HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES):
                shutil.rmtree(ref_dir)
                pruned.append(f"references/{ref_dir.name}")

    return pruned


wiki_template_prune_dest_leftovers = harness_template_prune_dest_leftovers  # Backward compatibility alias


def harness_template_sanitize_file_content(rel: str, raw_text: str) -> str:
    """Sanitize file contents for harness template export (e.g. drop unkept delegation targets)."""
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
                    if target_agent in HARNESS_TEMPLATE_DROP_AGENTS or not agent_is_kept(target_agent):
                        continue
                elif stripped and not stripped.startswith("#"):
                    in_delegation_targets = False
            out.append(line)
        return "\n".join(out) + ("\n" if raw_text.endswith("\n") else "")
    if len(parts) >= 3 and parts[0] == "ai-tooling" and parts[1] == "agents" and parts[-1] == "README.md":
        lines = raw_text.splitlines()
        out = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and any(f"`{da}/`" in stripped or f"/{da}/" in stripped for da in HARNESS_TEMPLATE_DROP_AGENTS):
                continue
            out.append(line)
        return "\n".join(out) + ("\n" if raw_text.endswith("\n") else "")
    return raw_text


wiki_template_sanitize_file_content = harness_template_sanitize_file_content  # Backward compatibility alias


def render_dest_skill_dispatch(dest_root: Path) -> str:
    """Build skill-dispatch.md from dest skill frontmatter (kept skills only)."""
    rows: list[dict[str, Any]] = []
    skills_root = dest_root / "ai-tooling" / "skills"
    if skills_root.is_dir():
        for path in skill_paths(dest_root):
            rows.append(load_skill_record(path))
    seen: set[str] = set()
    deduped_rows: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("name", ""))
        if name and name not in seen:
            seen.add(name)
            deduped_rows.append(r)
    rows = deduped_rows
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
        "generator: scripts/sync/_harness_template.py (dest skill frontmatter)",
        "---",
        "",
        "# Skill dispatch",
        "",
        "Generated from dest `ai-tooling/skills/*/SKILL.md` frontmatter after harness-template export. "
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

    # Composite skill prerequisites and failure policies section
    composite_rows = []
    for row in rows:
        deps = row.get("dependencies", {})
        req_list = deps.get("required_skills", [])
        del_list = deps.get("delegated_skills", [])
        ins_list = deps.get("in_session_skills", [])
        prereqs_list = row.get("prerequisites", [])
        fail_policy = row.get("on_failure")
        if req_list or del_list or ins_list or prereqs_list or (fail_policy and fail_policy != "abort_and_rollback"):
            composite_rows.append((row, req_list, del_list, ins_list, prereqs_list, fail_policy or "abort_and_rollback"))

    if composite_rows:
        lines.extend(
            [
                "",
                "## Composite skill prerequisites and failure policies",
                "",
                "| Skill | Required skills | Delegated skills | In-session skills | Binary prerequisites | Failure policy |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row, req_list, del_list, ins_list, prereqs_list, fail_str in composite_rows:
            link_target = skill_link_map.get(row["name"], f"../ai-tooling/skills/{row['name']}/SKILL.md")
            skill_link = f"[`{row['name']}`]({link_target})"
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

            lines.append(
                f"| {skill_link} | {req_str} | {del_str} | {ins_str} | {prereqs_str} | `{fail_str}` |"
            )

    lines.append("")
    return "\n".join(lines)


def _keep_scripts(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] == "AGENTS.md":
        return True
    if len(parts) == 2 and parts[1] == "script-index.md":
        return False
    if len(parts) >= 2 and parts[1] in HARNESS_TEMPLATE_KEEP_SCRIPT_DIRS:
        return True
    return False


def _keep_supporting(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] in {"AGENTS.md", "workstation-onboarding.md"}:
        return True
    if len(parts) >= 2 and parts[1] in HARNESS_TEMPLATE_KEEP_SUPPORTING_DIRS:
        return True
    return False


def _keep_docs(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] in HARNESS_TEMPLATE_KEEP_DOCS_FILES:
        return True
    if len(parts) == 3 and parts[1] == "standards" and parts[2] in HARNESS_TEMPLATE_KEEP_DOCS_STANDARDS:
        return True
    return False


def _keep_references(parts: list[str]) -> bool:
    if len(parts) == 2 and parts[1] == "AGENTS.md":
        return False
    if len(parts) == 2 and parts[1] == "reference-maintenance.md":
        return True
    if len(parts) >= 2 and parts[1] in HARNESS_TEMPLATE_KEEP_REFERENCE_FAMILIES:
        return True
    if len(parts) >= 2 and parts[1] in HARNESS_TEMPLATE_DROP_REFERENCE_FAMILIES:
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
            if p in HARNESS_TEMPLATE_DROP_SKILLS or p.startswith(HARNESS_TEMPLATE_DROP_SKILL_PREFIXES):
                return False
        return any(skill_is_kept(p) for p in parts[2:]) or len(parts) == 3
    if len(parts) >= 2 and parts[1] == "memory":
        if parts[-1] in {"AGENTS.md", ".gitkeep"}:
            if len(parts) >= 5 and parts[2] in {"user", "agent", "model"}:
                return False
            return True
        return False
    return False


def _keep_empty_area(parts: list[str]) -> bool:
    if parts[-1] == "AGENTS.md":
        return True
    if parts[-1] == ".gitkeep":
        return True
    if len(parts) == 2 and parts[0] == "results" and parts[1] == "results-conventions.md":
        return True
    if len(parts) == 3 and parts[0] == "projects" and parts[1] == "notes" and parts[2] == "README.md":
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
            if p in HARNESS_TEMPLATE_DROP_SKILLS or p.startswith(HARNESS_TEMPLATE_DROP_SKILL_PREFIXES):
                return False
        return True
    if parts[1] == "memory":
        if len(parts) >= 4 and parts[2] in {"user", "agent", "model"}:
            return False
        return True
    return False
