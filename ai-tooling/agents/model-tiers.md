---
doc_kind: process
canonical_id: agent-model-tiers
purpose: [process]
rank: high
topics: [agents]
rag_keywords: [model_tier, fast, standard, high, max, platform-native, host]
---

# Agent model tiers

Orchestrators pick a reasoning tier and a **platform-native** model when spawning specialists. Default is **standard** unless the human specified another tier.

## Tiers

| Tier | Reasoning | Host examples |
| --- | --- | --- |
| `fast` | low | cheapest fastest model on that host |
| `standard` | mid | GPT Luna; Cursor Grok 4.5; Gemini 3.7 Flash |
| `high` | high | GPT Terra; Cursor Grok 4.6; Gemini 3.7 Flash |
| `max` | max | GPT Sol; Cursor Grok 4.6; Gemini 3.1 Pro |

## Platform-native selection

The orchestrator selects the column for the **current host** and never defaults to another vendor's model on a host that has first-party models. Cursor → Cursor models (never default GPT/Claude on Cursor). ChatGPT/Codex → GPT models. Antigravity → Gemini models.

Product names in the table are the human-facing map. Host picker IDs change and are host-local operational data; do not persist them in cross-host canonical contracts.

New agents get `model_tier: standard` unless the human specifies otherwise.

## Secondary model quotas and pacing

When using secondary/external models (e.g. Anthropic Claude or OpenAI GPT inside Antigravity) or quota-metered tiers:

1. **Down-tier leaf workers**: Research and inspection subagents (`TypeName: "research"`) MUST use `flash` or `flash_lite` rather than inheriting the parent's expensive model. Reserve the secondary model for top-level orchestration and synthesis.
2. **Execution profiles**: Pacing behavior is governed by quota profiles (`unmetered`, `standard`, `metered_secondary` in [`../../config/harness.config.json`](../../config/harness.config.json)). Enterprise PTUs and Cursor default to `unmetered` (no artificial throttling).
3. **Concurrency windows**: Under `metered_secondary`, limit concurrent active subagents to 1–2.
4. **429 Recovery**: On `RESOURCE_EXHAUSTED` (429), parse the reset window and use the Antigravity `schedule` tool to wait and resume without losing context.

Detailed guidance: [`../../docs/guidance/quota-and-pacing.md`](../../docs/guidance/quota-and-pacing.md).

## Related

| Doc | Role |
| --- | --- |
| [`AGENTS.md`](./AGENTS.md) | Agent authoring rules |
| [`../a2a/interaction-protocol.md`](../a2a/interaction-protocol.md) | A2A delegation and quota-aware tiering |
| [`../../docs/guidance/quota-and-pacing.md`](../../docs/guidance/quota-and-pacing.md) | Quota management & pacing guidance |
| [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md) | Host cards (`type: host`; migration note only) |
| [`../skills/meta/isolate-work/SKILL.md`](../skills/meta/isolate-work/SKILL.md) | Isolate then spawn |

