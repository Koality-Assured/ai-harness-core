---
doc_kind: result
canonical_id: prompt-caching-invariance
purpose: [process]
topics: [cost-layers, prompt-caching, kv-cache, validation]
generated_at_utc: 2026-08-28T18:27:54Z
---

# Prompt Cache Invariance Validation

Validates that system prompt prefixes and agent definitions exhibit static byte stability at their heads without volatile timestamps, random session UUIDs, or dynamic environment paths that invalidate provider KV-caches (Anthropic prompt caching, OpenAI prompt caching, Gemini context caching).

## Summary

- Status: **PASS**
- Total prompt definitions audited: **22**
- Violations detected: **0**
- Minimum static prefix requirement: **512 bytes**

## Audited Prompt Definitions

| File | Size (Bytes) | Est. Tokens | Static Prefix Stability | Violations |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | 14578 | 3622 | PASS | 0 |
| `ai-tooling/agents/ai-tooling-ops/AGENT.md` | 2398 | 599 | PASS | 0 |
| `ai-tooling/agents/artifact-agent/AGENT.md` | 3655 | 912 | PASS | 0 |
| `ai-tooling/agents/as-code-agent/AGENT.md` | 2007 | 501 | PASS | 0 |
| `ai-tooling/agents/chat-collab-agent/AGENT.md` | 4247 | 1061 | PASS | 0 |
| `ai-tooling/agents/community-analyst/AGENT.md` | 4049 | 1011 | PASS | 0 |
| `ai-tooling/agents/detailed-activity/AGENT.md` | 4350 | 1085 | PASS | 0 |
| `ai-tooling/agents/docs-collab-agent/AGENT.md` | 4785 | 1196 | PASS | 0 |
| `ai-tooling/agents/documentation-ops/AGENT.md` | 2792 | 696 | PASS | 0 |
| `ai-tooling/agents/git-fast-operator/AGENT.md` | 1961 | 489 | PASS | 0 |
| `ai-tooling/agents/github-ops/AGENT.md` | 2531 | 631 | PASS | 0 |
| `ai-tooling/agents/google-suite-admin/AGENT.md` | 3128 | 782 | PASS | 0 |
| `ai-tooling/agents/google-suite-operator/AGENT.md` | 3638 | 909 | PASS | 0 |
| `ai-tooling/agents/memory-operator/AGENT.md` | 3038 | 759 | PASS | 0 |
| `ai-tooling/agents/public-llm-admin/AGENT.md` | 3313 | 828 | PASS | 0 |
| `ai-tooling/agents/qmd-ops/AGENT.md` | 2160 | 540 | PASS | 0 |
| `ai-tooling/agents/reference-ops/AGENT.md` | 2665 | 665 | PASS | 0 |
| `ai-tooling/agents/repo-sync-ops/AGENT.md` | 3414 | 853 | PASS | 0 |
| `ai-tooling/agents/router/AGENT.md` | 10439 | 2605 | PASS | 0 |
| `ai-tooling/agents/router-maintenance/AGENT.md` | 2708 | 676 | PASS | 0 |
| `ai-tooling/agents/script-ops/AGENT.md` | 1793 | 448 | PASS | 0 |
| `routing/AGENTS.md` | 3888 | 964 | PASS | 0 |

## Findings & Invariance Violations

- All prompt definitions maintain byte-stable prefix headers.
- No dynamic timestamps, nonces, or user environment paths detected in prompt heads.
- KV-cache hit efficiency preserved across provider routing boundaries.
