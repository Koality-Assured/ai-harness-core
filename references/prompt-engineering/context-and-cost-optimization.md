---
doc_kind: reference
canonical_id: prompt-engineering-context-cost-optimization
purpose: [reference, cost-optimization, context-engineering]
topics: [cost-layers, context-window, prompt-caching, batch-apis, web-retrieval, model-tiers]
advisory_only: true
---

# Context and Cost Optimization: High-ROI, Zero-Degradation Strategies

## Purpose

Provides an empirical framework for reducing LLM token consumption and API operational costs while maintaining 100% reasoning fidelity, syntactic precision, and system reliability.

---

## 1. The Cost-Optimization Hierarchy

Cost reduction must be prioritized by impact vs. reliability risk. Micro-optimizations that alter grammar or risk model comprehension should be avoided in favor of architectural levers.

```
+-------------------------------------------------------------+  Savings: 50% - 90%
|  1. Prefix Caching & KV Stability (Anthropic / Gemini / OpenAI)|  Risk: Zero
+-------------------------------------------------------------+
|  2. Subagent Model Down-Tiering (Leaf Workers -> Fast/Flash)   |  Savings: 70% - 85%
+-------------------------------------------------------------+  Risk: Very Low
|  3. Batch APIs for Async & Offline Workloads (50% Discount)   |  Savings: 50%
+-------------------------------------------------------------+  Risk: Zero
|  4. Bounded Context & Symbol Outlining (ast-grep / qmd)        |  Savings: 60% - 80%
+-------------------------------------------------------------+  Risk: Zero
|  5. Tool Output Compression (Headroom CCR / Truncation)       |  Savings: 40% - 70%
+-------------------------------------------------------------+  Risk: Very Low
|  6. Clean Web Ingestion (Readability / Markdown Stripping)    |  Savings: 75% - 90%
+-------------------------------------------------------------+  Risk: Zero
|  [DO NOT USE] Lossy Syntax Stripping / "Caveman" Prompting     |  Savings: < 8%
+-------------------------------------------------------------+  Risk: Extreme
```

---

## 2. Deep Dive: Architectural Cost Levers

### Lever A: Prompt Prefix Caching
- **Mechanism**: LLM providers cache the KV-states of prompt prefixes across API calls.
- **Economic Impact**:
  - Anthropic Claude: 90% discount on cached prompt read tokens; 25% surcharge on initial cache write.
  - Google Gemini: 75% discount on cached context (minimum context thresholds apply).
  - OpenAI GPT-4o: 50% automatic discount on cached prompt tokens.
- **Implementation**: Ensure base system prompts, tool schemas, and static rules are serialized at the head of every request with byte-for-byte consistency.

### Lever B: Batch APIs for Non-Interactive Workloads
- **Mechanism**: Asynchronous processing with 24-hour turnaround SLAs (OpenAI Batch API, Anthropic Message Batches, Gemini Batch API).
- **Economic Impact**: Flat **50% discount** across both input and output tokens, coupled with separate rate limit pools.
- **When to Use**:
  - Offline evaluation pipelines and benchmark sweeps.
  - Bulk codebase scanning, threat modeling, and documentation generation.
  - Batch semantic embedding and indexing.
- **When NOT to Use**: Interactive coding agent loops, synchronous tool-calling chains, and pair programming sessions where sub-second or immediate turnaround is required.

### Lever C: Host-Agnostic Subagent Down-Tiering
- **Mechanism**: Orchestrators assign semantic capability tiers (`tier: "fast" | "standard" | "high" | "max"`) rather than hardcoding vendor model strings.
  - **Fast Tier**: Lightweight, high-throughput models (Gemini Flash, Grok Fast, Claude Haiku, GPT-4o-mini, or local 7B/8B quantized models like Qwen-2.5-Coder-7B). Dedicated to mechanical search, file reading, grep, and lint verification.
  - **Standard/High Tier**: Deep reasoning models (Gemini Pro, Claude Sonnet/Opus, GPT-4o, or local 70B models). Dedicated to top-level architecture, plan decomposition, and final code synthesis.
- **Economic Impact**: Leaf exploration accounts for ~70–80% of total raw tokens in multi-agent workflows. Routing leaf tasks to the host's `fast` tier yields an **80%+ net reduction** in high-tier quota consumption without degrading top-level synthesis.

### Lever D: Precision Context Extraction (ast-grep & qmd)
- **Mechanism**: Instead of whole-file dumps, use AST symbol extraction (`ast-grep outline`) and line-bounded slicing (`StartLine`/`EndLine`).
- **Economic Impact**: Replaces a 3,000-token file ingestion with a 150-token symbol outline and targeted 40-line function read.

### Lever E: Headroom CCR (Compress-Cache-Retrieve)
- **Mechanism**: Intercepts redundant JSON arrays, repeated compiler logs, and voluminous grep returns between agent and provider. Compresses redundant structures while preserving unique error signatures and gold facts.
- **Economic Impact**: 40% to 70% reduction in conversation history token inflation across multi-turn sessions.

### Lever F: Local-First Agnostic Web Distillation (Python-Native)
- **Mechanism**: Ingesting external web URLs exclusively through local Python extraction libraries (e.g. `trafilatura`, `readability-lxml`, `markdownify`, or BeautifulSoup) to strip DOM boilerplate, navigation bars, cookie banners, tracking scripts, and styling before markdown conversion. Zero dependence on third-party cloud scraping APIs.
- **Economic Impact**: Reduces raw web page token payloads from 15,000–30,000 tokens (unfiltered DOM/HTML) down to 800–2,500 tokens of clean, high-signal Markdown.

---

## 3. What to Avoid: Pseudo-Optimizations

| Technique | Claimed Benefit | Actual Outcome | Verdict |
| :--- | :--- | :--- | :--- |
| **"Caveman" Token Stripping** | "Saves 15% tokens" | Degrades reasoning, breaks conditional syntax, causes syntax errors in code generation. | **Forbidden** |
| **Dynamic Instruction Churn** | "Injects dynamic context" | Invalidates prefix cache across turns; increases cost by 4x–10x. | **Forbidden** |
| **Micro-prompt Shortening** | "Trims 50 words" | Marginal <1% savings with high risk of missing edge-case constraints. | **Avoid** |
| **Over-compressing Gold Facts** | "Shrinks logs to 1 line" | Omits critical error stack traces, forcing redundant repair turns. | **Avoid** |
