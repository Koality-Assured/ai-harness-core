# Memory AGENTS

Portable checkpoints for cold resumption. Split into **user** (human/workstation) and **agent** (per-specialist threads).

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Parent spawns `ai-tooling-ops` for `memory-create` / `memory-adjust` / `memory-cleanup`.

## Layout

| Path | Role |
| --- | --- |
| [`user/`](./user/) | Per-human checkpoints keyed by Git/GitHub identity |
| [`agent/`](./agent/) | Per-specialist thread checkpoints under registered `owner_agent` ids |

## Rules

- This tree is the **authoritative** project memory store for any AI agent — not `~/.cursor`, host-home memory, Documents, or Cursor personal rules as the default.
- Update before finishing any session that advanced a tracked thread (Critical gate).
- One file per active thread; ≈30-second read.
- Status: `Active` | `Paused` | `Complete`; refresh `Last updated`.
- No secrets.
- Memory never substitutes for source-area write-back; promote reusable lessons to the owning area.
- Flat `ai-tooling/memory/*.md` thread files are obsolete — write under `user/<git-identity>/` or `agent/<owner_agent_id>/`.

## Ownership note (skill-agent-dispatch)

The isolation + dispatch + skills enablement thread lives under [`agent/router/`](./agent/router/) (`skill-agent-dispatch.md`). Router owns spawn/isolation/dispatch orchestration; `ai-tooling-ops` owns skill/agent body authoring and still runs the memory-* skills that write these files.
