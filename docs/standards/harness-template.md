---
doc_kind: requirement
canonical_id: harness-template
purpose: [decision, requirement]
rank: high
topics: [wiki, harness, agents]
rag_keywords:
  [
    ai-harness-core,
    fed-instance,
    generic-template,
    router-structure,
    downstream-sync,
  ]
---

# Harness template versus fed instance

## Purpose

This page records how this harness instance relates to the public generic template `ai-harness-core`. Structure here is the source; domain corpus stays in fed instances.

## Fed instance versus generic template

`ai-router` is a fed instance of the AI harness. It carries a security and tech corpus under `references/`, many pages under `docs/standards/`, and cloud-provider skills.

`ai-harness-core` is the generic harness template. It uses the same folder layout and operating machinery, with domain areas empty or stubbed so another domain router can start from it.

Start a new domain router from the template, then add that domain's corpus. The template must not receive this instance's framework dumps, organization security-ops pages, or cloud-vendor skills.

## What the template keeps

Machinery belongs in `ai-harness-core`. Copy it, then sync later corrections from this harness:

- Root and nested `AGENTS.md`
- `routing/` (areas, skill-dispatch, isolation)
- Cost layers: qmd, ast-grep, Headroom
- Generic skills, agents, scripts, and `supporting/` notes that are not a vendor or domain corpus
- Harness operating pages such as this one and [`context-management.md`](./context-management.md)

## What the template must not copy

Fed domain content stays in this instance, or in public slice repos that publish a selected corpus. Leave it out of `ai-harness-core`:

- Framework dumps under `references/` (NIST, OWASP, CWE, ATT&CK, and similar)
- Organization security-ops standards under `docs/standards/` (identity, endpoint, cloud tenancy, and the other control pages in that folder), except the harness operating pages listed above
- Cloud-vendor skills (AWS, Azure, GCP)
- Instance `projects/`, `research/`, and `ai-tooling/memory/`

The template may keep empty or stub folders so the layout is recognizable, without the filled domain pages from this instance.

## Sync source

Structure corrections in this harness are the source that gets synced into `ai-harness-core` via `scripts/sync`. Domain pages remain in this instance and in other public slice repos; they do not go into the template.

This page states the boundary. The file map and redaction pipeline live with the repo-sync specialist.

## Repository taxonomy & subfolder archetypes

The harness architecture divides the repository into 12 canonical top-level areas. Each area defines strict layout rules, allowed subfolder archetypes, and criteria for when to create subfolders versus keeping files flat or promoting to other areas:

| Area | Purpose & Role | Permitted Subfolder Types | When to Create Subfolders | Generic Template (`ai-harness-core`) vs Fed Instance |
| :--- | :--- | :--- | :--- | :--- |
| **`projects/`** | Initiative specs, informal notes, and follow-up prompts | `projects/<slug>/`, `notes/`, `project-prompts/` | Create `<slug>/` for multi-step initiatives; create files in `notes/` on human request; create `.md` templates in `project-prompts/`. | Template keeps `AGENTS.md` and `README.md` for `notes/` and `project-prompts/`; instance slug folders are omitted. |
| **`ai-tooling/`** | Skills, specialist agents, A2A protocol, and memory scaffolds | `skills/<family>/<skill>/`, `agents/<agent>/`, `a2a/agent-cards/`, `memory/{user,agent,model}/` | Create skill folders under family subfolders; create agent folders for standalone specialists; split memory checkpoints. | Template keeps generic skills, agents, A2A machinery, and memory folder scaffold. Domain/cloud skills and instance memory dumps omitted. |
| **`docs/`** | Protected normative corpus of record, security MUST, and playbooks | `standards/`, `guidance/` | Only `standards/` and `guidance/` are permitted subfolders; root `docs/` is reserved for universal security MUST and anti-slop rules. | Template keeps universal security MUST, anti-slop, and portable harness standards (`context-management.md`, `harness-template.md`). Org security controls omitted. |
| **`references/`** | External framework captures and machine-readable catalogs (advisory only) | `<framework-family>/` | Exactly one subfolder per external framework family (e.g. `conventional-commits/`, `markdown/`, `owasp/`, `nist-csf/`). | Template keeps universal tooling families (`conventional-commits/`, `markdown/`, `prompt-engineering/`, `valid-sources/`). Domain frameworks (OWASP, NIST, CWE, MITRE) stay in fed instances. |
| **`supporting/`** | Workstation onboarding, tool patterns, CLI guides, and conventions | `<tool-or-capability>/` (e.g. `qmd/`, `ast-grep/`, `headroom/`, `github/`, `powershell/`, `mermaid/`) | Create a new tool subfolder when onboarding a core tool, CLI capability, or environment pattern. | Template keeps universal agent tooling patterns. Specific workplace/cloud platform integrations are fed per harness instance based on what it interacts with. |
| **`scripts/`** | Tagged Python automation and validation utilities | `<purpose>/` (e.g. `_lib/`, `routing/`, `qmd/`, `cost-layers/`, `change-history/`, `sync/`, `repos/`, `tests/`, `docs/`, `github/`, `ai-tooling/`) | Group scripts by functional purpose; shared non-indexed helper modules sit in `_lib/`. | Template keeps core harness management scripts and tests. Domain/cloud provider scripts omitted. |
| **`results/`** | Immutable deliverables, audit reports, generated diagrams, benchmarks | `<category>/<run-or-topic>/<YYYY-MM-DD>/` | Organize non-ephemeral deliverables by artifact category and date. | Template keeps empty area with `AGENTS.md` and `results-conventions.md`. Run artifacts omitted. |
| **`research/`** | Topic deep-dives, multi-turn investigations, and technology spikes | `<topic>/` | Create a subfolder when launching an in-depth topic investigation. | Template keeps empty area with `AGENTS.md` and `README.md`. Instance research dossiers omitted. |
| **`scratch/`** | Ephemeral scratchpad and isolated git worktrees | `worktrees/<slug>/` | Created automatically by `spawn_worktree.py` for isolated worktrees; never durable SoT. | Template keeps empty area with `AGENTS.md` and `README.md`. Worktrees omitted. |
| **`change-history/`** | Structured provenance log across quarters | `<YYYY>/Q<1-4>/` | Managed automatically via `append_change_history.py` (year and quarter subfolders). | Template keeps empty area with `AGENTS.md` and `README.md`. History entries omitted. |
| **`actionable/`** | Temporary human intake drop zone | _(Flat structure)_ | Avoid creating subfolders; drop items as flat files, claim them, execute, and promote to durable home. | Template keeps empty area with `AGENTS.md` and `README.md`. Intake items cleared. |
| **`routing/`** | Generated next-step indexes after root `AGENTS.md` | _(Flat structure)_ | Flat structure containing `areas.yaml`, `AGENTS.md`, and generated dispatch maps. | Template keeps full routing machinery, re-rendered for destination contents upon export. |

---

## Detailed subfolder rules & decision criteria

### 1. `projects/` (Initiatives, Notes, and Prompts)
`projects/` manages work across three distinct subfolder archetypes:
- **`projects/<slug>/README.md` (Initiative Specs)**: Flat slug folders for formal multi-step initiatives. Must contain YAML frontmatter (`status: proposed | active | ongoing | completed`, `owner: router`, `repos: [...]`) and 10 standard sections (`Intent`, `Current state`, `Completed work`, `Plan / next actions`, `Exit criteria`, `Risks & mitigations`, `Related repos & paths`, `Research & results pointers`, `Decisions`, `Open questions`). Do not nest slug folders within slug folders.
- **`projects/notes/` (Human Non-Spec Notes)**: Informal drop area for unstructured notes, thoughts, and follow-up items that have **not** yet been established as a formal project or had any real planning done beyond a vague note. Created **only on explicit human request** (one kebab-case Markdown file per concern, e.g. `YYYY-MM-DD-topic.md`). When real scoping or planning begins, promote the note into a formal `projects/<slug>/` initiative.
- **`projects/project-prompts/` (Situational Prompt Templates)**: Lean, situational prompt templates for human-initiated follow-up agent sessions (e.g. live OAuth token configuration, executing unverified generic tools against test environments, or interactive human-in-the-loop phases). Non-authoritative, non-normative, and never consumed autonomously by agents.

### 2. `supporting/` (Tool Patterns & Capabilities)
`supporting/` provides operational tool patterns and workstation onboarding guides:
- **Universal Tooling vs Instance-Specific Integrations**: The generic harness template carries universal agent tooling patterns (`qmd/`, `ast-grep/`, `headroom/`, `github/`, `powershell/`, `mermaid/`). In contrast, integration patterns for specific platforms, chat clients, documentation hubs, or cloud services (e.g. `slack/`, `confluence/`, `google/`, `aws/`) are fed into each harness instance based specifically on the services and environments that harness interacts with.
- **When to Create Subfolders**: Create a dedicated subfolder under `supporting/<tool-or-capability>/` whenever introducing a new external CLI tool, agent capability, or workstation onboarding workflow.

### 3. `references/` (External Frameworks)
`references/` holds advisory captures of external standards and industry frameworks:
- **Tooling Families vs Domain Frameworks**: The generic template carries only tooling-related reference families required for universal development workflows (`conventional-commits/`, `markdown/`). Domain-specific framework captures (NIST, OWASP, CWE, MITRE ATT&CK/ATLAS, STRIDE) are fed into specialized domain instances and omitted from `ai-harness-core`.
- **When to Create Subfolders**: Exactly one folder per framework family (`references/<framework-family>/`).

### 4. `ai-tooling/` (Skills, Agents, Memory, and A2A)
- **Skills (`ai-tooling/skills/<family>/<skill>/SKILL.md`)**: Group skills into functional family subfolders (`meta/`, `reporting/`, `git/`, `memory/`, `cost-layers/`, `admin/`, `community/`, `google/`, etc.). Catalog-root exceptions are reserved for universal meta-review skills (`harness-review`, `model-memory-operate`).
- **Agents (`ai-tooling/agents/<agent-id>/AGENT.md`)**: Each specialist agent occupies a dedicated folder with an `AGENT.md` defining its bounded capabilities, model tier, and tool access.
- **Memory (`ai-tooling/memory/`)**: Memory is strictly partitioned into three subfolder trees:
  - `user/<git-identity>/`: Tactical user preferences, workstation setups, and operator quirks.
  - `agent/<owner_agent_id>/`: Operational failure modes, common pitfalls, and learned recovery strategies for specific agents.
  - `model/<model_id>/`: Provider/model-specific reasoning quirks, token limits, and prompt caching patterns.

---

## Relationship model and data flow invariants

The harness architecture enforces strict directional flows to prevent corpus pollution, link rot, and hidden sources of truth:

```text
actionable/ ────────► claim ────────► durable owning area

projects/ ──────────► supporting/ (strictly one-way)
projects/ ──────────► results/ (pointers only)

scratch/ ───────────► delete or promote

docs/ ──────────────► protected corpus of record (no inferred mutations)
```

- **`actionable/`**: Temporary drop zone for human requests; items are claimed, executed, promoted to durable areas, and cleared.
- **`projects/ -> supporting/`**: One-way dependency. `supporting/` tool patterns must never link back to ephemeral `projects/`, `research/`, or `actionable/` queues.
- **`projects/ -> results/`**: Project specs link to finished run artifacts under `results/`; results do not serve as policy sources of truth.
- **`scratch/`**: Non-authoritative working data, generator previews, and worktrees; never durable SoT.
- **`docs/`**: Protected corpus of record. Additions or modifications require explicit human or project promotion.

## Folder-level AGENTS.md 8-point schema

Every routed directory’s `AGENTS.md` defines eight canonical dimensions:
1. **Content ownership:** Defined agent and repository role.
2. **Placement:** Directory structure and naming conventions.
3. **Lifecycle:** How records advance, update, and close.
4. **Relationships:** Permitted and prohibited links/dependencies.
5. **Source-of-truth boundaries:** Authoritative scope.
6. **Validation:** Automated fast validators and linters.
7. **Escalation:** Ambiguity gate and research escalation.
8. **Local exceptions:** Folder-specific overrides.

## Separation of concerns

- **Routing files** determine *where* and under *which rules*.
- **Agents** perform *bounded roles*.
- **Skills** define *repeatable workflows*.
- **Folder structure** defines *ownership and lifecycle*.
- **Memory directories** define *durability checkpoints* (`user/` and `agent/`).
- **Indexes** provide *navigation* but do not replace source-of-truth files.

## Public export

Public export still redacts credentials, tokens, internal paths, and similar secrets. Redaction applies even when the payload is machinery only.

Session rules: [`../agent-session-security.md`](../agent-session-security.md).

## Related

Phase 4 initiative spec: [`../../projects/harness-v2-evolution/README.md`](../../projects/harness-v2-evolution/README.md).

