---
schema_version: "2.0.0"
name: agent-cost-estimator
description: >-
  Estimate token consumption, system prompt overhead, tool schema footprints,
  KV prompt cache hit ratios, and financial costs for standalone agent
  definitions and paired skill executions across model tiers (fast, standard,
  high, max) and major provider pricing matrices. Use when forecasting agent run
  budgets, evaluating prompt caching economics, or comparing model tier pricing
  for single-turn or multi-turn agent workflows.
owner_agent: benchmark-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - "Target agent ID, paired skill name, or fleet selection"
    - "Model tier or specific provider model (Gemini, Claude, GPT, Grok)"
    - "Multi-turn trajectory parameter (turn count, tool calls per turn, output tokens per turn)"
  outputs:
    - "Cost estimation breakdown, KV cache savings, and token trajectory profile under results/cost-layers/agent-estimates/"
---

# Agent Cost Estimator

## When to use

Use when estimating token consumption and dollar costs for individual agents or paired agent-skill runs. Useful for budgeting multi-agent workflows, calculating prompt caching ROI, evaluating KV cache hit break-evens, and comparing pricing across host model tiers (`fast`, `standard`, `high`, `max`).

## When not to use

Do not use for static prompt prefix invariance checks (`validate_prompt_caching.py` via `cost-layer-dry-run`), everyday file retrieval (`qmd-usage`), or general model benchmark lookups (`benchlm-lookup`).

## Criticality

High for cost modeling, budget governance, and multi-turn agent capacity planning.

## Source of truth

- `python scripts/benchmarks/estimate_agent_costs.py`
- [`ai-tooling/agents/model-tiers.md`](../../../../ai-tooling/agents/model-tiers.md)
- [`supporting/benchmarks/README.md`](../../../../supporting/benchmarks/README.md)
- [`results/cost-layers/`](../../../../results/cost-layers/)

## Isolation

`mutate` because generated cost estimation profiles and reports are saved to `results/cost-layers/agent-estimates/<slug>/`. Parent isolates `results` prior to mutating execution.

## How to use

1. Run single agent estimation:
   ```bash
   python scripts/benchmarks/estimate_agent_costs.py --agent assessment-agent
   ```
2. Run paired agent-skill run estimation:
   ```bash
   python scripts/benchmarks/estimate_agent_costs.py --agent assessment-agent --skill threat-model --turns 5
   ```
3. Run fleet-wide cost matrix across all model tiers:
   ```bash
   python scripts/benchmarks/estimate_agent_costs.py --all --out results/cost-layers/agent-estimates/latest
   ```
4. Review generated report at `results/cost-layers/agent-estimates/latest/report.md` and machine-readable data at `results/cost-layers/agent-estimates/latest/estimates.json`.

## Dry run

```bash
python scripts/benchmarks/estimate_agent_costs.py --help
python scripts/benchmarks/estimate_agent_costs.py --agent router --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Cost estimation scripts parse agent and skill definitions locally without sending prompts or proprietary context to external endpoints.

## Completion gates

Generated report saved to `results/cost-layers/agent-estimates/<slug>/report.md` with JSON summary. Update `supporting/benchmarks/` if pricing presets or token estimation formulas change.
