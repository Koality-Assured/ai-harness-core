# AI tooling AGENTS

Enablement for memory, skills, standalone agents, and A2A — not a substitute for `docs/` standards or `routing/` operating procedure.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md).

## Nested scopes

| Path | Role |
| --- | --- |
| [`memory/`](./memory/) | Authoritative checkpoints: `user/<git-identity>/`, `agent/<owner_agent_id>/`, and `model/<model-family>/` |
| [`skills/`](./skills/) | SKILL.md workflows + skill-conventions SoT |
| [`agents/`](./agents/) | Standalone AGENT.md definitions |
| [`a2a/`](./a2a/) | Protocol + canonical agent-contract migration note |

## Rules

- Update the owning source area first when a skill encodes a directive; then update the skill.
- Memory ≠ durable architecture: stable patterns go to `docs/`, `supporting/`, or `routing/`.
- Keep secrets out of canonical agent contracts.
- Spawn `ai-tooling-ops` (or the skill’s `owner_agent`) when that catalogued work is material. Session-end memory and isolate CLI stay with the parent.
