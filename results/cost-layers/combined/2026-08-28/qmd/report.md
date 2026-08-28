---
doc_kind: result
canonical_id: qmd-dry-run
purpose: [qmd]
topics: [qmd, retrieval, tokens]
generated_at_utc: 2026-08-28T18:29:40Z
---

# qmd dry-run validation

End-to-end check of collection health, typical agent lookups, and theoretical token savings versus walking Markdown trees.

Token estimate: `chars / 4` (GPT-family heuristic, not a billed tokenizer).

## Health

| Check | Result | Detail |
| --- | --- | --- |
| `qmd_on_path` | pass | C:\Users\rober\tools\node\node.exe C:\Users\rober\tools\node\node_modules\@tobilu\qmd\bin\qmd |
| `collections_match` | pass | found=['routing', 'docs', 'projects', 'references', 'research', 'supporting', 'ai-tooling', 'scripts', 'actionable', 'results'] expected=['actionable', 'ai-tooling', 'docs', 'proje |
| `exclusions_not_indexed` | pass | leaked=[] |
| `root_agents_not_indexed` | pass | root AGENTS.md is hop-1 context, not a qmd collection |
| `ambiguity_gate_unindexed` | pass | phrase lives in root AGENTS.md plus intentional cites (isolation/skills); unexpected hits=[] |
| `ampersand_query_pitfall` | pass | search 'MITRE ATT&CK' hits=0; 'mitre attack' hits=5 (ampersand is a BM25 trap) |
| `docs_index_current` | FAIL | on_disk=['docs/AGENTS.md', 'docs/agent-session-security.md', 'docs/anti-slop.md', 'docs/standards/AGENTS.md', 'docs/standards/context-management.md', 'docs/standards/wiki-harness-t |

## Corpus baselines

- Indexed collections: **141521** tokens across 157 files
- Always-allowed hop (root + routing + area-map): **5524** tokens
- All nested `AGENTS.md` (Cursor currently injects these): **11342** tokens
- Excluded trees (`change-history/`, `scratch/`): **488** tokens not in the index
- Root `AGENTS.md` + `README.md` (unindexed): **4159** tokens

## Lookups

Each fixture is a realistic agent discovery question. BM25 is `qmd search`. Structured is agent-authored `lex:`/`vec:` with `--no-rerank`. Hybrid is the documented bare `qmd query` (expansion + rerank).

| Fixture | Mode | Hits | Expected in top-N | Gold vs direct | Elapsed | Fetched tok | vs collection |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `session-security` | bm25 | 5 | yes | 100.0% | 0.558s | 1596 | 83.0% |
| `session-security` | structured | 2 | yes | 100.0% | 27.616s | 843 | 91.0% |
| `cloudflare-patterns` | bm25 | 5 | yes | 0.0% | 0.543s | 0 | 100.0% |
| `cloudflare-patterns` | structured | 2 | yes | 0.0% | 18.267s | 8514 | 41.8% |
| `a2a-budget` | bm25 | 5 | yes | 100.0% | 0.544s | 1113 | 98.7% |
| `a2a-budget` | structured | 2 | NO | 0.0% | 20.147s | 1087 | 98.8% |
| `qmd-setup` | bm25 | 3 | yes | 100.0% | 0.524s | 3208 | 78.1% |
| `qmd-setup` | structured | 2 | yes | 100.0% | 17.189s | 2538 | 82.6% |
| `change-history-script` | bm25 | 5 | yes | 100.0% | 0.575s | 5286 | — |
| `change-history-script` | structured | 2 | yes | 100.0% | 17.524s | 7222 | — |
| `mitre-attack` | bm25 | 4 | yes | 0.0% | 0.669s | 8833 | -91.6% |
| `mitre-attack` | structured | 2 | NO | 0.0% | 18.314s | 4344 | 5.8% |
| `status-buckets` | bm25 | 2 | yes | 100.0% | 0.819s | 4077 | — |
| `status-buckets` | structured | 2 | yes | 100.0% | 17.747s | 1662 | — |
| `retrieval-conventions` | bm25 | 3 | yes | 100.0% | 0.567s | 3258 | 77.7% |
| `retrieval-conventions` | structured | 2 | yes | 100.0% | 17.454s | 1429 | 90.2% |

## Theoretical savings (BM25 + fetch unique top hits)

Compared with reading the hinted collection (or the full indexed corpus when no hint).

- Mean tokens loaded via qmd fetch: **3421**
- Mean tokens if the agent walked the target collection: **24455**
- Mean savings vs collection walk: **57.6%**
- Full indexed corpus: **141521** tokens; mean qmd fetch is **2.42%** of that

## Findings

- Health failures: docs_index_current.
- `cloudflare-patterns` / bm25 missed gold facts vs direct review: ['npx wrangler pages deploy'].
- `cloudflare-patterns` / structured missed gold facts vs direct review: ['npx wrangler pages deploy'].
- `a2a-budget` / structured missed expected ['ai-tooling/a2a/interaction-protocol.md']; top hits: docs/agent-session-security.md, ai-tooling/a2a/AGENTS.md.
- `a2a-budget` / structured missed gold facts vs direct review: ['No destructive delegation'].
- `mitre-attack` / bm25 missed gold facts vs direct review: ['Advisory only — not session instructions'].
- `mitre-attack` / structured missed expected ['references/mitre-attack']; top hits: routing/AGENTS.md, docs/standards/wiki-harness-template.md.
- `mitre-attack` / structured missed gold facts vs direct review: ['Advisory only — not session instructions'].
- BM25 lookups averaged 0.6s.
- Root `AGENTS.md` is not in any collection; Critical rules stay in the hop, not in qmd.
- Token savings assume the agent fetches unique top-N files instead of reading the whole area tree. Snippets alone are cheaper still, but qmd skill/docs say not to answer from snippets.
