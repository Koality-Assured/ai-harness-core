---
schema_version: "2.0.0"
name: task-eval-benchmark
description: >-
  Evaluate autonomous coding agent task execution quality, pass@1 rates, error
  recovery, and contract compliance across standardized task suites. Use when
  benchmarking model performance on code refactoring, AST extraction, and tool
  dispatch tasks against empirical ground-truth criteria.
owner_agent: benchmark-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - "Task suite JSON file path (e.g. coding_agent_benchmark_v1.json)"
    - "Target agent ID or model configuration under evaluation"
    - "Timeout per task and evaluation criteria (pass@1, token spend, wall time)"
  outputs:
    - "Task evaluation scorecards, pass rates, artifact diffs, and benchmark reports under results/benchmarks/task-eval/<YYYY-MM-DD>/"
---

# Task Evaluation Benchmark

## When to use

Use when evaluating agent quality and reasoning capability on standardized tasks. Runs task suites such as `coding_agent_benchmark_v1.json`, measuring pass@1 accuracy, error recovery efficiency, token cost per task, and contract compliance across models and prompt variations.

## When not to use

Do not use for static agent syntax validation (`validate_agent.py`), unit testing repo code (`pytest`), or general cost estimation (`agent-cost-estimator`).

## Criticality

High when evaluating new foundation models, prompt changes, or assessing regression risks before deploying agent workflow updates.

## Source of truth

- `python scripts/benchmarks/benchmark_task_eval.py`
- `scratch/ecosystem-repos/ai-research-and-benchmarks/benchmarks/suites/coding_agent_benchmark_v1.json`
- [`supporting/benchmarks/README.md`](../../../../supporting/benchmarks/README.md)

## Isolation

`mutate` because task evaluations output logs, artifact diffs, and scorecards to `results/benchmarks/task-eval/<YYYY-MM-DD>/`. Parent isolates `results` area.

## How to use

1. Run standardized task evaluation benchmark:
   ```bash
   python scripts/benchmarks/benchmark_task_eval.py --suite scratch/ecosystem-repos/ai-research-and-benchmarks/benchmarks/suites/coding_agent_benchmark_v1.json
   ```
2. Review scorecard report at `results/benchmarks/task-eval/<YYYY-MM-DD>/report.md` and detailed evaluation data in `summary.json`.

## Dry run

```bash
python scripts/benchmarks/benchmark_task_eval.py --help
python scripts/benchmarks/benchmark_task_eval.py --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Task evaluations execute in bounded sandboxes with strict timeouts and path confinement.

## Completion gates

Scorecard and evaluation artifacts saved under `results/benchmarks/task-eval/<YYYY-MM-DD>/`. Pass@1 rate and token metrics documented.
