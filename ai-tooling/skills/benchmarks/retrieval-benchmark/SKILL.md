---
schema_version: "2.0.0"
name: retrieval-benchmark
description: >-
  Benchmark corpus retrieval accuracy, Mean Reciprocal Rank (MRR), Precision@K,
  and token consumption comparing qmd BM25 search vs hybrid semantic retrieval
  vs AST symbol lookup. Use when evaluating corpus retrieval performance,
  tuning index search ranking, or measuring retrieval token savings over raw file
  reads.
owner_agent: benchmark-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - "Test query set or ground-truth retrieval fixture path"
    - "Retrieval mode (bm25, hybrid, ast-grep, direct)"
    - "Evaluation metrics (MRR, precision@k, recall, token_cost)"
  outputs:
    - "Retrieval evaluation benchmark report and metrics JSON under results/benchmarks/retrieval/<YYYY-MM-DD>/"
---

# Retrieval Benchmark

## When to use

Use when measuring empirical accuracy and token savings of Markdown retrieval mechanisms across the repository. Evaluates qmd BM25 retrieval, hybrid vector/lexical search, and AST symbol extraction against known ground-truth topic queries to calculate Precision@1, Precision@3, Precision@5, MRR, latency, and tokens saved versus full-tree scans.

## When not to use

Do not use for everyday qmd search (`qmd-usage`), index rebuilding (`refresh_qmd_index.py`), or basic qmd health dry runs (`qmd-efficiency`).

## Criticality

High when testing retrieval recall improvements or modifying search index architectures.

## Source of truth

- `python scripts/benchmarks/benchmark_retrieval.py`
- `python scripts/qmd/validate_qmd_retrieval.py`
- [`supporting/qmd/README.md`](../../../../supporting/qmd/README.md)
- [`supporting/benchmarks/README.md`](../../../../supporting/benchmarks/README.md)

## Isolation

`mutate` because generated evaluation benchmarks land under `results/benchmarks/retrieval/<YYYY-MM-DD>/`. Parent isolates `results` area.

## How to use

1. Run standard retrieval benchmark suite:
   ```bash
   python scripts/benchmarks/benchmark_retrieval.py
   ```
2. Include slow hybrid queries for comparison:
   ```bash
   python scripts/benchmarks/benchmark_retrieval.py --hybrid
   ```
3. Check metrics report at `results/benchmarks/retrieval/<YYYY-MM-DD>/report.md`.

## Dry run

```bash
python scripts/benchmarks/benchmark_retrieval.py --help
python scripts/benchmarks/benchmark_retrieval.py --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Ground-truth query fixtures must not contain sensitive query tokens or production secrets.

## Completion gates

Retrieval benchmark output saved to `results/benchmarks/retrieval/<YYYY-MM-DD>/`. Precision@1 and MRR meet or exceed baseline targets.
