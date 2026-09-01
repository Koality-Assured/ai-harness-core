---
schema_version: "2.0.0"
name: tool-efficiency-benchmark
description: >-
  Benchmark tool output compression ratios, AST structural extraction
  fidelity, and serialization overhead across Headroom, ast-grep, and web
  distillation. Use when evaluating tool payload compression performance,
  measuring fact retention rates, or profiling execution latency of tool
  formatters.
owner_agent: benchmark-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - "Test fixture directory or sample tool outputs (git diffs, build logs, AST dumps, HTML)"
    - "Target compression pipelines (headroom, ast-grep, local_webfetch)"
  outputs:
    - "Compression ratios, fact retention scores, and serialization latency report under results/benchmarks/tool-efficiency/<YYYY-MM-DD>/"
---

# Tool Efficiency Benchmark

## When to use

Use when evaluating the empirical token compression performance and fact fidelity of tool formatters, including Headroom, `extract_ast_facts.py`, and `local_webfetch.py`. Quantifies raw token size vs compressed token size, percentage savings, structural-fact preservation, and processing overhead.

## When not to use

Do not use for everyday Headroom usage (`headroom`), AST code querying (`ast-grep`), or single web page fetching (`local-webfetch`).

## Criticality

High when upgrading compression algorithms, adjusting Headroom rule heuristics, or verifying AST extraction precision.

## Source of truth

- `python scripts/benchmarks/benchmark_tool_efficiency.py`
- `python scripts/cost-layers/validate_headroom_compression.py`
- `python scripts/cost-layers/validate_ast_grep.py`
- [`supporting/headroom/README.md`](../../../../supporting/headroom/README.md)
- [`supporting/ast-grep/README.md`](../../../../supporting/ast-grep/README.md)

## Isolation

`mutate` because generated benchmark reports land under `results/benchmarks/tool-efficiency/<YYYY-MM-DD>/`. Parent isolates `results` area.

## How to use

1. Run tool efficiency benchmark suite:
   ```bash
   python scripts/benchmarks/benchmark_tool_efficiency.py
   ```
2. Inspect results and compression breakdowns at `results/benchmarks/tool-efficiency/<YYYY-MM-DD>/report.md`.

## Dry run

```bash
python scripts/benchmarks/benchmark_tool_efficiency.py --help
python scripts/benchmarks/benchmark_tool_efficiency.py --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Tool fixtures must be sanitized and free of real API tokens or sensitive credentials.

## Completion gates

Report written to `results/benchmarks/tool-efficiency/<YYYY-MM-DD>/` showing >= 70% compression ratio on verbose tool logs and 100% structural fact retention.
