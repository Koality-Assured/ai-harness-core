# Benchmarking & Cost Methodology

Human overview of the repository's empirical benchmarking suite, cost estimation frameworks, and agent fleet simulation harnesses.

**Agents:** Operational instructions live in [`AGENTS.md`](./AGENTS.md) and topic guidance in [`methodology.md`](./methodology.md). Do not use this README as agent context (root [`../../AGENTS.md`](../../AGENTS.md) High README rule).

## Modules Overview

- **Agent Cost Estimator (`estimate_agent_costs.py`)**: Models token consumption, tool schema footprints, multi-turn accumulation, KV cache hit discounts, and financial costs across host model tiers (`fast`, `standard`, `high`, `max`).
- **Agent Fleet Benchmark (`benchmark_agent_fleet.py`)**: Executes dry-run validation sweeps and simulated multi-agent fleets across all 24 agents and 80+ skills.
- **Corpus Retrieval Benchmark (`benchmark_retrieval.py`)**: Evaluates BM25 vs hybrid search recall, MRR, Precision@K, and query latency across ground-truth queries.
- **Tool Efficiency Benchmark (`benchmark_tool_efficiency.py`)**: Measures token compression ratios, structural fact retention, and latency across Headroom, ast-grep, and web distillation formatters.
- **Task Evaluation Benchmark (`benchmark_task_eval.py`)**: Scores autonomous coding agent quality, pass@1, and contract compliance against standard coding task suites.
