---
doc_kind: result
canonical_id: headroom-dry-run
purpose: [process]
topics: [headroom, tokens]
generated_at_utc: 2026-08-28T18:41:06Z
---

# Headroom compression dry-run

Compress bulky tool dumps locally (no provider call). Compare token savings and whether gold facts survive versus the uncompressed original (direct review).

Headroom `tokens_*` come from its tokenizer. `est_tokens_*` is `chars/4` for comparison with the qmd validator.

## Fixtures

| Fixture | Saved (Headroom tok) | Ratio | Gold in original | Gold after compress | vs direct |
| --- | --- | --- | --- | --- | --- |
| `json_tool_array` | 5901 | 72.2% | 2/2 | 2/2 | 100.0% |
| `build_log` | 0 | 0.0% | 1/1 | 1/1 | 100.0% |
| `grep_hits` | 118 | 5.9% | 2/2 | 2/2 | 100.0% |

## Savings summary

- Mean compression ratio: **26.0%**
- Total Headroom tokens saved: **6019**
- Fixtures with 100% gold-fact survival: **3/3**

## Findings

- `json_tool_array` saved 5901 tokens (72.2%).
- `build_log` saved 0 tokens (0.0%).
- `grep_hits` saved 118 tokens (5.9%).
- This measures compression quality, not Cursor-hosted billing. Provider savings require traffic through the proxy or MCP compress.
- Windows may log a Magika/ONNX detect-backend warning; compression still ran.
