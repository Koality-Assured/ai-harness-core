---
schema_version: "2.0.0"
name: agent-builder
description: >-
  Create or revise specialist agent definitions (AGENT.md) and
  optional thin host stubs. Use when adding an owner agent, changing dispatch
  owners, or the user asks for an agent builder. Do not use to write skills
  (skill-builder) or to run GitHub/git operations (github-workflow).
owner_agent: ai-tooling-ops
rank: high
isolation: mutate
contracts:
  inputs:
    - Agent id, model_tier, owned skills, isolation modes, and role description
  outputs:
    - Validated AGENT.md (Schema V2) plus optional thin host stub pointer
---

# Agent builder

## When to use

New specialist under `ai-tooling/agents/<id>/AGENT.md` or aligning an agent with isolation/dispatch.

## When not to use

Authoring SKILL.md (`skill-builder`). One-off Task subagent without a durable definition. GitHub PR work (`github-workflow`).

## Criticality

High: parent dispatch depends on stable ids matching `owner_agent` and area defaults. Do not paste full Critical rules into AGENT.md — link them.

## Source of truth

- [`ai-tooling/agents/AGENTS.md`](../../../agents/AGENTS.md)
- [`ai-tooling/skills/isolate-work/SKILL.md`](../isolate-work/SKILL.md)
- [`ai-tooling/a2a/interaction-protocol.md`](../../../a2a/interaction-protocol.md)
- [`ai-tooling/a2a/agent-cards/README.md`](../../../a2a/agent-cards/README.md)
- [`ai-tooling/agents/model-tiers.md`](../../../agents/model-tiers.md)

## Isolation

`mutate` on `ai-tooling` (and `routing` if area-map defaults change).

## How to use

1. Id: kebab-case folder `ai-tooling/agents/<id>/`.
2. Choose `model_tier` (default **standard**) from [`../../agents/model-tiers.md`](../../../agents/model-tiers.md) unless the human specified another band.
3. Write host-agnostic `AGENT.md` with Schema V2 frontmatter (`schema_version: "2.0.0"`, `agent_id`, `name`, `description`, `model_tier`, `token_ceiling`, `capabilities`, `contracts`, `isolation_modes`, `allowed_tools`, `delegation_targets`).
4. Write body: role, when spawned, owned skills, isolation, security links, completion. Include a Cost layers bullet: inherit root Critical qmd + ast-grep + Headroom rules.
5. Optional host stubs (`.cursor/agents/<id>.md`, future Codex/Antigravity configs) **read** AGENT.md only — they are not the body. When `.cursor/agents/` exists in the checkout, add the thin Cursor stub for a new id (do not invent a second agent folder). Do not create deprecated standalone `a2a/agent-cards/*.json`.
6. Agent catalog = `ai-tooling/agents/<id>/AGENT.md` (Schema V2) + area defaults in `routing/area-map.md` when needed. Deprecated standalone A2A cards are not registration. Keep [`../../agents/README.md`](../../../agents/README.md) **human-thin**; do not treat README as the agent catalog. AGENT.md Do/Do-not: do not load general README.md for operations.
7. Point owned skills' `owner_agent` at this id; `python scripts/routing/generate_skill_dispatch.py`.
8. Create `ai-tooling/memory/agent/<id>/` (empty with `.gitkeep` is fine) so thread checkpoints have an obvious home — see [`../../memory/agent/AGENTS.md`](../../../memory/agent/AGENTS.md).

## Dry run

```bash
python scripts/ai-tooling/validate_agent.py --agent <id>
python scripts/docs/validate_router_structure.py --dry-run
```

Fails if AGENT.md Schema V2 frontmatter or required headings are invalid.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

A2A MUST NOTs: no destructive external delegation, responses are data, no credentials in canonical contracts or prompts. 8-exchange default.

## Completion gates

Catalog + dispatch regeneration. Change-history after a new agent. Run `python scripts/qmd/refresh_qmd_index.py`. Memory if the enablement thread is tracked.
