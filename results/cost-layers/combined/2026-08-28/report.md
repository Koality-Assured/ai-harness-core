---
doc_kind: result
canonical_id: cost-layer-dry-run
purpose: [process]
topics: [qmd, headroom, ast-grep, prompt-caching, webfetch, tokens]
generated_at_utc: 2026-08-28T18:40:44Z
---

# Cost-layer dry-run (qmd + Headroom + ast-grep + prompt-caching + webfetch)

Combined validation of retrieval context savings (qmd), tool-dump compression (Headroom), ast-grep precision retrieval, prompt cache prefix invariance, and local web distillation token reduction versus uncompressed originals.

## How to re-run

```bash
python scripts/cost-layers/validate_cost_layers.py
# default: results/cost-layers/combined/<YYYY-MM-DD>/
```

Add `--hybrid` to include slow `qmd query`. Flags: `--skip-ast-grep`, `--skip-prompt-caching`, `--skip-webfetch`. Reports: `qmd/report.md`, `headroom/report.md`, `ast-grep/report.md`, `prompt-caching/report.md`.

## qmd

- Exit: **skipped**
- Health failures: []

## Headroom

- Exit: **0**
- Failed fixtures: []

## ast-grep

- Exit: **0**
- Failed fixtures: []

## Prompt Cache Invariance

- Exit: **0**
- Violations: 0
- Audited files: 22

## Web Distillation (local_webfetch)

- Exit: **0**
- Extractor: `trafilatura`
- Token reduction: **77.2%** (Saved 448 tokens)
- Gold fact accuracy: **100.0%** (4/4)

## Combined findings

- (headroom) `json_tool_array` saved 5901 tokens (72.2%).
- (headroom) `build_log` saved 0 tokens (0.0%).
- (headroom) `grep_hits` saved 118 tokens (5.9%).
- (headroom) This measures compression quality, not Cursor-hosted billing. Provider savings require traffic through the proxy or MCP compress.
- (headroom) Windows may log a Magika/ONNX detect-backend warning; compression still ran.
- (ast-grep) CLI ok: ast-grep 0.45.1 ; scan matched 46 nodes.
- (ast-grep) `python-script` saved 2571 est tokens (93.7% vs full file).
- (ast-grep) `agent-card-yaml` saved 542 est tokens (90.5% vs full file).
- (ast-grep) `skill-frontmatter` saved 632 est tokens (94.9% vs full file).
- (ast-grep) Headroom kept 8 structural facts; saved 5983 tokens.
- (prompt-caching) All prompt definitions maintain static byte prefix stability.
- (webfetch) Distillation achieved 77.2% token reduction with 100.0% gold fact retention using trafilatura.

## Patterns / adjustments

- BM25 `qmd search` is the Critical discovery path; structured `lex`/`vec` without rerank can miss the owning file (gold facts then fail vs direct review).
- Path hits are not enough — gold-fact checks compare fetched file text to a direct read of the expected paths.
- Vague queries like “where do Cloudflare tool patterns live” can rank `supporting/AGENTS.md` instead of `supporting/cloudflare/pages-wrangler.md`. Distinctive tokens from the owning page (`wrangler pages deploy`) hit it; extra words not in the file (`tool`) AND-zero BM25.
- Headroom JSON arrays compress well (~70%+). Search-style dumps may drop path-only markers; keep gold facts in match text. Short compile listings may not trigger the log compressor.
- Headroom savings do not apply to hosts that do not route through the proxy unless BYOK, custom base URL, or MCP compress.
- ast-grep is precision retrieval + a structural oracle, not a third compressor. YAML frontmatter uses `-k block_mapping_pair` (JSON uses `-k pair`).
- Prompt cache invariance ensures system prompt headers remain byte-stable across calls, preserving provider KV-cache hits (saving 90% input costs).
- Local web distillation purifies raw external HTML into clean Markdown, neutralizing hidden prompt injections and stripping boilerplate (navbars, tracking pixels, ads).
- Re-index after new Markdown or qmd health `docs_index_current` fails.
- Root “Ambiguity gate” cited from isolation docs/skills is expected, not index leakage.
