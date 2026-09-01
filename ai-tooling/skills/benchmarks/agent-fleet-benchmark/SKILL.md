---
schema_version: "2.0.0"
name: agent-fleet-benchmark
description: >-
  Orchestrate dry-run validation sweeps and simulated multi-agent fleets across
  all registered agents and skills in the repository. Use when auditing
  fleet-wide prompt cache invariance, token ceiling headroom, tool parameter
  schemas, isolation compliance, and simulated multi-agent dispatch latency.
owner_agent: benchmark-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - "Target agent fleet filter or all-agents flag"
    - "Sample size, execution timeout, or concurrency profile"
  outputs:
    - "Fleet validation summary, headroom distribution, and benchmark report under results/benchmarks/fleet/<YYYY-MM-DD>/"
---

# Agent Fleet Benchmark

## When to use

Use when conducting automated dry-run sweeps across all registered agents and skills. Useful for verifying fleet-wide prompt prefix stability, ensuring all agents have adequate token headroom against their declared `token_ceiling`, checking tool schema validity across the entire agent catalog, and validating multi-agent dispatch graphs.

## When not to use

Do not use for single agent cost calculation (`agent-cost-estimator`), static linter runs (`validate_agent.py`), or single-skill contract checking (`validate_skill.py`).

## Criticality

High before major version bumps, routing index refreshes, or when auditing fleet health.

## Source of truth

- `python scripts/benchmarks/benchmark_agent_fleet.py`
- [`ai-tooling/agents/`](../../../../ai-tooling/agents/)
- [`ai-tooling/skills/`](../../../../ai-tooling/skills/)
- [`supporting/benchmarks/README.md`](../../../../supporting/benchmarks/README.md)

## Isolation

`mutate` because benchmark logs and reports land under `results/benchmarks/fleet/<YYYY-MM-DD>/`. Parent isolates `results` area.

## How to use

1. Run full fleet dry-run benchmark:
   ```bash
   python scripts/benchmarks/benchmark_agent_fleet.py --all
   ```
2. Run targeted benchmark on specific agent families:
   ```bash
   python scripts/benchmarks/benchmark_agent_fleet.py --agents router,router-maintenance,script-ops,benchmark-agent
   ```
3. Inspect generated fleet matrix at `results/benchmarks/fleet/<YYYY-MM-DD>/report.md`.

## Dry run

```bash
python scripts/benchmarks/benchmark_agent_fleet.py --help
python scripts/benchmarks/benchmark_agent_fleet.py --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Simulated dry runs execute locally without spawning live billable API calls or invoking external subagents unless explicitly configured.

## Completion gates

Fleet dry-run report written to `results/benchmarks/fleet/<YYYY-MM-DD>/`. Zero failed assertions on agent contracts, prompt prefix stability, or token ceilings.
