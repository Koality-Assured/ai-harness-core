# Memory AGENTS

Portable checkpoints for cold resumption. Split into **user** (human/workstation), **agent** (per-specialist threads), and **model** (model-family capability outcomes).

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Session-end memory checkpoints are a parent gate — do not mint specialists for them. Spawn `ai-tooling-ops` when `memory-create`, `memory-adjust`, or `memory-cleanup` *is* the material task. Spawn `memory-operator` when `model-memory-operate` *is* the material task — not `ai-tooling-ops`.

## Layout

| Path | Role |
| --- | --- |
| [`user/`](./user/) | Per-human checkpoints keyed by Git/GitHub identity |
| [`agent/`](./agent/) | Per-specialist thread checkpoints under registered `owner_agent` ids |
| [`model/`](./model/) | Cross-host model-family capability outcomes; links to user/agent context instead of copying it |

## Rules

- This tree is the **authoritative** project memory store for any AI agent — not `~/.cursor`, host-home memory, Documents, or Cursor personal rules as the default.
- **Core Purpose:** Agent memory stores operational knowledge, common problems/pitfalls, environment quirks, and learned recovery strategies to ensure an agent's future success.
- **What Memory IS NOT:**
  - NOT a session work log or chronicle of completed PRs/features (belongs in `change-history/`).
  - NOT a project task tracker (belongs in `projects/<slug>/`).
  - NOT a duplicate of skill instructions (belongs in `SKILL.md` or `references/`).
  - NOT a duplicate of agent configuration/role boundaries (belongs in `AGENT.md`).
  - NOT a permanent research repository (belongs in `research/` or `references/`).
- **Standard Shape for Agent Memory:**
  - Header: Status (`Active` | `Paused`), `Last updated`, `Scope`.
  - `## Common Failure Modes & Pitfalls`
  - `## Environment Quirks & Tooling Gotchas`
  - `## Learned Recovery Strategies`
  - `## Critical Success Factors`
- One file per active operational thread; ≈30-second read.
- No secrets.
- Memory never substitutes for source-area write-back; promote reusable lessons to the owning area.
- Flat `ai-tooling/memory/*.md` thread files are obsolete — write under `user/<git-identity>/` or `agent/<owner_agent_id>/`.

## Ownership note (skill-agent-dispatch)

The isolation + dispatch orchestration operational memory lives under [`agent/router/`](./agent/router/) (`skill-agent-dispatch.md`). Router owns spawn/isolation/dispatch orchestration and writes session-end checkpoints here. `ai-tooling-ops` owns skill/agent body authoring; spawn it for user/agent `memory-*` only when that skill is the material user task. `memory-operator` owns `model-memory-operate` (model-family capability outcomes under [`model/`](./model/)).
