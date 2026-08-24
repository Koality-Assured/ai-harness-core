# Agent cards (Deprecated)

> [!NOTE]
> **Consolidation Notice (Schema V2 / LOW-02 / MED-03)**:
> Standalone JSON files under `ai-tooling/a2a/agent-cards/*.json` have been deprecated and consolidated directly into canonical specialist definitions at [`../../agents/<id>/AGENT.md`](../../agents/).
> `AGENT.md` YAML frontmatter is now the **single source of truth (SoT)** for agent identity, capabilities, I/O contracts, allowed tools, isolation modes, delegation targets, model tiers, and token consumption ceilings (`token_ceiling`).

## Canonical Agent Schema V2

All registered specialist agents define their contracts and A2A specifications via YAML frontmatter in their respective [`../../agents/<id>/AGENT.md`](../../agents/) files using Schema `2.0.0`:

```yaml
---
schema_version: "2.0.0"
agent_id: "<id>"
name: "<Display Name>"
description: "..."
model_tier: "standard" # fast | standard | high | max
token_ceiling: 100000  # Cumulative token consumption limit (MED-03)
capabilities:
  - "capability-1"
  - "capability-2"
contracts:
  inputs:
    - "Input specification 1"
  outputs:
    - "Output specification 1"
isolation_modes:
  - "mutate"
  - "read-only"
allowed_tools:
  - "read_file"
  - "write_file"
  - "run_command"
delegation_targets:
  - "router"
  - "other-agent"
prohibitions:
  - "prohibition rule 1"
quirks:
  - "quirk description 1"
last_verified: "YYYY-MM-DD"
---
```

## Validation

All `AGENT.md` files are validated using:

```bash
python scripts/ai-tooling/validate_agent.py --all
```

## Host Model Tiers

Host platform selections and reasoning tiers (`fast`, `standard`, `high`, `max`) are governed centrally in [`../../agents/model-tiers.md`](../../agents/model-tiers.md).
