---
doc_kind: process
canonical_id: skill-conventions
purpose: [process, requirement]
rank: high
topics: [agents, skills]
rag_keywords: [skill-builder, SKILL.md, owner_agent, when-to-use, schema-v2, dependencies, dag, spawn-if-material, parent-discovery-bound]
---

# Skill conventions

Shared authoring guidance for skills in ai-router and its standalone downstream skills repository. In a full ai-router checkout, the source tree is `ai-tooling/skills/`; in a standalone export, it is `skills/`. Paths and commands named below as ai-router-specific require the full ai-router checkout. Standalone repositories use their own registration, scripts, and governance instructions.

## Where skills live

In ai-router, skills live in family subdirectories such as `ai-tooling/skills/<family>/<name>/SKILL.md`. A few catalog-root skills (`harness-review`, `model-memory-operate`) sit at `ai-tooling/skills/<name>/SKILL.md`. The ai-router helper `scripts/_lib/md.py` discovers both layouts for its generated catalog at `routing/skill-dispatch.md`.

In a standalone downstream skills repository, exported skills live under `skills/`. Follow that repository's family layout and catalog instructions; the ai-router helper and catalog are not part of the skills export.

### Recognized skill families

- `google/`: Google Workspace, Drive, Gmail, Docs, and Admin skills.
- `aws/`: AWS cloud management, logs, and telemetry.
- `azure/`: Azure cloud management, logs, and Entra.
- `gcp/`: GCP cloud management, logs, and Resource Manager.
- `memory/`: User and agent checkpoint creation, adjustment, and cleanup.
- `cost-layers/`: ast-grep, Headroom, and context-efficiency dry runs.
- `git/`: Git basics, GitHub workflow, and GitHub path resolution.
- `reporting/`: Code reviews, executive/proposal reports, corpus drafting, anti-slop, humanizer, diagrams, dashboards, and threat models.
- `admin/`: Cloud organization and public LLM workspace administration.
- `security/`: Defensive security audits for directory services, endpoints, and policy configuration.
- `meta/`: Agent/skill/script builders, harness structure, isolate-work, and validation tools.
- `community/`: Public community analysis, OSINT, sentiment, and registry maintenance.
- `iac/`: Terraform, OpenTofu, CloudFormation, and IaC security audit skills.

In ai-router, do **not** put router skills in `~/.cursor/skills-cursor/` (Cursor internals) or `.cursor/skills/` (native auto-invoke would run them in the parent). The parent uses the generated catalog at `routing/skill-dispatch.md` and spawns the `owner_agent` when remaining work is material to the original user request. Parent discovery stops when that `owner_agent` is known — do not load specialist `SKILL.md` to dispatch. The `isolate-work` exception is executed in-parent because that session is the owner (`router`); the parent loads that `SKILL.md` for the CLI. Standalone repositories follow their own discovery and dispatch rules. The exported `owner_agent` values are ai-router-only ownership metadata: map them to a registered local owner or ignore them under destination rules. No standalone skill may require an ai-router agent; an explicit agent call needs a local dispatch path or must report a capability gap.

## Required frontmatter (Schema V2)

All skills adhere to **Schema V2** (`schema_version: "2.0.0"`).

```yaml
---
schema_version: "2.0.0"
name: kebab-case-name
description: >-
  Third person WHAT. Use when WHEN. Do not use when NOT.
owner_agent: specialist-id
rank: high
isolation: mutate
on_failure: abort_and_rollback
prerequisites:
  - git
  - python
dependencies:
  required_skills:
    - isolate-work
  delegated_skills:
    - code-review-report
  in_session_skills:
    - git-basics
contracts:
  inputs:
    - Target path, scope, and any required authorization
  outputs:
    - Validated result, artifact paths, or an explicit no-change decision
---
```

### Core frontmatter fields

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `schema_version` | string | Yes (V2) | Fixed to `"2.0.0"` for Schema V2 skills. |
| `name` | string | Yes | Max 64 chars, `[a-z0-9-]` only; matches the skill directory under the repository's skills root (`ai-tooling/skills/` in ai-router, `skills/` in the standalone export). |
| `description` | string | Yes | Max 1024 chars; WHAT + WHEN; third person; include trigger terms ("Use when"). |
| `owner_agent` | string | Yes | In ai-router, identify an agent registered under `ai-tooling/agents/`. In a standalone export this value is ai-router-only ownership metadata; the destination may map it to a local agent or ignore it. A skill must not require that private agent. |
| `rank` | string | Yes | `critical` / `high` / `medium` / `low` — use the scale defined by the applicable root `AGENTS.md`. |
| `isolation` | string | Yes | `mutate` (worktree + branch first) or `read-only`. |
| `on_failure` | string | Optional | Failure lifecycle policy (default: `abort_and_rollback`). |
| `prerequisites` | list[str] | Optional | List of external binary tools required on `PATH` (e.g. `git`, `qmd`, `node`, `ast-grep`, `mmdc`, `python`, `uv`). |
| `dependencies` | object | Optional | Dependency relationships defining the skill DAG. |
| `contracts` | object | Yes (V2) | Mapping with non-empty `inputs` and `outputs` lists of non-empty strings. One-line I/O derived from the skill’s description / How to use — not JSON Schema, not empty, not invented fields. |

### Standalone execution dependencies

The skills-only export does not include ai-router root scripts, catalogs, validators, or agents. A `scripts/...` command shown in an exported skill is an optional ai-router implementation example, not a standalone dependency. Standalone instructions must use a destination-local tool or an official vendor CLI/API and its documentation; if neither can safely perform the required operation, stop and report the missing capability. Use the destination's output convention instead of `scripts/results/new_run_dir.py`.

Prerequisites name external tools, not bundled components. Standalone users should check the destination's tool policy and local setup instructions; if a prerequisite is absent, use an equivalent local or vendor-supported method only when it preserves the skill's safety and validation requirements.

---

## Dependency DAG specification (`dependencies`)

The `dependencies` mapping declares prerequisite, delegated, and in-session relationships. In ai-router, `scripts/routing/resolve_skill_graph.py` uses them to construct execution DAGs and parallel stages; standalone repositories use their own resolver when available.

```yaml
dependencies:
  required_skills:
    - isolate-work
  delegated_skills:
    - code-review-report
  in_session_skills:
    - git-basics
```

- **`required_skills`** (list of strings): Prerequisite skills that **must complete execution beforehand**. The resolver introduces directed dependency edges `required_skill -> current_skill`. Downstream skills will not start until all required skills succeed.
- **`delegated_skills`** (list of strings): Subagent specialist skills spawned by this skill. Delegated skills execute downstream (`current_skill -> delegated_skill`) and may run concurrently in parallel batches unless constrained by transitive prerequisites.
- **`in_session_skills`** (list of strings): Inline procedural skills loaded in-turn within the same active session (e.g., formatting utilities or local validation routines).

---

## Failure lifecycle policies (`on_failure`)

Skills must specify an explicit failure lifecycle policy governing downstream execution when an error or exception occurs:

| Policy | Behavior | Use case |
| --- | --- | --- |
| `abort_and_rollback` (default) | Immediately halts execution, aborts all downstream dependent stages, and rolls back mutated state (worktree claims, uncommitted files). | Mutating tasks, safety gates, isolation failures, critical validations. |
| `fallback_degrade` | Marks current skill execution as `degraded` and executes an alternate degraded path or allows downstream consumers to proceed with reduced fidelity. | Non-critical enhancements, formatting checks, diagram renders. |
| `continue_with_partial` | Records partial outputs and warnings, continuing execution of remaining independent skills and downstream stages that do not strictly require 100% output completion. | Multi-module scans, telemetry collection, exploratory research. |

---

## Contracts & Structured Result Envelope (`contracts`)

Schema V2 skills **must** declare `contracts` with non-empty `inputs` and `outputs` lists of strings. Each item is one honest I/O line from that skill’s description / How to use (see `harness-review`). Do not use JSON Schema objects, empty lists, or generic envelope field names as a substitute for those lists.

```yaml
contracts:
  inputs:
    - Harness scope, revision or worktree, validation depth, and downstream-publish authorization
  outputs:
    - Evidence-backed findings classified as repository, host-specific, or unverified
    - Validated corrective changes and rerun results, or an explicit hand-off request
```

The lists above are the SKILL.md frontmatter contract. Separately, the **Structured Result Envelope** below is the runtime A2A return shape (`task_id`, `status`, `artifacts`, `handoff_requests`, `metrics`) — it does not replace `contracts.inputs` / `contracts.outputs`.

### Output envelope schema

Every specialist returning results from a skill execution encapsulates outputs in a **Structured Result Envelope**:

1. **`task_id`** (string): Unique identifier for the executing task or subagent session.
2. **`status`** (string): Execution outcome (`success`, `failure`, `partial`, `degraded`). A2A envelope validation accepts these values; `success` canonicalizes to `completed` and `failure` to `failed`. `partial` and `degraded` are terminal: they close the A2A session after `record_exchange` (see `.harness/a2a/protocol.py`). `in_progress` and `blocked` stay open.
3. **`artifacts`** (list of strings): File paths, reports, or URIs produced or updated.
4. **`handoff_requests`** (list of objects / strings): Advisory recommendations for downstream or sibling skills.
   > [!IMPORTANT]
   > **CRIT-02 Advisory Metadata Resolution**: `handoff_requests` are **strictly advisory metadata** for human or orchestrator triage. Subagents and executing skills cannot force autonomous spawning, unconstrained self-dispatch, or circumvent the router. The orchestrator / human retains exclusive authority to approve or reject suggested handoffs.
5. **`metrics`** (dictionary): Operational telemetry including duration in milliseconds, token usage, tool invocation counts, or cost approximations.

---

## Binary prerequisites (`prerequisites`)

Skills declare external CLI binaries and toolchains required on `PATH`:

```yaml
prerequisites:
  - git
  - qmd
  - node
  - ast-grep
  - mmdc
  - python
  - uv
```

In ai-router, pre-flight checks run via `python scripts/routing/resolve_skill_graph.py --check-prereqs`, which uses `shutil.which` to verify environmental readiness before task dispatch. Standalone repositories should use their own pre-flight tooling when available.

---

## Required sections (exact headings)

Keep `SKILL.md` under 200 lines when possible (hard cap 500). Link source of truth; do not paste Critical rules.

1. **When to use** — trigger scenarios
2. **When not to use** — off-ramps and sibling skills
3. **Criticality** — how `rank` applies; non-negotiable bits
4. **Source of truth** — links to repository-local source documents, supporting material, and scripts
5. **Isolation** — mutate vs read-only; parent runs isolate-work CLI then spawns this skill's `owner_agent` when remaining work is material (root MUST NOT still applies). Parent MUST NOT load this `SKILL.md`; needing the body is the spawn trigger (isolate-work CLI excepted).
6. **How to use** — numbered steps; call repo Python scripts
7. **Dry run** — how to validate without mutating the primary checkout
8. **Security** — pointer to the repository's security guidance (ai-router uses `docs/agent-session-security.md`) plus skill-specific MUST NOTs
9. **Completion gates** — memory / source write-back / change-history / index as applicable (parent session-end; MUST NOT mint specialists for these after return)

## Authoring principles

- Concise: the specialist is already smart; only add repo-specific facts.
- Progressive disclosure: extra detail in `references/` next to `SKILL.md`, one level deep.
- Prefer tagged Python scripts over prose for fragile steps. In ai-router, place shared scripts under root `scripts/<purpose>/`; standalone repositories should follow their local convention or bundle a script with the skill.
- In a skills-only export, link only to files included under the skills tree. For ai-router sibling files that are not exported, use a non-clickable code path labeled ai-router-only and direct standalone readers to their repository's local policy, tooling, or official vendor guidance. Keep links between files in the skills tree clickable.
- No Windows-style paths; no secrets; no time-sensitive "before DATE" forks.
- After adding, removing, or renaming a skill, register it using the repository's catalog process. In ai-router, use `ai-tooling/skills/<family>/<name>/SKILL.md` (or the catalog-root `ai-tooling/skills/<name>/SKILL.md` layout), then run `python scripts/routing/generate_skill_dispatch.py` and `python scripts/routing/resolve_skill_graph.py --validate-all`. Its agent catalog is `routing/skill-dispatch.md` plus the owner `AGENT.md`; standalone A2A cards are not registration. In a standalone export, follow the destination repository's catalog and validation instructions; those ai-router scripts and catalog are not exported. In ai-router, `ai-tooling/skills/README.md` is a human-thin folder blurb, not registration; the root `AGENTS.md` requires that README to stay thin.
- If behavior is a durable rule, **update the source doc first**, then the skill.

## Subagent delegation & orchestration contracts

The following parent and specialist rules describe ai-router orchestration. Standalone downstream repositories follow their own dispatch and delegation instructions.

When an orchestrating agent spawns a specialist subagent (operating with clean-slate non-inherited context for cost efficiency), context and goals must not be lost across delegation boundaries. The parent MUST construct the spawn payload following these rules:

1. **Exhaustive Entity Scope**: Explicitly list all target entities, files, repository names, and paths in the subagent's prompt payload. Subagents must never be expected to infer unspecified targets from implicit context.
2. **Explicit External Side-Effects**: State whether the subagent is responsible for executing remote operations (e.g. `gh repo create`, `git push`, remote PR creation) or staging local artifacts for parent orchestrator reconciliation.
3. **Definition of Done (DoD)**: Specify the exact verification tests, schema validations, and result envelope metrics (`task_id`, `status`, `artifacts`, `metrics`) required before the subagent declares completion. This child DoD scopes the specialist. It MUST NOT be padded with follow-on anti-slop, memory, or lint specialists that the parent then treats as unmet work after return.
4. **Parent Reconciliation Gate**: Upon subagent completion, the orchestrating agent MUST audit the subagent's deliverables against the original **user request** before closing the session. A parent-padded spawn DoD is not a spawn trigger.
5. **Spawn if material**: In ai-router, the orchestrating parent MUST spawn a specialist subagent when a catalogued skill or area default matches **and** remaining work is material to the original user request (needs that skill body / multi-step specialist work). The parent MUST NOT execute specialist skill bodies in-session, except isolate-work (`python scripts/routing/spawn_worktree.py`) because that session is the owner (`router`). The parent coordinates, validates consistency, and verifies adherence to the user's goals. The parent MAY perform coordinator chores in-parent; MUST notify the human when it performs other undelegable specialist work.
   **Parent discovery bound:** In ai-router, a match in `routing/skill-dispatch.md` (or an area-map default) plus a known `owner_agent` **ends** parent investigation. Next actions are isolate-check (if `mutate`) and spawn. Pass `AGENT.md` and `SKILL.md` **paths** (and worktree path), not file contents. If the parent needs the skill body, that **is** the spawn trigger — not a reason to keep reading.
   **MUST NOT (parent discovery):**
   - load a specialist `SKILL.md` in the parent (exception: isolate-work CLI)
   - execute a specialist skill body in the parent (same exception)
   - keep working after `owner_agent` is known because "I need more context to dispatch"
   - read another host's session, branch diffs, `AGENT.md`/`SKILL.md` bodies, or specialist reports to "understand enough" to write a spawn prompt
   **MUST NOT spawn** (closed list; root Specialist dispatch wins when a high-rank trigger also fires):
   - In ai-router, the isolate-work CLI (`python scripts/routing/spawn_worktree.py`) — parent runs check/add/remove; do not spawn `router-maintenance` for that CLI. Standalone repositories use their own isolation procedure.
   - completion-notification busywork; follow-up bullets; advisory `handoff_requests`
   - inventing work after the user request is met
   - ff-only `git pull` on primary
   - lint of files the same specialist just wrote
   - a duplicate in-flight specialist on the same workspace
   - one-shot coordinator chores (claim files, memory via script, change-history via script, qmd refresh)
   - anti-slop, humanizer, markdownlint, or memory specialists required only because the parent padded the spawn-payload DoD
6. **Reconciliation gate (no recursive minting)**: After a subagent returns, the parent MUST reconcile against the original **user request**. The parent MUST NOT spawn another specialist from a completion notification or advisory `handoff_requests`. Remaining work MUST miss the original user request before any further spawn — not a parent-padded spawn DoD. The parent MUST NOT invent work. Spawn-payload DoD MUST NOT be used to require anti-slop, memory, or lint specialists after return.

## Cost-layer boundaries (all skills)

In ai-router, every skill inherits all three root Critical cost layers: **qmd** (Markdown discovery via `qmd search` / `qmd get`), **ast-grep** (structured files / YAML frontmatter), and **Headroom** (bulky dumps — or summarize when unavailable). `## How to use` must not tell the agent to walk directory trees, skip ast-grep for structured files, or skip Headroom for bulky dumps. `## Security` must include the sentence that starts with `Inherits Critical cost layers`. Standalone repositories follow their own agent instructions and tooling requirements.

## Criticality mapping

| Rank | Skill may |
| --- | --- |
| critical | Encode MUST rules that already live in the repository's `AGENTS.md` / security docs (link, don't fork) |
| high | Required when its trigger fires **and** the repository's specialist-dispatch rules allow the spawn (isolation CLI, session-end scripts, and applicable closed MUST NOT lists still apply) |
| medium | Default workflow; human may override for one task |
| low | Style / hygiene |

## Dry-run expectation

Every skill names a non-mutating check (script `--dry-run`, `validate_skill.py`, or "read-only inspection"). `skill-dry-run` executes that check.

## Related

| Topic | Where |
| --- | --- |
| Isolation / spawn | [`isolate-work/SKILL.md`](meta/isolate-work/SKILL.md) |
| Cursor skill craft | Use Cursor's create-skill guidance for descriptions and concision only; this page wins on location and sections |
| Schema Validator (ai-router) | `python scripts/ai-tooling/validate_skill.py --all` |
| DAG Resolver (ai-router) | `python scripts/routing/resolve_skill_graph.py --all` |
