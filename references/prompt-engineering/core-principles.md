---
doc_kind: reference
canonical_id: prompt-engineering-core-principles
purpose: [reference, prompt-engineering, reliability]
topics: [prompt-engineering, llm, reasoning, cache-stability, tokens, anti-patterns]
advisory_only: true
---

# Prompt Engineering Core Principles and Reliability Standards

## Purpose

Establishes research-backed principles and empirical best practices for prompt design, instruction hierarchies, reasoning alignment, and reliability preservation across LLM architectures.

---

## 1. Structural Demarcation and Semantic Tagging

Modern frontier LLMs (Anthropic Claude, Google Gemini, OpenAI GPT) are trained extensively on structured markups. Explicit semantic tags provide clear boundaries between instructions, static context, and untrusted runtime data.

### Best practices
- **XML/HTML-Style Delimiters**: Wrap disparate context blocks in explicit tags (`<instructions>`, `<context>`, `<rules>`, `<tools>`, `<user_data>`).
- **Data vs. Instruction Isolation**: Always encapsulate external retrieval, user documents, and tool outputs in clear payload containers to prevent prompt injection and instruction confusion.
- **Hierarchical Framing**: Present system persona $\rightarrow$ strict constraints $\rightarrow$ reference knowledge $\rightarrow$ dynamic task inputs.

```markdown
<!-- Recommended Prompt Structure -->
<system_identity>
You are an expert systems engineer...
</system_identity>

<strict_constraints>
- Never reveal private tokens.
- All diffs must follow Unified Diff format.
</strict_constraints>

<context>
[Advisory domain knowledge or codebase schema]
</context>

<task>
[Specific actionable instruction]
</task>
```

---

## 2. Context Window Positioning (Mitigating "Lost in the Middle")

Research on transformer attention mechanisms (*Liu et al., 2023*) demonstrates that LLMs exhibit a U-shaped retrieval accuracy curve (primacy and recency effects):

1. **Top of Context (Primacy)**: High attention weight. Ideal for core persona, behavioral constraints, tool definitions, and system rules.
2. **Middle of Context**: Lowest relative attention weight. Place supplementary documentation, large search results, and secondary examples here.
3. **Bottom of Context (Recency)**: Highest attention weight for immediate task execution. Re-state critical output schemas, target requirements, and the final prompt directive here.

---

## 3. Prompt Prefix Caching and Deterministic Invariance

Modern LLM providers (Anthropic Prompt Caching, Google Gemini Context Caching, OpenAI Automatic Caching) offer **75% to 90% cost discounts** and dramatic latency reductions for reused prompt prefixes.

### Rules for cache maximization
1. **Static Prefixes**: Keep system prompts, baseline instructions, agent rules, and tool declarations completely static and byte-stable at the very beginning of the prompt.
2. **Zero Timestamp Churn**: Do not inject dynamically changing timestamps, session IDs, or volatile random seeds into the system prompt or early context blocks. Dynamic metadata belongs at the end.
3. **Incremental Appending**: Append conversation history and new tool turns strictly at the tail. Modifying earlier turns invalidates all subsequent KV-cache blocks.

---

## 4. Reasoning Steering and Output Structuring

- **Few-Shot Demonstration vs. Rule Inflation**: 2–3 high-quality input-output examples often yield greater accuracy than 20 lines of abstract negative constraints.
- **Explicit Step-by-Step Reasoning (CoT)**: For complex multi-step analysis or code refactoring, prompting the model to reason through constraints before emitting code reduces defect rates by 40–60%.
- **Constrained Output Schemas**: Prefer structured JSON Schema or Pydantic definitions over freeform text when programmatic parsing is required.

---

## 5. Anti-Patterns and Degradation Risks

### The "Caveman" Compression Anti-Pattern
Attempting to save tokens by stripping natural language grammar, articles, and punctuation (e.g., `"You write code no speak english fast no talk"`) is fundamentally flawed:

- **Token Economy Fallacy**: Stripping articles (`a`, `the`, `is`) only saves 5–10% of tokens, but causes high-order failure modes.
- **Semantic Degradation**: Tokenizers split truncated words and broken syntax into sub-optimal byte fragments, increasing embedding perplexity.
- **Instruction Drift & Hallucination**: Loss of grammatical nuance destroys conditional logic (`if`, `unless`, `except`), leading to severe instruction adherence failures and syntactically invalid code outputs.
- **Empirical Verdict**: Never degrade natural language syntax in system instructions or prompts. Rely on prefix caching, selective retrieval, and AST tooling for genuine cost reductions.

### Negative-Only Prompting
- Avoid long lists of *"Do NOT do X, Y, Z"* without specifying the correct positive action.
- Models respond significantly better to clear positive guidance: *"When encountering X, perform Y."*

### Context Stuffing
- Do not dump entire files or full repository trees into the prompt "just in case".
- Rely on targeted semantic search (`qmd`), structural symbol outlines (`ast-grep`), and JIT file retrieval to minimize noise.
