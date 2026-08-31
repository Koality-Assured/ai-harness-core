---
doc_kind: routing_map
canonical_id: script-index
topics: [scripts, routing]
generated_at_utc: export
generator: scripts/routing/generate_script_index.py
---

# Script index

Generated from dest `scripts/` after harness-template export (kept trees only). Do not hand-edit — run `python scripts/routing/generate_script_index.py` from the dest checkout after feeding scripts.

| Script | Tags | Hints | Summary |
| --- | --- | --- | --- |
| [`ai-tooling/model_memory.py`](./ai-tooling/model_memory.py) | `ai-tooling`, `memory` | model-memory, model-capability-memory, capability-retrieval, promote-model-learning | Search, validate, and propose promotion of model-family capability memory. |
| [`ai-tooling/validate_agent.py`](./ai-tooling/validate_agent.py) | `ai-tooling`, `routing`, `agents` | agents, validate, dry-run, schema-v2 | Validate one or all agents against Schema V2 frontmatter and agent conventions. |
| [`ai-tooling/validate_skill.py`](./ai-tooling/validate_skill.py) | `ai-tooling`, `routing` | skills, dry-run, template, schema-v2 | Validate one or all skills against skill-conventions.md. |
| [`change-history/append_change_history.py`](./change-history/append_change_history.py) | `change-history` | provenance, session-end, completion-gate | Append a change-history entry for the active year/quarter. |
| [`change-history/ensure_change_history_quarter.py`](./change-history/ensure_change_history_quarter.py) | `change-history` | provenance, scaffold | Ensure change-history year/quarter entries file exists. |
| [`cost-layers/extract_ast_facts.py`](./cost-layers/extract_ast_facts.py) | `qmd`, `headroom`, `ast-grep` | structural-facts, outline, cost-layers | Extract structural facts via ast-grep outline/kind JSON (not full files). |
| [`cost-layers/validate_ast_grep.py`](./cost-layers/validate_ast_grep.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, structural-facts | Dry-run ast-grep precision retrieval and Headroom structural-fact survival. |
| [`cost-layers/validate_cost_layers.py`](./cost-layers/validate_cost_layers.py) | `qmd`, `headroom`, `ast-grep`, `cost-layers`, `research` | validation, dry-run, tokens, cost-layers, prompt-caching, webfetch | Run qmd + Headroom + ast-grep + prompt-caching + webfetch cost-layer dry runs and write a combined report. |
| [`cost-layers/validate_headroom_compression.py`](./cost-layers/validate_headroom_compression.py) | `headroom`, `qmd` | validation, dry-run, tokens, compression | Dry-run Headroom compression: token savings vs gold-fact accuracy. |
| [`cost-layers/validate_prompt_caching.py`](./cost-layers/validate_prompt_caching.py) | `cost-layers`, `routing`, `agents` | prompt-caching, invariance, validation, dry-run, kv-cache | Validate prompt cache invariance across agent definitions and system instructions. |
| [`docs/run_markdownlint.py`](./docs/run_markdownlint.py) | `docs`, `markdown` | markdownlint, lint, markdownlint-cli2, dry-run | Run markdownlint-cli2 over repo Markdown (read-only by default). |
| [`docs/validate_context_budget.py`](./docs/validate_context_budget.py) | `docs`, `validation`, `cost-layers` | context-budget, tokens, agents-md, ingestibility, ceiling | Validate context budget ceilings and ingestibility rules across repository entry files. |
| [`docs/validate_router_structure.py`](./docs/validate_router_structure.py) | `docs`, `routing` | router, structure, validation, results-layout | Validate router structure (areas, catalogs, frontmatter, dispatch, results layout). |
| [`docs/validate_structure_fast.py`](./docs/validate_structure_fast.py) | `docs`, `validation`, `lint` | validate, structure, frontmatter, links, markdown | Fast structural validator for Markdown documents in ai-router. |
| [`github/resolve_github_path.py`](./github/resolve_github_path.py) | `github` | blob, main, path, url | Resolve local repo paths to GitHub https blob/tree URLs on main. |
| [`qmd/qmd_preflight.py`](./qmd/qmd_preflight.py) | `qmd` | preflight, index, onboarding, safety | Inspect reusable qmd state without creating or refreshing an index. |
| [`qmd/refresh_qmd_index.py`](./qmd/refresh_qmd_index.py) | `qmd` | index, embed, session-end, completion-gate | Refresh an existing local qmd index after explicit user approval. |
| [`qmd/setup_qmd_collections.py`](./qmd/setup_qmd_collections.py) | `qmd` | index, collections, embed, modular, areas | Set up missing qmd collections only after an explicit, inspected approval. |
| [`qmd/validate_qmd_retrieval.py`](./qmd/validate_qmd_retrieval.py) | `qmd` | validation, dry-run, tokens | Dry-run qmd retrieval: health, relevance, and token-cost comparison. |
| [`repos/scaffold_public_repos.py`](./repos/scaffold_public_repos.py) | `repos`, `scaffold`, `github` | scaffold, public-repos, agent-skills, agent-standards, ai-research, wiki-template | Automated scaffolding CLI to initialize the 3 public Koality-Assured ecosystem repositories. |
| [`research/ai_vendor_briefing.py`](./research/ai_vendor_briefing.py) | `research`, `intelligence`, `briefing` | vendor-updates, flash-briefing, ai-vendors, primary-sources | Fetch, analyze, and synthesize AI vendor updates into flash briefings. |
| [`research/benchlm_lookup.py`](./research/benchlm_lookup.py) | `research`, `benchmarks`, `pricing`, `models` | benchlm, llm-benchmarks, model-pricing, price-performance, speed | Query, filter, and compare LLM benchmarks, pricing, and speed from BenchLM. |
| [`research/community_analyzer.py`](./research/community_analyzer.py) | `research`, `communities`, `socials`, `analysis`, `osint` | community-analyzer, subreddits, forums, sentiment, troubleshooting, osint | Community analyzer utility for querying, scoring, and synthesizing developer communities. |
| [`research/local_webfetch.py`](./research/local_webfetch.py) | `research`, `web`, `distillation`, `cost-layers` | webfetch, markdown, scrape, sanitize | Local Python web distillation utility for clean, boilerplate-free Markdown. |
| [`research/manage_social_registry.py`](./research/manage_social_registry.py) | `research`, `communities`, `socials`, `registry`, `maintenance` | social-registry, manage-communities, rubric-scoring, validate | Manage, score, and validate the community reliability catalog. |
| [`routing/generate_routing_index.py`](./routing/generate_routing_index.py) | `routing` | area-map, skill-dispatch, areas.yaml, index | Generate routing/area-map.md and routing/skill-dispatch.md. |
| [`routing/generate_script_index.py`](./routing/generate_script_index.py) | `routing` | script-discovery, index | Generate scripts/script-index.md from Python docstring tags. |
| [`routing/generate_skill_dispatch.py`](./routing/generate_skill_dispatch.py) | `routing`, `ai-tooling` | skills, dispatch, catalog | Generate routing/skill-dispatch.md from skill frontmatter. |
| [`routing/hybrid_dispatch.py`](./routing/hybrid_dispatch.py) | `routing`, `ai-tooling` | dispatch, hybrid-dispatch, bm25, fast-path, ambiguity-gate, router | 3-Tier Hybrid Dispatch Pipeline for skills, agents, and area routing. |
| [`routing/resolve_skill_graph.py`](./routing/resolve_skill_graph.py) | `routing`, `skills`, `dag` | skills, dependencies, topological-sort, execution-plan, prerequisites | Resolve skill dependency DAGs, topological ordering, and execution stages. |
| [`routing/spawn_worktree.py`](./routing/spawn_worktree.py) | `routing`, `isolation` | worktree, branch, concurrency, claims | Spawn, list, and remove isolated git worktrees for concurrent agent work. |
| [`sync/sync_and_push_downstreams.py`](./sync/sync_and_push_downstreams.py) | `sync`, `git`, `export`, `downstream` | sync-and-push, update-downstreams, multi-repo-publish, downstream-repo-update | Automated synchronization, sanitation, commit, and push engine for public downstream repositories. |
| [`sync/sync_public_repos.py`](./sync/sync_public_repos.py) | `sync`, `security`, `export` | sync, redaction, multi-repo, export, sanitize, wiki-template | Multi-repo synchronization and sanitization/redaction engine for public exports. |
| [`tests/test_benchmarks.py`](./tests/test_benchmarks.py) | `tests`, `benchmarks`, `cost-layers`, `agents`, `retrieval`, `fleet` | tests, test-benchmarks, cost-estimator, fleet-benchmark, mrr | Unit tests for empirical benchmarking and cost estimation tooling. |
| [`tests/test_hybrid_dispatch.py`](./tests/test_hybrid_dispatch.py) | `tests`, `routing`, `ai-tooling` | tests, hybrid-dispatch, bm25, ambiguity-gate, schema-v2 | Unit tests for 3-Tier Hybrid Dispatch Pipeline and Schema V2 Indexing. |
| [`tests/test_pacing.py`](./tests/test_pacing.py) | `tests`, `pacing`, `quota`, `routing` | tests, pacing, quota-management | Unit tests for adaptive quota management and pacing helper. |
| [`tests/test_pretty_docs_security.py`](./tests/test_pretty_docs_security.py) | `tests`, `security`, `github` | tests, href, github-paths | Stdlib unit tests for href allow-list and GitHub path helpers. |
| [`tests/test_qmd_preflight.py`](./tests/test_qmd_preflight.py) | `tests`, `qmd` | qmd, preflight, onboarding | Unit tests for the non-mutating qmd lifecycle preflight. |
| [`tests/test_skill_graph.py`](./tests/test_skill_graph.py) | `tests`, `routing`, `skills`, `dag` | tests, dag, topological-sort, dependencies, prerequisites | Unit tests for skill dependency DAG resolution, topological ordering, and Schema V2 conventions. |
| [`tests/test_subagent_context_config.py`](./tests/test_subagent_context_config.py) | `tests`, `subagents`, `context`, `config` | tests, subagents, context-isolation, host-config | Unit tests for cross-host subagent context isolation and project-level settings. |
| [`tests/test_validate_agent.py`](./tests/test_validate_agent.py) | `tests`, `ai-tooling`, `agents`, `schema-v2` | tests, validate-agent, agents | Unit tests for Schema V2 agent validation. |
| [`tests/test_validate_context_budget.py`](./tests/test_validate_context_budget.py) | `tests`, `docs`, `validation`, `cost-layers` | tests, validate_context_budget, context-budget, tokens | Unit tests for validate_context_budget.py. |
| [`tests/test_validate_router_structure.py`](./tests/test_validate_router_structure.py) | `tests`, `docs`, `validation`, `results` | tests, validate_router_structure, results-layout | Unit tests for router structure validator results-layout check. |
| [`tests/test_validate_skill.py`](./tests/test_validate_skill.py) | `tests`, `ai-tooling`, `skills`, `schema-v2` | tests, validate-skill, skills | Unit tests for Schema V2 skill validation. |
| [`tests/test_validate_structure_fast.py`](./tests/test_validate_structure_fast.py) | `tests`, `docs`, `validation` | tests, validate_structure_fast, markdown | Unit tests for fast structural validator. |

## By tag

- **agents:** `ai-tooling/validate_agent.py`, `cost-layers/validate_prompt_caching.py`, `tests/test_benchmarks.py`, `tests/test_validate_agent.py`
- **ai-tooling:** `ai-tooling/model_memory.py`, `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `tests/test_hybrid_dispatch.py`, `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **analysis:** `research/community_analyzer.py`
- **ast-grep:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`
- **benchmarks:** `research/benchlm_lookup.py`, `tests/test_benchmarks.py`
- **briefing:** `research/ai_vendor_briefing.py`
- **change-history:** `change-history/append_change_history.py`, `change-history/ensure_change_history_quarter.py`
- **communities:** `research/community_analyzer.py`, `research/manage_social_registry.py`
- **config:** `tests/test_subagent_context_config.py`
- **context:** `tests/test_subagent_context_config.py`
- **cost-layers:** `cost-layers/validate_cost_layers.py`, `cost-layers/validate_prompt_caching.py`, `docs/validate_context_budget.py`, `research/local_webfetch.py`, `tests/test_benchmarks.py`, `tests/test_validate_context_budget.py`
- **dag:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`
- **distillation:** `research/local_webfetch.py`
- **docs:** `docs/run_markdownlint.py`, `docs/validate_context_budget.py`, `docs/validate_router_structure.py`, `docs/validate_structure_fast.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`
- **downstream:** `sync/sync_and_push_downstreams.py`
- **export:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **fleet:** `tests/test_benchmarks.py`
- **git:** `sync/sync_and_push_downstreams.py`
- **github:** `github/resolve_github_path.py`, `repos/scaffold_public_repos.py`, `tests/test_pretty_docs_security.py`
- **headroom:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`
- **intelligence:** `research/ai_vendor_briefing.py`
- **isolation:** `routing/spawn_worktree.py`
- **lint:** `docs/validate_structure_fast.py`
- **maintenance:** `research/manage_social_registry.py`
- **markdown:** `docs/run_markdownlint.py`
- **memory:** `ai-tooling/model_memory.py`
- **models:** `research/benchlm_lookup.py`
- **osint:** `research/community_analyzer.py`
- **pacing:** `tests/test_pacing.py`
- **pricing:** `research/benchlm_lookup.py`
- **qmd:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `qmd/qmd_preflight.py`, `qmd/refresh_qmd_index.py`, `qmd/setup_qmd_collections.py`, `qmd/validate_qmd_retrieval.py`, `tests/test_qmd_preflight.py`
- **quota:** `tests/test_pacing.py`
- **registry:** `research/manage_social_registry.py`
- **repos:** `repos/scaffold_public_repos.py`
- **research:** `cost-layers/validate_cost_layers.py`, `research/ai_vendor_briefing.py`, `research/benchlm_lookup.py`, `research/community_analyzer.py`, `research/local_webfetch.py`, `research/manage_social_registry.py`
- **results:** `tests/test_validate_router_structure.py`
- **retrieval:** `tests/test_benchmarks.py`
- **routing:** `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `cost-layers/validate_prompt_caching.py`, `docs/validate_router_structure.py`, `routing/generate_routing_index.py`, `routing/generate_script_index.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `routing/resolve_skill_graph.py`, `routing/spawn_worktree.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pacing.py`, `tests/test_skill_graph.py`
- **scaffold:** `repos/scaffold_public_repos.py`
- **schema-v2:** `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **security:** `sync/sync_public_repos.py`, `tests/test_pretty_docs_security.py`
- **skills:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`, `tests/test_validate_skill.py`
- **socials:** `research/community_analyzer.py`, `research/manage_social_registry.py`
- **subagents:** `tests/test_subagent_context_config.py`
- **sync:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **tests:** `tests/test_benchmarks.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pacing.py`, `tests/test_pretty_docs_security.py`, `tests/test_qmd_preflight.py`, `tests/test_skill_graph.py`, `tests/test_subagent_context_config.py`, `tests/test_validate_agent.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_skill.py`, `tests/test_validate_structure_fast.py`
- **validation:** `docs/validate_context_budget.py`, `docs/validate_structure_fast.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`
- **web:** `research/local_webfetch.py`
