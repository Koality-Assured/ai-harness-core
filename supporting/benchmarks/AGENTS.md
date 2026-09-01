# Benchmarks supporting area

Delta for agents operating in `supporting/benchmarks/` and running benchmark tools under `scripts/benchmarks/`.

## Read first

- Root [`../../AGENTS.md`](../../AGENTS.md)
- [`../../routing/AGENTS.md`](../../routing/AGENTS.md)
- [`../../docs/anti-slop.md`](../../docs/anti-slop.md)
- [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md)

## Purpose

Houses empirical benchmark methodology, pricing models, metric formulas (pass@1, MRR, compression ratios, KV cache hit ratios), and repeatable evaluation execution patterns.

## Local constraints

- Default agent: [`benchmark-agent`](../../ai-tooling/agents/benchmark-agent/AGENT.md) (`model_tier: standard`).
- All benchmark scripts live under `scripts/benchmarks/` and are tagged Python scripts.
- Benchmark reports land under `results/benchmarks/<suite>/<YYYY-MM-DD>/` and `results/cost-layers/agent-estimates/`. Never dump raw outputs into `scratch/` as durable records.
- In-session anti-slop and humanizer MUST be applied to all human-readable summaries before declaring completion.
- Ground-truth fixtures must be sanitized and free of real API tokens, passwords, or proprietary customer PII.

## Next hops

- Cost modeling methodology & pricing presets: [`methodology.md`](./methodology.md)
- Agent cost estimation: `python scripts/benchmarks/estimate_agent_costs.py`
- Fleet dry-run sweeps: `python scripts/benchmarks/benchmark_agent_fleet.py`
- Corpus retrieval evaluation: `python scripts/benchmarks/benchmark_retrieval.py`
- Tool compression evaluation: `python scripts/benchmarks/benchmark_tool_efficiency.py`
- Task evaluations: `python scripts/benchmarks/benchmark_task_eval.py`
- Master benchmark suite: `python scripts/benchmarks/run_benchmark_suite.py`
