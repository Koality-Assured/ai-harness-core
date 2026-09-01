---
doc_kind: supporting
canonical_id: benchmark-methodology
purpose: [process]
rank: high
topics: [benchmarks, cost-layers, pricing, methodology, mrr, pass-at-1, kv-cache]
rag_keywords: [benchmark, pricing, pass@1, MRR, precision@k, headroom, trajectory, kv-cache]
---

# Benchmarking Methodology & Metric Formulas

Empirical methodology and formulas used by `benchmark-agent` and associated benchmark tooling across the repository.

## 1. Agent & Skill Cost Estimation Methodology

### Token Trajectory & KV Caching

In conversational agent loops, token consumption is divided into **static prompt prefixes** (system prompt, agent definition, allowed tool parameter schemas, paired skill instructions) and **dynamic turns** (user prompts, tool execution outputs, model thought traces, final output text).

$$\text{Static Prefix Tokens} = T_{\text{agent}} + T_{\text{skill}} + \sum_{i=1}^{N_{\text{tools}}} T_{\text{schema}_i}$$

In multi-turn executions with provider-side KV prompt caching (e.g. Gemini, Claude Prompt Caching, OpenAI Prompt Caching):
- **Turn 1**: Pays full uncached input rate for $\text{Static Prefix} + \text{User Prompt}_1$.
- **Turn $k$ ($k \ge 2$)**: Pays cached input rate for prior context ($C_{k-1}$) and uncached input rate for new turn deltas ($\Delta_{\text{in}_k}$).

$$\text{Cost}_{\text{Turn } k} = \left(\frac{C_{k-1}}{10^6} \times P_{\text{cached\_in}}\right) + \left(\frac{\Delta_{\text{in}_k}}{10^6} \times P_{\text{uncached\_in}}\right) + \left(\frac{T_{\text{out}_k}}{10^6} \times P_{\text{out}}\right)$$

### Pricing Matrix by Tier (USD per 1M Tokens)

| Model Tier | Uncached Input | Cached Input | Output | Reference Providers / Models |
| --- | --- | --- | --- | --- |
| `fast` | \$0.15 | \$0.0375 | \$0.60 | Gemini 3.7 Flash, Claude 3.5 Haiku, GPT-4o-mini |
| `standard` | \$1.25 | \$0.30 | \$5.00 | Gemini 3.7 Flash, GPT Luna, Grok 4.5 |
| `high` | \$3.00 | \$0.30 | \$15.00 | Claude 3.7 Sonnet, GPT Terra, Grok 4.6 |
| `max` | \$5.00 | \$1.25 | \$25.00 | Gemini 3.1 Pro, GPT Sol, Claude Extended Thinking |

---

## 2. Multi-Agent Fleet Simulation

The fleet benchmark executes dry-run validation sweeps across all registered agents and skills to assert:
1. **Prompt Cache Invariance**: Asserts that prompt heads do not contain volatile runtime timestamps, random nonces, or dynamic environment paths that invalidate provider KV-caches.
2. **Context Headroom**: Asserts that 5-turn and 10-turn multi-turn trajectories remain within the agent's declared `token_ceiling`.
3. **Delegation Graph Integrity**: Verifies that all `delegation_targets` reference valid, existing agents in `ai-tooling/agents/`.
4. **Tool Parameter Footprint**: Quantifies serialization overhead per tool schema.

$$\text{Headroom \%} = \frac{\text{token\_ceiling} - \text{Context Tokens}_{\text{end}}}{\text{token\_ceiling}} \times 100$$

---

## 3. Corpus Retrieval Quality Metrics

### Mean Reciprocal Rank (MRR)

Measures the rank position of the first relevant document retrieved for a test query:

$$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

Where $\text{rank}_i$ is the 1-indexed position of the first ground-truth document retrieved for query $i$.

### Precision@K

Measures the proportion of retrieved documents in the top $K$ that are relevant:

$$\text{Precision@K} = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{K}$$

---

## 4. Tool Output Compression & Efficiency

Measures token reduction achieved by tool output preprocessors (Headroom, ast-grep, local_webfetch) while auditing structural fact retention:

$$\text{Token Reduction \%} = \left(1 - \frac{\text{Tokens}_{\text{compressed}}}{\text{Tokens}_{\text{raw}}}\right) \times 100$$

$$\text{Fact Preservation \%} = \frac{|\text{Facts}_{\text{retained}}|}{|\text{Facts}_{\text{required}}|} \times 100$$

Target: $\ge 70\%$ token reduction on verbose command dumps with $100\%$ gold fact preservation.

---

## 5. Coding Agent Task Evaluation

Evaluates autonomous coding agent execution against standardized benchmarks:
- **Pass@1**: Proportion of coding tasks solved correctly on the first attempt without human intervention.
- **Contract Adherence**: Verifies generation of all declared artifact paths without modifying forbidden files.
- **Token Efficiency**: Measures total tokens spent per successfully completed task.
