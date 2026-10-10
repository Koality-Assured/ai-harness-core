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

| Tier | Reasoning | Google (Antigravity) | OpenAI (Codex / ChatGPT) | Anthropic (Claude Code) | Cursor | Local (Ollama) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `local` | mid / high | — | — | — | — | Qwen 2.5 Coder 14B / 7B |
| `fast` | low | Gemini Flash Lite | GPT-4o mini | Claude 3.5 Haiku | Composer 2.5 | Qwen 2.5 Coder 7B |
| `standard` | mid | Gemini 3.8 Flash | GPT 6.0 Luna | Claude 5.5 Sonnet | Cursor Grok 4.7 (High, 256k) | Qwen 2.5 Coder 14B |
| `high` | high | Gemini 3.8 Flash (High) | GPT Terra | Claude 5.5 Sonnet (Thinking) | Cursor Grok 4.7 (High, 500k Fast) | Qwen 2.5 Coder 32B |
| `max` | max | Gemini 3.8 Pro | GPT Sol | Claude 5.5 Opus | Cursor Grok 4.7 (Extra High, 500k Fast) / Claude 5.5 Opus | DeepSeek-R1 (quant) |

### Active model generations & pricing dynamics
- **OpenAI (Codex / ChatGPT)**: Retired older GPT 5.6 Luna in favor of **GPT 6.0 Luna** as the standard workhorse. High and max tiers utilize GPT Terra and GPT Sol.
- **Anthropic (Claude)**: **Claude 5.5 Sonnet** is now substantially cheaper across prompt caching and token generation, establishing it as the standard workhorse for both standalone Claude sessions and Antigravity Ultra secondary deferral. **Claude 5.5 Opus** anchors the max capability tier.
- **Cursor**: Anchors `fast` inline edits with **Composer 2.5**. Standard tier configures **Cursor Grok 4.7 on High with 256k context**; high tier configures **Cursor Grok 4.7 on High with 500k context in Fast Mode**; max tier utilizes **Cursor Grok 4.7 on Extra High with 500k context in Fast Mode** (or Claude 5.5 Opus).
- **Google**: Standardized on **Gemini 3.8 Flash** (`standard`), **Gemini 3.8 Flash (High)** (`high`), and **Gemini 3.8 Pro** (`max`). Older 3.7 / 3.6 / 3.1 models are retired.


## Platform-native selection

The orchestrator selects the column for the **current host** and never defaults to another vendor's model on a host that has first-party models. Cursor → Cursor models (never default GPT/Claude on Cursor). ChatGPT/Codex → GPT models. Antigravity → Gemini models.

**Antigravity Ultra secondary allocation exception**: On Antigravity hosts with a paid Ultra subscription, a dedicated rolling allocation (typically 5 hours) is provided for secondary models (Claude / GPT) that operates on an independent quota meter from native Gemini. Because this capacity is strictly "use-it-or-lose-it" and resets periodically, orchestrators SHOULD actively route eligible high-leverage tasks (complex concurrency, rigid invariant refactors, security audits, AST/regex parsing, and dense RFCs) to Claude while the window is active. If the secondary window is exhausted (429 or active cooldown), orchestrators immediately fall back to Gemini 3.8 Flash (High) / Gemini 3.8 Pro with transparent human notice. See [`../../GEMINI.md`](../../GEMINI.md) and [`../../docs/guidance/quota-and-pacing.md`](../../docs/guidance/quota-and-pacing.md).

Product names in the table are the human-facing map. Host picker IDs change and are host-local operational data; do not persist them in cross-host canonical contracts.

New agents get `model_tier: standard` unless the human specifies otherwise.

## Local model deferral tier

When standing up host-local inference (via Ollama or `llama-server` on `127.0.0.1:11434` / `8080`), frontier agents may defer mechanical and high-volume operations (linter fixes, unit test boilerplate, AST rewrites, log summarization) to the `local` tier.
- **Zero Cloud Spend**: $0.00 marginal token cost.
- **Quota Preservation**: Eliminates 429 rate limit risk on cloud providers by routing leaf operations off the cloud network.
- **Execution**: Invoked directly via `harness chat --provider local -q "..."` or subagent delegation. Detailed architecture: [`../../research/local-models/deferral-architecture.md`](../../research/local-models/deferral-architecture.md).

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

