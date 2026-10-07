---
doc_kind: standard
canonical_id: context-management
purpose: [standard, caching, context, architecture]
rank: critical
topics: [prompt-caching, context-hierarchy, anthropic, openai, gemini]
---

# Context management and prompt caching (generalized)

## Purpose

Define a context hierarchy, prompt-caching practices, provider breakpoint considerations, and anti-patterns for improving cache reuse and managing token costs across multi-turn agent sessions. Measure outcomes against the product’s own workload; cache hit-rate targets are model- and workload-specific.

## Scope

All agent harnesses, orchestrators, subagents, tools, and prompts operating across frontier LLM providers (Anthropic Claude, OpenAI GPT, Google Gemini).

---

## Context organization heuristic

Group context from stable to turn-specific when the host request format permits. This five-part model is a planning heuristic, not a required wire format or a universal cache layout. Providers and APIs define their own matching, breakpoint, retention, and context-order rules; follow those rules for the selected model and endpoint.

```text
┌──────────────────────────────────────────────────────────────────┐
│ Tier 1: Stable Instructions and Schemas                         │
├──────────────────────────────────────────────────────────────────┤
│ Tier 2: Static Skill & Specialist Context                        │
├──────────────────────────────────────────────────────────────────┤
│ Tier 3: Conversation History                                      │
├──────────────────────────────────────────────────────────────────┤
│ Tier 4: Ephemeral Turn Context (Scoped Instructions, if present) │ ◄── Dynamic Tail
├──────────────────────────────────────────────────────────────────┤
│ Tier 5: Dynamic Turn Delta (User Prompt, Tool Outputs)           │ ◄── Volatile Tail
└──────────────────────────────────────────────────────────────────┘
```

### Tier 1: Static Base Prefix

- **Content**: Stable instructions, system guardrails, tool schemas and definitions, and other shared catalogs used by the product.
- **Volatility**: Keep stable across requests that should share a reusable prefix.
- **Caching Role**: May form part of a reusable prefix when the provider and API support it; this does not guarantee a cache hit.

### Tier 2: Static Skill & Specialist Context

- **Content**: Specialist definitions, active skill instructions, tool schemas, and declarative constraints when the host or product uses them.
- **Volatility**: Keep stable during an invocation when practical.
- **Caching Role**: Include in the request position supported by the host. Do not assume a shared prefix or cache boundary across products.

### Tier 3: Monotonic Conversation History

- **Content**: Append-only sequence of historical turns (Turns 1 to N-1), including user messages, assistant responses, and executed tool results.
- **Handling**: Preserve conversation records under the product’s retention policy. If context limits require compaction, label summaries as derived context and preserve source records where policy permits.
- **Caching Role**: History may be included in provider-specific cache matching. Do not assume a penultimate-turn breakpoint or cumulative reuse.

### Tier 4: Ephemeral Turn Context (JIT Area Rules)

- **Content**: Applicable repository or folder-specific instructions, when present, and scoped local constraints loaded Just-In-Time (JIT) upon entering an area.
- **Placement**: Put changing scoped instructions in a variable part of the request when the host permits.
- **Rationale**: Keeping frequently changing content outside an otherwise reusable prefix may reduce needless prefix variation. Actual cache reuse depends on the provider, model, request structure, and cache lifetime.

### Tier 5: Dynamic Turn Delta

- **Content**: Latest user input prompt, active tool call invocations, current execution results, compiler logs, and git diffs.
- **Volatility**: Volatile per turn; discarded or promoted into Tier 3 history upon turn completion.
- **Compression**: Bulky dumps (build output, large files, JSON structures) MUST be reduced to relevant summaries, excerpts, or structural views before inclusion. Use tools supported by the current product repository; no specific private search or compression utility is required.
- **Sectional & Heading Subtree Extraction**: When ingesting supporting documentation, standards, or reference corpuses into active turn context (Tier 4/5), agents MUST extract only the relevant heading subtree or line-bounded range (`StartLine`/`EndLine`). Ingesting full documents when only a single control or procedure is needed bloats turn context, accelerates token consumption, and introduces noise.

### Context Hierarchy Summary

| Tier | Layer Name | Content Ingestion | Volatility | Caching Classification | Invalidation Scope |
| --- | --- | --- | --- | --- | --- |
| **Tier 1** | Stable Base Context | Stable instructions, tool schemas, shared catalogs | Prefer stable | Potential reusable prefix | Changes to shared context |
| **Tier 2** | Specialist Context | Specialist definitions, skills, domain schemas when used | Invocation-scoped | Host-specific | Specialist invocation |
| **Tier 3** | Conversation History | Relevant user, assistant, and tool messages or derived summaries | Grows or is compacted by policy | Provider-specific | History or summary changes |
| **Tier 4** | Scoped Context | Applicable repository or area instructions, if present | Area- or task-scoped | Host-specific | Area or task changes |
| **Tier 5** | Turn-Specific Context | Latest user prompt, tool calls, and execution outputs | Volatile | Usually variable input | Current turn |

---

## Multi-Model Caching Mechanics (Resolving HIGH-01)

Prompt-caching behavior varies by provider, model, API, account settings, and release. Treat thresholds, breakpoints, retention, and prices as version-specific; verify them in the provider’s current documentation before implementation.

### Provider Comparison Matrix

| Provider family | Cache mechanism | Thresholds, retention, and accounting |
| --- | --- | --- |
| Anthropic Claude | Implicit and explicit prompt caching, depending on model/API | Verify current model and API documentation |
| OpenAI | Automatic prefix caching and model-specific cache options | Verify current model and API documentation |
| Google Gemini | Implicit and explicit context caching, depending on model/API | Verify current model and API documentation |

---

### Anthropic Claude prompt caching

The Claude API uses `cache_control` breakpoints and searches backward through a 20-block lookback window per breakpoint; the current API documentation permits up to four breakpoints per request. Consecutive `tool_use` blocks and consecutive `tool_result` blocks count as one position in the API lookback. Place breakpoints only where the documented request structure supports them, and account for cache writes, reads, uncached input, model thresholds, and TTL. The API reports cache creation and read counts in `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens`. Avoid synthetic keepalive traffic intended only to preserve idle cache entries, and verify limits in the current documentation before implementation.

---

### OpenAI prompt caching

OpenAI caching matches eligible rendered request prefixes. Cache thresholds, breakpoints, and retention vary by model and request settings; for example, current documentation specifies a 1,024-token minimum for GPT-5.6 and later, while earlier models vary by request settings. Responses API usage reports `usage.input_tokens_details.cached_tokens` and `usage.input_tokens_details.cache_write_tokens`. Stable prefixes can improve reuse, but session continuity or prompt length alone does not guarantee a cache hit. Verify current behavior for the selected API and model, then measure reads, writes, latency, and total cost.

---

### Google Gemini context caching

Gemini supports implicit caching and, for supported APIs, explicit cache resources. Availability and minimum token counts depend on the selected model and API. The Interactions API reports cached tokens in `usage.total_cached_tokens`; GenerateContent reports the REST field `usageMetadata.cachedContentTokenCount` (SDKs may expose `usage_metadata.cached_content_token_count`). Verify the field and cost behavior for the API in use.

---

## Cache Invalidation Anti-Patterns and Prohibitions

The following patterns can reduce cache reuse, increase costs, or weaken execution auditability. Apply each rule according to the selected provider and the product’s security requirements.

### 1. Dynamic Timestamps in Prefix Prompts

- **Failure**: Injecting changing values into a prefix intended for reuse can prevent that prefix from matching, depending on the provider’s cache rules.
- **Rule**: Keep dynamic timestamps and identifiers out of context deliberately designed as a stable prefix when the request format allows.
- **Remediation**: Pass timestamps exclusively in Tier 5 (Turn Delta) or allow agents to query time via dedicated on-demand tooling.

### 2. Un-Ordered JSON Dictionaries and Schemas

- **Failure**: Nondeterministic serialization can introduce avoidable variation in a prefix intended for reuse.
- **Rule**: When serialized tool schemas, configuration, or catalogs are part of a reusable prefix, use deterministic serialization where the format permits.
- **Remediation**: Use the product’s supported canonical serialization method and verify the emitted request structure.

### 3. Frequently Changing Scoped Instructions in a Reusable Prefix

- **Failure**: Injecting changing folder instructions into an otherwise reusable prefix can change the prefix whenever an agent switches areas.
- **Rule**: Keep frequently changing scoped instructions outside a reusable prefix when the host permits.
- **Remediation**: Place scoped instructions in the request location documented for variable context, or start a separate task with only the necessary local context.

### 4. In-Place Conversation History Rewriting

- **Failure**: Rewriting history can obscure what information the model received and make behavior harder to reproduce.
- **Rule**: Do not silently alter source conversation records for cache optimization. Apply the product’s retention policy and distinguish derived summaries from original records.
- **Remediation**: When context limits require compaction, create a traceable summary and start a new task if needed. Treat cache effects as provider-specific.

### 5. Base64 Execution and Code Obfuscation (CRIT-01)

- **Failure**: Executing Base64-encoded payloads via dynamic eval/exec (`python -c "import base64; exec(...)"`) obfuscates execution from AST security linters, defeats audit trails, and risks prompt injection execution.
- **Rule**: Base64 dynamic execution patterns are strictly banned.
- **Remediation**: Place explicit, reviewable scripts in a suitable local working directory and invoke them through the normal command-line interface.

### 6. Provider breakpoint limits

- **Failure**: Placing cache markers beyond a provider or API’s supported limit can reject a request; excessive cache writes can also increase cost without useful reuse.
- **Rule**: Follow the selected model and API’s documented breakpoint limit and placement rules. Do not apply Anthropic’s four-breakpoint cap or 20-block lookback to other providers, or impose a universal two-breakpoint policy.

---

## Cross-host delegation context boundaries

Delegated agents should receive only the context needed for their task. Context filtering, process isolation, and filesystem isolation are separate controls; do not treat one as proof of another.

### 1. Bounded subagent context

When an orchestrator delegates work:
- **Bounded context**: Provide the task, necessary parameters, applicable local instructions, and working location. Do not include unrelated conversation history or private data.
- **Targeted discovery**: Let the delegated agent acquire other context using search and code-inspection tools supported by the repository.
- **History controls**: Do not copy or forward unrelated transcripts. Check whether the host includes conversation history by default and use documented filtering controls where needed.

### 2. Multi-Host Configuration and Enforcement Matrix

| Product or API | Documented behavior | Boundary to verify |
| :--- | :--- | :--- |
| **Claude Code subagents** | Each subagent has its own context window and configurable tools/permissions. `isolation: worktree` controls the working directory. | Confirm which prompt and project instructions are loaded. A separate context window or worktree does not itself prove data or process isolation. |
| **OpenAI Agents SDK handoffs** | A receiving agent gets the conversation history by default; `input_filter` can change what history it receives. | A handoff filter controls input history; it is not a sandbox or filesystem boundary. Configure and test those controls separately. |
| **Other hosts and APIs** | Behavior depends on the product, version, and delegation feature. | Consult the product’s current documentation and test the actual passed history, instructions, tools, permissions, and working directory. Do not infer enforcement from a config filename or a prompt alone. |

### 3. Anti-Patterns in Subagent Context Delegation

1. **Transcript Dumping**: Pasting the full multi-turn coordinator history into a delegated task. This can expose unrelated data and distract from the bounded task.
2. **Whole-Repository Preloading**: Instructing a delegated agent to read the entire repository before beginning. Use targeted search and code inspection supported by the local environment.
3. **Padded Definitions of Done**: Expanding subagent task prompts with unrequested coordinator chores rather than passing the concise, bounded task contract.
4. **Agent-access ignore on worktrees**: Do not deny file access to a working tree that the assigned agent must edit. Where the host distinguishes access controls from indexing exclusions, use the documented control for the intended effect.

---

## Verification and Enforcement

1. **Cache measurement**: Compare representative repeated requests and record the provider, model, API, cache reads and writes, uncached input, latency, and cost. Use the provider’s documented response fields and current pricing.
2. **Delegation configuration**: Validate the host’s supported configuration format and inspect what history, instructions, tools, permissions, and working directory a delegated task receives. If the host offers no enforceable control required by the product, record that limitation.
3. **Code checks**: Run the product repository’s configured parser, linter, or tests for deterministic serialization and prohibited obfuscated execution. If no check exists, record the coverage gap rather than referring to a private checker.

---

## Related Standards and References

- AI Development Security: [`ai-development-security.md`](./ai-development-security.md)
- Data Protection: [`data-protection.md`](./data-protection.md)
- Provider documentation: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [Claude Code settings](https://code.claude.com/docs/en/settings), [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching), [OpenAI Agents SDK handoffs](https://openai.github.io/openai-agents-python/handoffs/), [Gemini context caching](https://ai.google.dev/gemini-api/docs/caching), [Gemini Interactions token usage](https://ai.google.dev/gemini-api/docs/tokens), [Gemini GenerateContent token usage](https://ai.google.dev/gemini-api/docs/generate-content/tokens)

AI Router may maintain additional internal harness notes as optional provenance. Access to those notes or tools is not required to apply, validate, or maintain this standard.

