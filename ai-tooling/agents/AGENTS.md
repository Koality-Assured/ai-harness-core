# Standalone agents AGENTS

Host-agnostic `AGENT.md` definitions (plus optional thin host stubs) for specialists.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Author via `agent-builder` — spawn that owner when the work is material.

## Rules

- One folder per agent: `ai-tooling/agents/<id>/AGENT.md`.
- Point at root + routing; do not paste Critical in full.
- Every `AGENT.md` inherits Critical cost layers (qmd / ast-grep / Headroom).
- Set `model_tier` (default **standard**); spawn uses [`model-tiers.md`](./model-tiers.md).
- Durable quirks and A2A specs → folded into `AGENT.md` Schema V2 frontmatter (`schema_version: "2.0.0"`).
- Host stubs read `AGENT.md` — do not fork the body. When registering a new id and `.cursor/agents/` exists, add `.cursor/agents/<id>.md`. Do not create deprecated standalone `a2a/agent-cards/*.json`.
- Catalog: `AGENT.md` (Schema V2) + [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) / area-map defaults. Do not load README for operations.
