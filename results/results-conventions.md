---
doc_kind: process
canonical_id: results-conventions
purpose: [process]
rank: medium
topics: [agents, results]
rag_keywords: [results, family, date layout, cost-layers, reports, finished-deliverables]
---

# Results conventions

## Purpose

`results/` holds finished work a human might hand to someone else: reports, HTML pages, images, diagrams, threat-model packages, as-code packages, dated cost-layer measurement reports, and finished research dossiers.

Interim scaffolds, generator previews, experiments, and review working notes belong in `scratch/` (or back to the orchestrator). Reusable policy belongs in `docs/`, `supporting/`, skills, or `AGENT.md`. `results/` is not policy source of truth.

## Layout

Every run uses `results/<family>/<topic-or-slug>/<YYYY-MM-DD>/`. Typed families insert `<type>` before the topic.

| Family | Path |
| --- | --- |
| reports | `results/reports/<type>/<topic>/<date>/` |
| research | `results/research/<topic>/<date>/` |
| diagrams | `results/diagrams/<topic>/<date>/` — or beside the report they attach to |
| threat-model | `results/threat-model/<topic>/<date>/` |
| as-code | `results/as-code/<type>/<topic>/<date>/` |
| cost-layers | `results/cost-layers/<slug>/<date>/` |

Report `<type>` values: `executive`, `proposal`, `corpus-draft`, `guidance-draft`, `code-review`, `framework-map`.

Do not invent new top-level run shapes such as `results/headroom-dry-run`, `results/ast-grep-dry-run`, or `results/scaffolded-repos`. Cost-layer output goes under `results/cost-layers/<slug>/<YYYY-MM-DD>/`. Public-repo generator previews and other scaffolds go in `scratch/`.

## Retired: reviews

Antagonistic reviews are not a durable results family. Do not keep completed reviews in git. Ranked findings go back to the orchestrator. Unique durable knowledge is promoted to the owning source area (`docs/`, `supporting/`, skills, `AGENT.md`) only when it is not already there.

Do not file antagonistic reviews under `results/reviews/` as a permanent artifact. The empty `results/reviews/` folder (`.gitkeep` only) is a retired marker so the name is not reused as a family.

## Cost-layer measurement reports

Write validation output under `results/cost-layers/<slug>/<YYYY-MM-DD>/` (for example `combined`, `combined-ast-grep`, `qmd-dry-run`). Do not use top-level `results/headroom-dry-run`, `results/ast-grep-dry-run`, `results/cost-layer-dry-run-*`, or `results/qmd-dry-run-*`. Do not leave an undated sibling (`report.md`, `summary.json`, `qmd/`, `headroom/`, `ast-grep/`) next to a dated run.

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
