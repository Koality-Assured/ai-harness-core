---
doc_kind: standard
canonical_id: context-management
purpose: [standard, caching, context, architecture]
rank: critical
topics: [prompt-caching, context-hierarchy, anthropic, openai, gemini]
---

# Context management and prompt caching (generalized)

## Purpose

Define the normative context hierarchy, prompt caching architecture, provider breakpoint placement rules, and anti-patterns required to maximize prompt cache hit rates (target: 92–98%) and minimize operational token costs across multi-turn agent sessions.

## Scope

All agent harnesses, orchestrators, subagents, tools, and prompts operating across frontier LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini).

---

## The 5-Tier Ordered Context Hierarchy

Frontier LLM prompt caching relies strictly on exact byte-for-byte prefix matching starting from token 0. Context payloads MUST be structured into five discrete tiers ordered from most static to most volatile.

```text
┌──────────────────────────────────────────────────────────────────┐
│ Tier 1: Static Base Prefix (Universal MUSTs, Schemas, Catalogs) │ ◄── Breakpoint 1
├──────────────────────────────────────────────────────────────────┤
│ Tier 2: Static Skill & Specialist Context                        │
├──────────────────────────────────────────────────────────────────┤
│ Tier 3: Monotonic Conversation History (Turns 1 to N-1)          │ ◄── Breakpoint 2
├──────────────────────────────────────────────────────────────────┤
│ Tier 4: Ephemeral Turn Context (Nearest JIT AGENTS.md)           │ ◄── Dynamic Tail
├──────────────────────────────────────────────────────────────────┤
│ Tier 5: Dynamic Turn Delta (User Prompt, Tool Outputs)           │ ◄── Volatile Tail
└──────────────────────────────────────────────────────────────────┘
```

### Tier 1: Static Base Prefix

- **Content**: Universal invariant instructions, system guardrails, immutable tool schemas and definitions, and global routing catalogs (`skill-dispatch.md`, core agent cards).
- **Volatility**: 100% static across all sessions and agent instances.
- **Caching Role**: **Provider Breakpoint 1**. Serves as the immutable root prefix shared across all sessions.

### Tier 2: Static Skill & Specialist Context

- **Content**: Specialist agent definition (`AGENT.md`), active skill instructions (`SKILL.md`), specialist tool schemas, and declarative constraints.
- **Volatility**: Static throughout the entire lifecycle of a specialist subagent invocation.
- **Caching Role**: Loaded cleanly upon specialist spawn. Preserves the byte prefix established in Tier 1 for the duration of the specialist task.

### Tier 3: Monotonic Conversation History

- **Content**: Append-only sequence of historical turns (Turns 1 to N-1), including user messages, assistant responses, and executed tool results.
- **Prefix Invariance**: Monotonically append-only. Past turns MUST NOT be modified, re-ordered, truncated, or rewritten in place.
- **Caching Role**: **Provider Breakpoint 2** (placed on turn N-1 / penultimate message block). Enables cumulative cache reuse across successive conversation turns.

### Tier 4: Ephemeral Turn Context (JIT Area Rules)

- **Content**: Nearest folder-level `AGENTS.md` and scoped local area constraints loaded strictly Just-In-Time (JIT) upon entering a repository directory.
- **Tail Placement Principle (Resolving CRIT-03)**: JIT folder rules MUST sit in the dynamic turn tail (after Tier 3 history) rather than ahead of conversation history.
- **Rationale**: If folder rules were placed ahead of conversation history, navigating between repository areas (e.g. `supporting/` → `projects/` → `docs/`) would alter upstream byte sequences and invalidate the cached prefix for the entire conversation history (Turns 1..N-1), degrading cache hit rates from >95% to <20%. Placing JIT rules in Tier 4 guarantees directory switches never invalidate historical prefix caches.

### Tier 5: Dynamic Turn Delta

- **Content**: Latest user input prompt, active tool call invocations, current execution results, compiler logs, and git diffs.
- **Volatility**: Volatile per turn; discarded or promoted into Tier 3 history upon turn completion.
- **Compression**: Bulky dumps (build output, large files, JSON structures) MUST be compressed prior to injection using the Headroom compression proxy, `ast-grep` symbol outlines, or `qmd` BM25 snippets.
- **Sectional & Heading Subtree Extraction**: When ingesting supporting documentation, standards, or reference corpuses into active turn context (Tier 4/5), agents MUST extract only the relevant heading subtree or line-bounded range (`StartLine`/`EndLine`). Ingesting full documents when only a single control or procedure is needed bloats turn context, accelerates token consumption, and introduces noise.

### Context Hierarchy Summary

| Tier | Layer Name | Content Ingestion | Volatility | Caching Classification | Invalidation Scope |
| --- | --- | --- | --- | --- | --- |
| **Tier 1** | Static Base Prefix | Universal MUSTs, system prompt, tool schemas, global catalogs | Immutable | **Breakpoint 1** (Global) | Repository/tool updates |
| **Tier 2** | Static Skill Context | Specialist `AGENT.md`, active `SKILL.md`, domain schemas | Immutable (Session) | Specialist Base Prefix | Specialist agent spawn |
| **Tier 3** | Monotonic History | Turns 1 to N-1 (user/assistant/tool messages) | Append-Only | **Breakpoint 2** (Penultimate Turn) | Monotonically extended |
| **Tier 4** | Ephemeral Turn Context | Nearest JIT `AGENTS.md` loaded on area entry | Turn-Scoped Tail | Ephemeral (Uncached) | Current turn only (CRIT-03 safe) |
| **Tier 5** | Dynamic Turn Delta | Latest user prompt, compressed tool execution outputs | Volatile | Uncached / Compressed | Flushed each turn |

---

## Multi-Model Caching Mechanics (Resolving HIGH-01)

Frontier providers implement distinct prompt caching architectures with divergent token thresholds, breakpoint limits, and lifecycles.

### Provider Comparison Matrix

| Provider & Model | Cache Mechanism | Minimum Threshold | Alignment Unit | Breakpoint Limit | TTL Lifecycle | Economic Benefit |
| --- | --- | --- | --- | --- | --- | --- |
| **Anthropic Claude 3.5 / 3.7** | Explicit `cache_control` | 1,024 / 2,048 tokens | Exact token | 4 blocks max | 5-minute rolling TTL | ~90% read discount (+25% write) |
| **OpenAI GPT-4o / o1 / o3** | Automatic Prefix | 1,024 tokens | 128-token blocks | Implicit (Unlimited) | 5–10 min dynamic TTL | 50% read discount (0% write surcharge) |
| **Google Gemini 1.5 / 2.0 / 3.0** | Explicit Context Caching | 32,768 (32k) tokens | Token block | 1 resource per call | Configurable (Default 1 hour) | ~75–80% input discount |

---

### Anthropic Claude 3.5 / 3.7 Mechanics

- **Hard Breakpoint Cap**: Anthropic enforces a strict maximum of **4 `cache_control` blocks** (`{"type": "ephemeral"}`) per API request. Attempting to specify 5 or more `cache_control` blocks triggers an immediate unrecoverable `400 Invalid Request` API error.
- **Normative 2-Breakpoint Policy**: Harnesses MUST adhere to a standard 2-breakpoint allocation:
  - **Breakpoint 1**: Placed at the end of Tier 1 / Tier 2 (Static System Instructions + Tool Definitions).
  - **Breakpoint 2**: Placed at the penultimate conversation turn (Turn N-1 in Tier 3).
  - **Breakpoints 3 & 4 (Reserved)**: Reserved exclusively for large, persistent reference corpuses (>10k tokens) or multi-agent handoff state. Never place breakpoints on ephemeral Tier 4/5 turn deltas.
- **TTL and Eviction Lifecycle**: Cached prefixes have a 5-minute time-to-live (TTL). Every cache hit resets the 5-minute timer.
- **Keepalive Anti-Pattern**: Do NOT implement aggressive polling or keepalive ping loops (e.g. pinging every 4.5 minutes) across idle subagents. Synthetic pings waste tokens, consume rate limits, and violate concurrency rules. Allow subagent caches to expire naturally once tasks complete.
- **Threshold**: Minimum cacheable prompt length is 1,024 tokens for Claude 3.5 Sonnet / 3.7 Sonnet, and 2,048 tokens for Claude 3.5 Haiku. Prompts below these thresholds bypass caching entirely.

---

### OpenAI GPT-4o / o1 / o3 Mechanics

- **Automatic Prefix Caching**: OpenAI models automatically cache matching prompt prefixes from token 0 without explicit API markers or `cache_control` headers.
- **Minimum Threshold**: Prompts must contain at least **1,024 tokens** in the common prefix to qualify for caching. Prompts below 1,024 tokens receive 0% cache benefit.
- **128-Token Increment Alignment**: Prefix caching operates in **128-token increments**. The cached prefix length is rounded down to the nearest multiple of 128 tokens; the remainder is evaluated as uncached delta until it crosses the next 128-token boundary.
- **Byte Prefix Sensitivity**: Even a single byte alteration in Tier 1 (such as an unsorted dictionary or dynamic timestamp) invalidates caching for the entire prompt.

---

### Google Gemini Context Caching API

- **Explicit Cache Resources**: Gemini utilizes the Context Caching API (`CachedContent` objects) where shared context is explicitly uploaded and assigned a cache resource identifier.
- **Minimum Threshold**: Requires a minimum of **32,768 (32k) tokens**. Sub-32k prompts cannot create explicit cache resources.
- **Corpus-Scale Use Case**: Gemini caching is designed for massive static context: entire repository codebases, complete architectural specifications, or voluminous reference manuals placed in Tier 1.
- **Configurable TTL**: Cache resources feature an explicit TTL (default 1 hour), which can be refreshed or extended programmatically.

---

## Cache Invalidation Anti-Patterns and Prohibitions

The following anti-patterns cause prefix divergence, cache eviction, or security vulnerabilities and are strictly prohibited.

### 1. Dynamic Timestamps in Prefix Prompts

- **Failure**: Injecting timestamps (e.g. `Current time: 2026-08-24T09:25:51`) into Tier 1 or Tier 2 changes the byte prefix on every request, causing a 100% cache miss.
- **Rule**: System prompts and static prefixes MUST NOT contain dynamic timestamps or UUIDs.
- **Remediation**: Pass timestamps exclusively in Tier 5 (Turn Delta) or allow agents to query time via dedicated on-demand tooling.

### 2. Un-Ordered JSON Dictionaries and Schemas

- **Failure**: Standard JSON serialization without key sorting produces non-deterministic key ordering across Python runtimes, generating byte mismatches.
- **Rule**: All tool schemas, configuration objects, and structured catalogs in Tiers 1–3 MUST be serialized with deterministic key ordering.
- **Remediation**: Enforce `json.dumps(obj, sort_keys=True)` across all schema generators and catalog compilers.

### 3. JIT Area Rule Ingestion Ahead of History (CRIT-03)

- **Failure**: Injecting directory-level `AGENTS.md` rules into Tier 2 or ahead of conversation history breaks byte prefix matching whenever an agent switches directories, invalidating the cache for all prior turns (1..N-1).
- **Rule**: JIT area rules MUST NEVER be placed upstream of Monotonic Conversation History.
- **Remediation**: Inject JIT area rules strictly into Tier 4 (dynamic turn tail), or spawn an isolated subagent for folder-specific mutations.

### 4. In-Place Conversation History Rewriting

- **Failure**: Modifying, summarizing, or deleting earlier conversation turns changes historical byte offsets and invalidates Breakpoint 2.
- **Rule**: Conversation history (Tier 3) MUST be monotonically append-only.
- **Remediation**: When approaching token window limits, do not rewrite past turns in place. Instead, perform a clean session compaction into a structured checkpoint and spawn a new session with clean Tier 1/2 prefixes.

### 5. Base64 Execution and Code Obfuscation (CRIT-01)

- **Failure**: Executing Base64-encoded payloads via dynamic eval/exec (`python -c "import base64; exec(...)"`) obfuscates execution from AST security linters, defeats audit trails, and risks prompt injection execution.
- **Rule**: Base64 dynamic execution patterns are strictly banned.
- **Remediation**: Write explicit, reviewable Python scripts into `scratch/` and execute them via standard CLI invocations.

### 6. Breakpoint Overuse and Churn (Anthropic)

- **Failure**: Setting `cache_control` markers on ephemeral tool outputs or every individual message exhausts the 4-breakpoint limit and triggers API errors.
- **Rule**: Never exceed 2 active breakpoints in standard operating loops (Tier 1/2 prefix and Tier 3 turn N-1).

---

## Verification and Enforcement

1. **Automated Cache Validation**: Agent harnesses SHOULD verify cache hit rates using `python scripts/cost-layers/validate_cost_layers.py`.
2. **Provider Telemetry Monitoring**: Monitor API response headers:
   - Anthropic: `cache_creation_input_tokens` vs. `cache_read_input_tokens`.
   - OpenAI: `usage.prompt_tokens_details.cached_tokens`.
   - Gemini: `cached_content_token_count`.
3. **AST Linting**: `ast-grep` rules enforce deterministic JSON serialization and ban Base64 execution patterns across all harness scripts.

---

## Related Standards and References

- AI Development Security: [`ai-development-security.md`](./ai-development-security.md)
- Agent Session Security: [`../agent-session-security.md`](../agent-session-security.md)
- Data Protection: [`data-protection.md`](./data-protection.md)
- Context & Caching Research: [`../../research/agent-harnesses/context-and-prompt-caching.md`](../../research/agent-harnesses/context-and-prompt-caching.md)
- Cost Layers Infrastructure: [`../../supporting/headroom/`](../../supporting/headroom/), [`../../supporting/ast-grep/`](../../supporting/ast-grep/), [`../../supporting/qmd/`](../../supporting/qmd/)
