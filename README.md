# Koality-Assured AI Harness Core

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
├── references/               # Universal tooling families (conventional-commits, markdown, valid-sources)
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
