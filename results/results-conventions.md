---
doc_kind: process
canonical_id: results-conventions
purpose: [process]
rank: medium
topics: [agents, results]
rag_keywords: [results, family, date layout, cost-layers, reports]
---

# Results conventions

## Purpose

Keep agent-generated artifacts findable without turning `results/` into a durable source of truth.

## Layout

Every run uses `results/<family>/<topic-or-slug>/<YYYY-MM-DD>/`. Typed families insert `<type>` before the topic.

| Family | Path |
| --- | --- |
| reviews | `results/reviews/<topic>/<date>/` |
| research | `results/research/<topic>/<date>/` |
| diagrams | `results/diagrams/<topic>/<date>/` — or beside the report they attach to |
| threat-model | `results/threat-model/<topic>/<date>/` |
| reports | `results/reports/<type>/<topic>/<date>/` |
| as-code | `results/as-code/<type>/<topic>/<date>/` |
| cost-layers | `results/cost-layers/<slug>/<date>/` |

Report `<type>` values: `executive`, `proposal`, `corpus-draft`, `guidance-draft`, `code-review`, `framework-map`.

## Cost-layer dry-runs

Write validation output under `results/cost-layers/<slug>/<YYYY-MM-DD>/` (for example `combined`, `combined-ast-grep`, `qmd-dry-run`). Do not use top-level `results/cost-layer-dry-run-*` or `results/qmd-dry-run-*`.

## Rules

- Prefer Markdown reports in-git; binaries may stay gitignored.
- Empty family folders may keep a `.gitkeep` so the tree exists in git.
- Promote reusable lessons to `docs/` or `supporting/`; do not treat results as policy.
- Agents: open one run folder only — do not bulk-load `results/`.
- Area rules: [`AGENTS.md`](./AGENTS.md).

## Related

| Topic | Where |
| --- | --- |
| Results index | [`README.md`](./README.md) |
| qmd / Headroom / ast-grep notes | [`../supporting/qmd/query-pattern.md`](../supporting/qmd/query-pattern.md), [`../supporting/headroom/proxy-mcp.md`](../supporting/headroom/proxy-mcp.md), [`../supporting/ast-grep/precision-retrieval.md`](../supporting/ast-grep/precision-retrieval.md) |
