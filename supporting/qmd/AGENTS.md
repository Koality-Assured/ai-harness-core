# QMD AGENTS

Durable tool recipes, query patterns, index lifecycle maintenance, and Markdown chunking standards for the repository search index.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational recipes, query grammar rules, and retrieval lifecycle protocols for the repository's local BM25 and vector-augmented search engine (`qmd`), enabling sub-second lexical and semantic discovery without context bloating.

## Local Constraints

1. **Strict Output Fire-Wall:** `supporting/` is an input resource and accelerator store. Agents and automation scripts MUST NEVER write execution outputs, benchmark measurements, search caches, or run reports into `supporting/qmd/`. All generated artifacts MUST route to `results/cost-layers/qmd/<topic>/<YYYY-MM-DD>/` per [`../../results/results-conventions.md`](../../results/results-conventions.md).
2. **One-Way Dependency Invariant:** Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
3. **Persistent Detached Checkout (`scratch/qmd-main`):** All Markdown retrieval commands (`qmd search`, `qmd vsearch`, `qmd query`, `qmd get`, and `qmd multi-get`) MUST execute from the persistent detached checkout at `scratch/qmd-main` synchronized to `origin/main`. Agents MUST NEVER retrieve from a task worktree, where unmerged local changes or divergent SQLite indexes distort results.
4. **Four Core Retrieval Primitives:** Select retrieval commands strictly according to query intent:
   - `qmd search`: BM25 lexical keyword index (default first-hop; ~5–15ms; exact symbols, filenames, code tokens, and precise phrase anchors).
   - `qmd vsearch`: Dense vector cosine similarity via Gemma embeddings (~1–3s; semantic/conceptual discovery when exact vocabulary is unknown).
   - `qmd query`: Hybrid reranked search (~30–60s; structured query documents with `intent:`, `lex:`, `vec:`, and `hyde:` fields for multi-intent disambiguation).
   - `qmd get` & `qmd multi-get`: Direct document reader (<5–30ms; line-bounded ranges or batch multi-doc reads without serial tool-call polling).
5. **Anti-Fallback Hard Gate:** Agents MUST NOT bypass QMD with ungrounded recursive shell searches (`Get-ChildItem -Recurse`, `Select-String`, `git grep`, raw `find`, or PowerShell loops) unless QMD returns zero candidates across all collections or explicitly targeting untracked local scratch files.
6. **Index Lifecycle & Mutation Gates:** Routine BM25 freshness updates via `qmd update` from `scratch/qmd-main` are authorized prior to retrieval. Collection reconfiguration, initial index creation, or running embedding hydration (`qmd embed`) requires preflight inspection (`python scripts/qmd/qmd_preflight.py --inspect-hooks`) and explicit human approval. Never pass `--pull` from a worktree.

## Next Hops

- Query patterns & structured query grammar: [`query-pattern.md`](./query-pattern.md)
- Markdown retrieval chunking & frontmatter conventions: [`retrieval-conventions.md`](./retrieval-conventions.md)
- Machine setup & environment onboarding: [`../workstation-onboarding.md`](../workstation-onboarding.md)
- Default specialist: [`../../ai-tooling/agents/harness-operator/AGENT.md`](../../ai-tooling/agents/harness-operator/AGENT.md)
