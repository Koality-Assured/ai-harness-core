# ast-grep AGENTS

Durable tool recipes, AST-based precision retrieval patterns, outline-first symbol discovery, and structural code refactoring rules.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational recipes, symbol extraction commands, and structural query rules for [ast-grep](https://ast-grep.github.io/), enabling precision retrieval across Python, JSON, and YAML without dumping whole files into context.

## Local Constraints

1. **Strict Output Fire-Wall:** `supporting/` is strictly an input resource and accelerator store. Agents and scripts MUST NEVER deposit AST extraction dumps, generated fact tables, or validation reports into `supporting/ast-grep/`. All run artifacts MUST route to `results/cost-layers/ast-grep/<topic>/<YYYY-MM-DD>/` per [`../../results/results-conventions.md`](../../results/results-conventions.md).
2. **One-Way Dependency Invariant:** Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
3. **Outline-First Code Inspection (No Whole-File Dumps):** Agents MUST inspect symbols, functions, and classes using `ast-grep outline` and bounded line-range reads (`StartLine`/`EndLine`) before modifying code. Whole-file dumping is strictly forbidden for code editing or inspection.
4. **Tri-Tier Agent Context Architecture:** Follow the mandatory 3-tier sequence:
   - *Tier 1 (Discovery & Localization):* Discover structural code with `ast-grep outline` or `run -p`, and prose/policy via `qmd`.
   - *Tier 2 (Surgical Ingestion & Mutation):* Ingest only the bounded range of the target function/class before modifying; apply surgical diff edits or `ast-grep --rewrite` for mechanical bulk updates. Never edit from outline skeletons alone without viewing implementation logic.
   - *Tier 3 (Validation & Guardrails):* Verify syntax/types with linters and repository invariants with `ast-grep scan -c sgconfig.yml`.
5. **Structural Correctness Oracle & Separation of Roles:** ast-grep serves as a structural correctness oracle (verifying `canonical_id`, `owner_agent`, agent card pairs). It is NOT a general Markdown prose searcher (use `qmd`), NOT a third compressor (use Headroom), and NOT a custom Markdown AST parser.
6. **Command & Syntax Rules:** Use `ast-grep` (the `sg` alias is deprecated). Quote patterns with single quotes in PowerShell to prevent `$` metavar interpolation (`ast-grep run -p 'def $NAME($$$ARGS):'`). Use `-k pair` for JSON and `-k block_mapping_pair` for YAML frontmatter.

## Next Hops

- Precision retrieval & structural recipes: [`precision-retrieval.md`](./precision-retrieval.md)
- Machine setup & environment onboarding: [`../workstation-onboarding.md`](../workstation-onboarding.md)
- Default specialist: [`../../ai-tooling/agents/harness-operator/AGENT.md`](../../ai-tooling/agents/harness-operator/AGENT.md)
