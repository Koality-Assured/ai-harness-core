---
doc_kind: routing_map
canonical_id: script-index
topics: [scripts, routing]
generated_at_utc: 2026-09-18T17:30:54Z
generator: scripts/routing/generate_script_index.py
---

# Script index

Generated from Python docstring `tags:` / `routing_hints:`. Do not hand-edit — run `python scripts/routing/generate_script_index.py`.

| Script | Tags | Hints | Summary |
| --- | --- | --- | --- |
| [`ai-tooling/model_memory.py`](./ai-tooling/model_memory.py) | `ai-tooling`, `memory` | model-memory, model-capability-memory, capability-retrieval, promote-model-learning | Search, validate, and propose promotion of model-family capability memory. |
| [`ai-tooling/validate_agent.py`](./ai-tooling/validate_agent.py) | `ai-tooling`, `routing`, `agents` | agents, validate, dry-run, schema-v2 | Validate one or all agents against Schema V2 frontmatter and agent conventions. |
| [`ai-tooling/validate_skill.py`](./ai-tooling/validate_skill.py) | `ai-tooling`, `routing` | skills, dry-run, template, schema-v2 | Validate one or all skills against skill-conventions.md. |
| [`benchmarks/benchmark_agent_fleet.py`](./benchmarks/benchmark_agent_fleet.py) | `benchmarks`, `agents`, `fleet`, `simulation`, `dry-run` | fleet-benchmark, agent-dry-run, headroom, cache-invariance, isolation | Orchestrate dry-run validation sweeps and simulated multi-agent fleet benchmarks. |
| [`benchmarks/benchmark_retrieval.py`](./benchmarks/benchmark_retrieval.py) | `benchmarks`, `qmd`, `retrieval`, `rag`, `tokens` | retrieval-benchmark, mrr, precision, bm25, search-latency | Benchmark corpus retrieval accuracy, MRR, Precision@K, and token savings. |
| [`benchmarks/benchmark_task_eval.py`](./benchmarks/benchmark_task_eval.py) | `benchmarks`, `eval`, `pass-at-1`, `tasks`, `coding-agent` | task-eval, benchmark-suite, pass-rate, evaluation-scorecard | Evaluate autonomous coding agent task execution quality and pass@1 rates on standard suites. |
| [`benchmarks/benchmark_tool_efficiency.py`](./benchmarks/benchmark_tool_efficiency.py) | `benchmarks`, `cost-layers`, `headroom`, `ast-grep`, `compression`, `tokens` | tool-efficiency, compression-ratio, fact-retention, serialization | Benchmark tool output compression ratios, AST extraction fidelity, and serialization overhead. |
| [`benchmarks/estimate_agent_costs.py`](./benchmarks/estimate_agent_costs.py) | `benchmarks`, `cost-layers`, `agents`, `pricing`, `tokens` | cost-estimator, agent-cost, token-budget, kv-cache, model-tiers | Estimate token consumption, KV cache savings, and monetary costs for agents and paired skills. |
| [`benchmarks/run_benchmark_suite.py`](./benchmarks/run_benchmark_suite.py) | `benchmarks`, `fleet`, `cost-layers`, `eval`, `retrieval`, `orchestration` | benchmark-suite, run-benchmarks, combined-benchmark, master-eval | Unified master orchestrator to execute benchmark suites and generate consolidated reports. |
| [`change-history/append_change_history.py`](./change-history/append_change_history.py) | `change-history` | provenance, session-end, completion-gate | Append a change-history entry for the active year/quarter. |
| [`change-history/ensure_change_history_quarter.py`](./change-history/ensure_change_history_quarter.py) | `change-history` | provenance, scaffold | Ensure change-history year/quarter entries file exists. |
| [`cli/auth/keyring_vault.py`](./cli/auth/keyring_vault.py) | `harness`, `cli`, `auth`, `keyring`, `vault`, `security` | auth, keyring, vault, credential, security, wincred, keychain, libsecret | Universal Keyring & Encrypted File Vault for Harness CLI. |
| [`cli/auth/oauth_flows.py`](./cli/auth/oauth_flows.py) | `harness`, `cli`, `auth`, `oauth`, `pkce`, `anthropic`, `cursor`, `gemini`, `openai` | auth, oauth, pkce, loopback, device-flow, anthropic, cursor, gemini, openai | Universal OAuth 2.0 and Provider Authentication Flows for Harness CLI. |
| [`cli/harness.py`](./cli/harness.py) | `harness`, `cli`, `routing`, `isolation`, `auth`, `keyring` | harness, cli, status, branch, agent, pr, clean, auth, login, logout | In-repo Python CLI control plane for ai-router. |
| [`cli/registry.py`](./cli/registry.py) | `harness`, `cli`, `registry`, `multi-harness`, `switcher` | harness, registry, switch, scan, list, register, deregister | Harness registry manager for multi-harness discovery and switching. |
| [`cli/schema_adapter.py`](./cli/schema_adapter.py) | `harness`, `cli`, `schema`, `adapter`, `multi-harness` | harness, schema, adapter, areas, skills, agents | Dynamic schema inspection and adapter for multi-harness repositories. |
| [`cli/tui.py`](./cli/tui.py) | `harness`, `cli`, `tui`, `switcher`, `interactive` | harness, tui, switcher, switch, menu | Interactive Terminal User Interface (TUI) and Harness Switcher. |
| [`cost-layers/extract_ast_facts.py`](./cost-layers/extract_ast_facts.py) | `qmd`, `headroom`, `ast-grep` | structural-facts, outline, cost-layers | Extract structural facts via ast-grep outline/kind JSON (not full files). |
| [`cost-layers/validate_ast_grep.py`](./cost-layers/validate_ast_grep.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, structural-facts | Dry-run ast-grep precision retrieval and Headroom structural-fact survival. |
| [`cost-layers/validate_cost_layers.py`](./cost-layers/validate_cost_layers.py) | `qmd`, `headroom`, `ast-grep`, `cost-layers`, `research`, `benchmarks` | validation, dry-run, tokens, cost-layers, prompt-caching, webfetch, multi-trial, randomized | Run qmd + Headroom + ast-grep + prompt-caching + webfetch cost-layer dry runs and write a combined report. |
| [`cost-layers/validate_headroom_compression.py`](./cost-layers/validate_headroom_compression.py) | `headroom`, `qmd`, `cost-layers`, `benchmarks` | validation, dry-run, tokens, compression, multi-trial, randomized | Dry-run Headroom compression: token savings vs gold-fact accuracy with multi-trial randomization. |
| [`cost-layers/validate_prompt_caching.py`](./cost-layers/validate_prompt_caching.py) | `cost-layers`, `routing`, `agents` | prompt-caching, invariance, validation, dry-run, kv-cache | Validate prompt cache invariance across agent definitions and system instructions. |
| [`docs/run_markdownlint.py`](./docs/run_markdownlint.py) | `docs`, `markdown` | markdownlint, lint, markdownlint-cli2, dry-run | Run markdownlint-cli2 over repo Markdown (read-only by default). |
| [`docs/validate_context_budget.py`](./docs/validate_context_budget.py) | `docs`, `validation`, `cost-layers` | context-budget, tokens, agents-md, ingestibility, ceiling | Validate context budget ceilings and ingestibility rules across repository entry files. |
| [`docs/validate_router_structure.py`](./docs/validate_router_structure.py) | `docs`, `routing` | router, structure, validation, results-layout | Validate router structure (areas, catalogs, frontmatter, dispatch, results layout). |
| [`docs/validate_structure_fast.py`](./docs/validate_structure_fast.py) | `docs`, `validation`, `lint` | validate, structure, frontmatter, links, markdown | Fast structural validator for Markdown documents in ai-router. |
| [`github/resolve_github_path.py`](./github/resolve_github_path.py) | `github` | blob, main, path, url | Resolve local repo paths to GitHub https blob/tree URLs on main. |
| [`qmd/qmd_preflight.py`](./qmd/qmd_preflight.py) | `qmd` | preflight, index, onboarding, safety | Inspect reusable qmd state without creating or refreshing an index. |
| [`qmd/refresh_qmd_index.py`](./qmd/refresh_qmd_index.py) | `qmd` | index, embed, session-end, completion-gate | Refresh an existing local qmd index after explicit user approval. |
| [`qmd/setup_qmd_collections.py`](./qmd/setup_qmd_collections.py) | `qmd` | index, collections, embed, modular, areas | Set up missing qmd collections only after an explicit, inspected approval. |
| [`qmd/validate_qmd_retrieval.py`](./qmd/validate_qmd_retrieval.py) | `qmd`, `cost-layers`, `benchmarks`, `retrieval` | validation, dry-run, tokens, mrr, precision, multi-trial, randomized | Dry-run qmd retrieval: health, relevance, query permutation robustness, and token-cost efficiency. |
| [`repos/scaffold_public_repos.py`](./repos/scaffold_public_repos.py) | `repos`, `scaffold`, `github` | scaffold, public-repos, agent-skills, agent-standards, ai-research, wiki-template | Automated scaffolding CLI to initialize the 3 public Koality-Assured ecosystem repositories. |
| [`research/ai_vendor_briefing.py`](./research/ai_vendor_briefing.py) | `research`, `intelligence`, `briefing` | vendor-updates, flash-briefing, ai-vendors, primary-sources | Fetch, analyze, and synthesize AI vendor updates into flash briefings. |
| [`research/benchlm_lookup.py`](./research/benchlm_lookup.py) | `research`, `benchmarks`, `pricing`, `models` | benchlm, llm-benchmarks, model-pricing, price-performance, speed | Query, filter, and compare LLM benchmarks, pricing, and speed from BenchLM. |
| [`research/community_analyzer.py`](./research/community_analyzer.py) | `research`, `communities`, `socials`, `analysis`, `osint` | community-analyzer, subreddits, forums, sentiment, troubleshooting, osint | Community analyzer utility for querying, scoring, and synthesizing developer communities. |
| [`research/local_webfetch.py`](./research/local_webfetch.py) | `research`, `web`, `distillation`, `cost-layers`, `benchmarks` | webfetch, markdown, scrape, sanitize, multi-trial, randomized | Local Python web distillation utility for clean, boilerplate-free Markdown. |
| [`research/manage_social_registry.py`](./research/manage_social_registry.py) | `research`, `communities`, `socials`, `registry`, `maintenance` | social-registry, manage-communities, rubric-scoring, validate | Manage, score, and validate the community reliability catalog. |
| [`routing/generate_routing_index.py`](./routing/generate_routing_index.py) | `routing` | area-map, skill-dispatch, areas.yaml, index | Generate routing/area-map.md and routing/skill-dispatch.md. |
| [`routing/generate_script_index.py`](./routing/generate_script_index.py) | `routing` | script-discovery, index | Generate scripts/script-index.md from Python docstring tags. |
| [`routing/generate_skill_dispatch.py`](./routing/generate_skill_dispatch.py) | `routing`, `ai-tooling` | skills, dispatch, catalog | Generate routing/skill-dispatch.md from skill frontmatter. |
| [`routing/hybrid_dispatch.py`](./routing/hybrid_dispatch.py) | `routing`, `ai-tooling` | dispatch, hybrid-dispatch, bm25, fast-path, ambiguity-gate, router | 3-Tier Hybrid Dispatch Pipeline for skills, agents, and area routing. |
| [`routing/resolve_skill_graph.py`](./routing/resolve_skill_graph.py) | `routing`, `skills`, `dag` | skills, dependencies, topological-sort, execution-plan, prerequisites | Resolve skill dependency DAGs, topological ordering, and execution stages. |
| [`routing/spawn_worktree.py`](./routing/spawn_worktree.py) | `routing`, `isolation` | worktree, branch, concurrency, claims | Spawn, list, and remove isolated git worktrees for concurrent agent work. |
| [`sync/propose_core_update.py`](./sync/propose_core_update.py) | `sync`, `harness`, `propose` | propose-core-update, harness-core, pull-request, issue | Propose generic core improvements back to Koality-Assured/ai-harness-core. |
| [`sync/pull_harness_core.py`](./sync/pull_harness_core.py) | `sync`, `harness`, `pull` | pull-harness-core, core-update, spoke, allowlist | Pull allowlisted ai-harness-core updates into a domain spoke. |
| [`sync/scaffold_harness.py`](./sync/scaffold_harness.py) | `sync`, `harness`, `scaffold` | scaffold-harness, domain-router, harness-core, spoke | Scaffold a domain harness spoke from generic ai-harness-core. |
| [`sync/sync_and_push_downstreams.py`](./sync/sync_and_push_downstreams.py) | `sync`, `git`, `export`, `downstream` | sync-and-push, update-downstreams, multi-repo-publish, downstream-repo-update | Automated synchronization, sanitation, commit, and push engine for public downstream repositories. |
| [`sync/sync_public_repos.py`](./sync/sync_public_repos.py) | `sync`, `security`, `export` | sync, redaction, multi-repo, export, sanitize, wiki-template | Multi-repo synchronization and sanitization/redaction engine for public exports. |
| [`tests/test_benchmarks.py`](./tests/test_benchmarks.py) | `tests`, `benchmarks`, `cost-layers`, `agents`, `retrieval`, `fleet` | tests, test-benchmarks, cost-estimator, fleet-benchmark, mrr | Unit tests for empirical benchmarking and cost estimation tooling. |
| [`tests/test_harness_auth.py`](./tests/test_harness_auth.py) | `tests`, `harness`, `cli`, `auth`, `keyring`, `oauth`, `security` | tests, auth, keyring, vault, oauth, pkce, sanitization | Unit tests for Harness CLI Universal Auth Subsystem and Keyring Manager. |
| [`tests/test_harness_cli.py`](./tests/test_harness_cli.py) | `tests`, `harness`, `cli`, `isolation` | tests, harness-cli, status, branch, agent, pr, clean | Unit tests for the in-repo Harness CLI control plane. |
| [`tests/test_harness_core_sync.py`](./tests/test_harness_core_sync.py) | `tests`, `sync`, `harness` | tests, scaffold-harness, pull-harness-core, propose-core-update | Tests for core-spoke harness protocol scripts. |
| [`tests/test_harness_registry.py`](./tests/test_harness_registry.py) | `tests`, `harness`, `registry`, `switcher`, `tui` | tests, harness-registry, switch, scan, list, register, deregister | Unit tests for HarnessRegistry, multi-harness discovery, and schema adaptation. |
| [`tests/test_hybrid_dispatch.py`](./tests/test_hybrid_dispatch.py) | `tests`, `routing`, `ai-tooling` | tests, hybrid-dispatch, bm25, ambiguity-gate, schema-v2 | Unit tests for 3-Tier Hybrid Dispatch Pipeline and Schema V2 Indexing. |
| [`tests/test_local_webfetch.py`](./tests/test_local_webfetch.py) | `tests`, `research`, `webfetch`, `cost-layers` | tests, webfetch, distillation, sanitize | Unit tests for local_webfetch.py web distillation and prompt injection defense. |
| [`tests/test_pacing.py`](./tests/test_pacing.py) | `tests`, `pacing`, `quota`, `routing` | tests, pacing, quota-management | Unit tests for adaptive quota management and pacing helper. |
| [`tests/test_pretty_docs_security.py`](./tests/test_pretty_docs_security.py) | `tests`, `security`, `github` | tests, href, github-paths | Stdlib unit tests for href allow-list and GitHub path helpers. |
| [`tests/test_qmd_preflight.py`](./tests/test_qmd_preflight.py) | `tests`, `qmd` | qmd, preflight, onboarding | Unit tests for the non-mutating qmd lifecycle preflight. |
| [`tests/test_skill_graph.py`](./tests/test_skill_graph.py) | `tests`, `routing`, `skills`, `dag` | tests, dag, topological-sort, dependencies, prerequisites | Unit tests for skill dependency DAG resolution, topological ordering, and Schema V2 conventions. |
| [`tests/test_subagent_context_config.py`](./tests/test_subagent_context_config.py) | `tests`, `subagents`, `context`, `config` | tests, subagents, context-isolation, host-config | Unit tests for cross-host subagent context isolation and project-level settings. |
| [`tests/test_validate_agent.py`](./tests/test_validate_agent.py) | `tests`, `ai-tooling`, `agents`, `schema-v2` | tests, validate-agent, agents | Unit tests for Schema V2 agent validation. |
| [`tests/test_validate_context_budget.py`](./tests/test_validate_context_budget.py) | `tests`, `docs`, `validation`, `cost-layers` | tests, validate_context_budget, context-budget, tokens | Unit tests for validate_context_budget.py. |
| [`tests/test_validate_prompt_caching.py`](./tests/test_validate_prompt_caching.py) | `tests`, `cost-layers`, `prompt-caching` | tests, prompt-caching, invariance | Unit tests for validate_prompt_caching.py prompt KV-cache invariance linter. |
| [`tests/test_validate_router_structure.py`](./tests/test_validate_router_structure.py) | `tests`, `docs`, `validation`, `results` | tests, validate_router_structure, results-layout | Unit tests for router structure validator results-layout check. |
| [`tests/test_validate_skill.py`](./tests/test_validate_skill.py) | `tests`, `ai-tooling`, `skills`, `schema-v2` | tests, validate-skill, skills | Unit tests for Schema V2 skill validation. |
| [`tests/test_validate_structure_fast.py`](./tests/test_validate_structure_fast.py) | `tests`, `docs`, `validation` | tests, validate_structure_fast, markdown | Unit tests for fast structural validator. |

## By tag

- **adapter:** `cli/schema_adapter.py`
- **agents:** `ai-tooling/validate_agent.py`, `benchmarks/benchmark_agent_fleet.py`, `benchmarks/estimate_agent_costs.py`, `cost-layers/validate_prompt_caching.py`, `tests/test_benchmarks.py`, `tests/test_validate_agent.py`
- **ai-tooling:** `ai-tooling/model_memory.py`, `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `tests/test_hybrid_dispatch.py`, `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **analysis:** `research/community_analyzer.py`
- **anthropic:** `cli/auth/oauth_flows.py`
- **ast-grep:** `benchmarks/benchmark_tool_efficiency.py`, `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`
- **auth:** `cli/auth/keyring_vault.py`, `cli/auth/oauth_flows.py`, `cli/harness.py`, `tests/test_harness_auth.py`
- **benchmarks:** `benchmarks/benchmark_agent_fleet.py`, `benchmarks/benchmark_retrieval.py`, `benchmarks/benchmark_task_eval.py`, `benchmarks/benchmark_tool_efficiency.py`, `benchmarks/estimate_agent_costs.py`, `benchmarks/run_benchmark_suite.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `qmd/validate_qmd_retrieval.py`, `research/benchlm_lookup.py`, `research/local_webfetch.py`, `tests/test_benchmarks.py`
- **briefing:** `research/ai_vendor_briefing.py`
- **change-history:** `change-history/append_change_history.py`, `change-history/ensure_change_history_quarter.py`
- **cli:** `cli/auth/keyring_vault.py`, `cli/auth/oauth_flows.py`, `cli/harness.py`, `cli/registry.py`, `cli/schema_adapter.py`, `cli/tui.py`, `tests/test_harness_auth.py`, `tests/test_harness_cli.py`
- **coding-agent:** `benchmarks/benchmark_task_eval.py`
- **communities:** `research/community_analyzer.py`, `research/manage_social_registry.py`
- **compression:** `benchmarks/benchmark_tool_efficiency.py`
- **config:** `tests/test_subagent_context_config.py`
- **context:** `tests/test_subagent_context_config.py`
- **cost-layers:** `benchmarks/benchmark_tool_efficiency.py`, `benchmarks/estimate_agent_costs.py`, `benchmarks/run_benchmark_suite.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `cost-layers/validate_prompt_caching.py`, `docs/validate_context_budget.py`, `qmd/validate_qmd_retrieval.py`, `research/local_webfetch.py`, `tests/test_benchmarks.py`, `tests/test_local_webfetch.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_prompt_caching.py`
- **cursor:** `cli/auth/oauth_flows.py`
- **dag:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`
- **distillation:** `research/local_webfetch.py`
- **docs:** `docs/run_markdownlint.py`, `docs/validate_context_budget.py`, `docs/validate_router_structure.py`, `docs/validate_structure_fast.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`
- **downstream:** `sync/sync_and_push_downstreams.py`
- **dry-run:** `benchmarks/benchmark_agent_fleet.py`
- **eval:** `benchmarks/benchmark_task_eval.py`, `benchmarks/run_benchmark_suite.py`
- **export:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **fleet:** `benchmarks/benchmark_agent_fleet.py`, `benchmarks/run_benchmark_suite.py`, `tests/test_benchmarks.py`
- **gemini:** `cli/auth/oauth_flows.py`
- **git:** `sync/sync_and_push_downstreams.py`
- **github:** `github/resolve_github_path.py`, `repos/scaffold_public_repos.py`, `tests/test_pretty_docs_security.py`
- **harness:** `cli/auth/keyring_vault.py`, `cli/auth/oauth_flows.py`, `cli/harness.py`, `cli/registry.py`, `cli/schema_adapter.py`, `cli/tui.py`, `sync/propose_core_update.py`, `sync/pull_harness_core.py`, `sync/scaffold_harness.py`, `tests/test_harness_auth.py`, `tests/test_harness_cli.py`, `tests/test_harness_core_sync.py`, `tests/test_harness_registry.py`
- **headroom:** `benchmarks/benchmark_tool_efficiency.py`, `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`
- **intelligence:** `research/ai_vendor_briefing.py`
- **interactive:** `cli/tui.py`
- **isolation:** `cli/harness.py`, `routing/spawn_worktree.py`, `tests/test_harness_cli.py`
- **keyring:** `cli/auth/keyring_vault.py`, `cli/harness.py`, `tests/test_harness_auth.py`
- **lint:** `docs/validate_structure_fast.py`
- **maintenance:** `research/manage_social_registry.py`
- **markdown:** `docs/run_markdownlint.py`
- **memory:** `ai-tooling/model_memory.py`
- **models:** `research/benchlm_lookup.py`
- **multi-harness:** `cli/registry.py`, `cli/schema_adapter.py`
- **oauth:** `cli/auth/oauth_flows.py`, `tests/test_harness_auth.py`
- **openai:** `cli/auth/oauth_flows.py`
- **orchestration:** `benchmarks/run_benchmark_suite.py`
- **osint:** `research/community_analyzer.py`
- **pacing:** `tests/test_pacing.py`
- **pass-at-1:** `benchmarks/benchmark_task_eval.py`
- **pkce:** `cli/auth/oauth_flows.py`
- **pricing:** `benchmarks/estimate_agent_costs.py`, `research/benchlm_lookup.py`
- **prompt-caching:** `tests/test_validate_prompt_caching.py`
- **propose:** `sync/propose_core_update.py`
- **pull:** `sync/pull_harness_core.py`
- **qmd:** `benchmarks/benchmark_retrieval.py`, `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `qmd/qmd_preflight.py`, `qmd/refresh_qmd_index.py`, `qmd/setup_qmd_collections.py`, `qmd/validate_qmd_retrieval.py`, `tests/test_qmd_preflight.py`
- **quota:** `tests/test_pacing.py`
- **rag:** `benchmarks/benchmark_retrieval.py`
- **registry:** `cli/registry.py`, `research/manage_social_registry.py`, `tests/test_harness_registry.py`
- **repos:** `repos/scaffold_public_repos.py`
- **research:** `cost-layers/validate_cost_layers.py`, `research/ai_vendor_briefing.py`, `research/benchlm_lookup.py`, `research/community_analyzer.py`, `research/local_webfetch.py`, `research/manage_social_registry.py`, `tests/test_local_webfetch.py`
- **results:** `tests/test_validate_router_structure.py`
- **retrieval:** `benchmarks/benchmark_retrieval.py`, `benchmarks/run_benchmark_suite.py`, `qmd/validate_qmd_retrieval.py`, `tests/test_benchmarks.py`
- **routing:** `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `cli/harness.py`, `cost-layers/validate_prompt_caching.py`, `docs/validate_router_structure.py`, `routing/generate_routing_index.py`, `routing/generate_script_index.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `routing/resolve_skill_graph.py`, `routing/spawn_worktree.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pacing.py`, `tests/test_skill_graph.py`
- **scaffold:** `repos/scaffold_public_repos.py`, `sync/scaffold_harness.py`
- **schema:** `cli/schema_adapter.py`
- **schema-v2:** `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **security:** `cli/auth/keyring_vault.py`, `sync/sync_public_repos.py`, `tests/test_harness_auth.py`, `tests/test_pretty_docs_security.py`
- **simulation:** `benchmarks/benchmark_agent_fleet.py`
- **skills:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`, `tests/test_validate_skill.py`
- **socials:** `research/community_analyzer.py`, `research/manage_social_registry.py`
- **subagents:** `tests/test_subagent_context_config.py`
- **switcher:** `cli/registry.py`, `cli/tui.py`, `tests/test_harness_registry.py`
- **sync:** `sync/propose_core_update.py`, `sync/pull_harness_core.py`, `sync/scaffold_harness.py`, `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`, `tests/test_harness_core_sync.py`
- **tasks:** `benchmarks/benchmark_task_eval.py`
- **tests:** `tests/test_benchmarks.py`, `tests/test_harness_auth.py`, `tests/test_harness_cli.py`, `tests/test_harness_core_sync.py`, `tests/test_harness_registry.py`, `tests/test_hybrid_dispatch.py`, `tests/test_local_webfetch.py`, `tests/test_pacing.py`, `tests/test_pretty_docs_security.py`, `tests/test_qmd_preflight.py`, `tests/test_skill_graph.py`, `tests/test_subagent_context_config.py`, `tests/test_validate_agent.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_prompt_caching.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_skill.py`, `tests/test_validate_structure_fast.py`
- **tokens:** `benchmarks/benchmark_retrieval.py`, `benchmarks/benchmark_tool_efficiency.py`, `benchmarks/estimate_agent_costs.py`
- **tui:** `cli/tui.py`, `tests/test_harness_registry.py`
- **validation:** `docs/validate_context_budget.py`, `docs/validate_structure_fast.py`, `tests/test_validate_context_budget.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`
- **vault:** `cli/auth/keyring_vault.py`
- **web:** `research/local_webfetch.py`
- **webfetch:** `tests/test_local_webfetch.py`
