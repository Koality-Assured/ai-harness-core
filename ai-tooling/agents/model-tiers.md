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

Product names in the table are the human-facing map. Host picker IDs change — record those on the host A2A card.

New agents get `model_tier: standard` unless the human specifies otherwise.

## Related

| Doc | Role |
| --- | --- |
| [`AGENTS.md`](./AGENTS.md) | Agent authoring rules |
| [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md) | Host cards (`type: host`) |
| [`../skills/isolate-work/SKILL.md`](../skills/isolate-work/SKILL.md) | Isolate then spawn |
