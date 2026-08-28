---
doc_kind: result
canonical_id: ast-grep-dry-run
purpose: [process]
topics: [ast-grep, qmd, headroom, tokens]
generated_at_utc: 2026-08-28T18:28:06Z
---

# ast-grep cost-layer dry-run

Precision retrieval (outline/kind facts vs full files) and Headroom survival of structural facts. Not a third compressor.

Token estimate is chars/4, same as the other cost-layer validators.

## CLI health

- ast-grep: **ast-grep 0.45.1**
- sgconfig.yml: **True**
- scan: **True** (46 matches in sample paths)

## Precision retrieval

| Sample | Facts | Full tok | Fact tok | Saved | % |
| --- | --- | --- | --- | --- | --- |
| `python-script` | 11 | 2743 | 172 | 2571 | 93.7% |
| `agent-card-yaml` | 4 | 599 | 57 | 542 | 90.5% |
| `skill-frontmatter` | 3 | 666 | 34 | 632 | 94.9% |

## Headroom structural oracle

- Fixture `ast_structural_survival`: gold 8/8 after compress; Headroom saved 5983 tokens (71.3%).

## Findings

- CLI ok: ast-grep 0.45.1 ; scan matched 46 nodes.
- `python-script` saved 2571 est tokens (93.7% vs full file).
- `agent-card-yaml` saved 542 est tokens (90.5% vs full file).
- `skill-frontmatter` saved 632 est tokens (94.9% vs full file).
- Headroom kept 8 structural facts; saved 5983 tokens.
