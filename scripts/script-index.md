---
doc_kind: routing_map
canonical_id: script-index
topics: [scripts, routing]
generated_at_utc: export
generator: scripts/routing/generate_script_index.py
---

# Script index

Generated from dest `scripts/` after wiki-template export (kept trees only). Do not hand-edit — run `python scripts/routing/generate_script_index.py` from the dest checkout after feeding scripts.

| Script | Tags | Hints | Summary |
| --- | --- | --- | --- |
| [`ai-tooling/model_memory.py`](./ai-tooling/model_memory.py) | `ai-tooling`, `memory` | model-memory, model-capability-memory, capability-retrieval, promote-model-learning | Search, validate, and propose promotion of model-family capability memory. |
| [`ai-tooling/validate_agent.py`](./ai-tooling/validate_agent.py) | `ai-tooling`, `routing`, `agents` | agents, validate, dry-run, schema-v2 | Validate one or all agents against Schema V2 frontmatter and agent conventions. |
| [`ai-tooling/validate_skill.py`](./ai-tooling/validate_skill.py) | `ai-tooling`, `routing` | skills, dry-run, template, schema-v2 | Validate one or all skills against skill-conventions.md. |
| [`change-history/append_change_history.py`](./change-history/append_change_history.py) | `change-history` | provenance, session-end, completion-gate | Append a change-history entry for the active year/quarter. |
| [`change-history/ensure_change_history_quarter.py`](./change-history/ensure_change_history_quarter.py) | `change-history` | provenance, scaffold | Ensure change-history year/quarter entries file exists. |
| [`cost-layers/extract_ast_facts.py`](./cost-layers/extract_ast_facts.py) | `qmd`, `headroom`, `ast-grep` | structural-facts, outline, cost-layers | Extract structural facts via ast-grep outline/kind JSON (not full files). |
| [`cost-layers/validate_ast_grep.py`](./cost-layers/validate_ast_grep.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, structural-facts | Dry-run ast-grep precision retrieval and Headroom structural-fact survival. |
| [`cost-layers/validate_cost_layers.py`](./cost-layers/validate_cost_layers.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, cost-layers | Run qmd + Headroom + ast-grep cost-layer dry runs and write a combined report. |
| [`cost-layers/validate_headroom_compression.py`](./cost-layers/validate_headroom_compression.py) | `headroom`, `qmd` | validation, dry-run, tokens, compression | Dry-run Headroom compression: token savings vs gold-fact accuracy. |
| [`docs/run_markdownlint.py`](./docs/run_markdownlint.py) | `docs`, `markdown` | markdownlint, lint, markdownlint-cli2, dry-run | Run markdownlint-cli2 over repo Markdown (read-only by default). |
| [`docs/validate_router_structure.py`](./docs/validate_router_structure.py) | `docs`, `routing` | router, structure, validation, results-layout | Validate router structure (areas, catalogs, frontmatter, dispatch, results layout). |
| [`docs/validate_structure_fast.py`](./docs/validate_structure_fast.py) | `docs`, `validation`, `lint` | validate, structure, frontmatter, links, markdown | Fast structural validator for Markdown documents in ai-router. |
| [`docs/validate_wiki_structure.py`](./docs/validate_wiki_structure.py) | `docs`, `routing` | wiki, structure, validation, results-layout | Validate router wiki structure (areas, catalogs, frontmatter, dispatch, results layout). |
| [`github/resolve_github_path.py`](./github/resolve_github_path.py) | `github` | blob, main, path, url | Resolve local repo paths to GitHub https blob/tree URLs on main. |
| [`qmd/qmd_preflight.py`](./qmd/qmd_preflight.py) | `qmd` | preflight, index, onboarding, safety | Inspect reusable qmd state without creating or refreshing an index. |
| [`qmd/refresh_qmd_index.py`](./qmd/refresh_qmd_index.py) | `qmd` | index, embed, session-end, completion-gate | Refresh an existing local qmd index after explicit user approval. |
| [`qmd/setup_qmd_collections.py`](./qmd/setup_qmd_collections.py) | `qmd` | index, collections, embed | Set up missing qmd collections only after an explicit, inspected approval. |
| [`qmd/validate_qmd_retrieval.py`](./qmd/validate_qmd_retrieval.py) | `qmd` | validation, dry-run, tokens | Dry-run qmd retrieval: health, relevance, and token-cost comparison. |
| [`repos/scaffold_public_repos.py`](./repos/scaffold_public_repos.py) | `repos`, `scaffold`, `github` | scaffold, public-repos, agent-skills, agent-standards, ai-research, wiki-template | Automated scaffolding CLI to initialize the 3 public Koality-Assured ecosystem repositories. |
| [`routing/generate_routing_index.py`](./routing/generate_routing_index.py) | `routing` | area-map, skill-dispatch, areas.yaml, index | Generate routing/area-map.md and routing/skill-dispatch.md. |
| [`routing/generate_script_index.py`](./routing/generate_script_index.py) | `routing` | script-discovery, index | Generate scripts/script-index.md from Python docstring tags. |
| [`routing/generate_skill_dispatch.py`](./routing/generate_skill_dispatch.py) | `routing`, `ai-tooling` | skills, dispatch, catalog | Generate routing/skill-dispatch.md from skill frontmatter. |
| [`routing/hybrid_dispatch.py`](./routing/hybrid_dispatch.py) | `routing`, `ai-tooling` | dispatch, hybrid-dispatch, bm25, fast-path, ambiguity-gate, router | 3-Tier Hybrid Dispatch Pipeline for skills, agents, and area routing. |
| [`routing/resolve_skill_graph.py`](./routing/resolve_skill_graph.py) | `routing`, `skills`, `dag` | skills, dependencies, topological-sort, execution-plan, prerequisites | Resolve skill dependency DAGs, topological ordering, and execution stages. |
| [`routing/spawn_worktree.py`](./routing/spawn_worktree.py) | `routing`, `isolation` | worktree, branch, concurrency, claims | Spawn, list, and remove isolated git worktrees for concurrent agent work. |
| [`sync/sync_and_push_downstreams.py`](./sync/sync_and_push_downstreams.py) | `sync`, `git`, `export`, `downstream` | sync-and-push, update-downstreams, multi-repo-publish, downstream-repo-update | Automated synchronization, sanitation, commit, and push engine for public downstream repositories. |
| [`sync/sync_public_repos.py`](./sync/sync_public_repos.py) | `sync`, `security`, `export` | sync, redaction, multi-repo, export, sanitize, wiki-template | Multi-repo synchronization and sanitization/redaction engine for public exports. |
| [`tests/test_confluence_sync.py`](./tests/test_confluence_sync.py) | `tests`, `confluence`, `sync`, `drift`, `storage-format` | tests, confluence-sync, confluence-drift | Unit and integration tests for Confluence knowledge-space sync and bi-directional drift reconciliation. |
| [`tests/test_hybrid_dispatch.py`](./tests/test_hybrid_dispatch.py) | `tests`, `routing`, `ai-tooling` | tests, hybrid-dispatch, bm25, ambiguity-gate, schema-v2 | Unit tests for 3-Tier Hybrid Dispatch Pipeline and Schema V2 Indexing. |
| [`tests/test_pacing.py`](./tests/test_pacing.py) | `tests`, `pacing`, `quota`, `routing` | tests, pacing, quota-management | Unit tests for adaptive quota management and pacing helper. |
| [`tests/test_pretty_docs_security.py`](./tests/test_pretty_docs_security.py) | `tests`, `security`, `github` | tests, href, github-paths | Stdlib unit tests for href allow-list and GitHub path helpers. |
| [`tests/test_qmd_preflight.py`](./tests/test_qmd_preflight.py) | `tests`, `qmd` | qmd, preflight, onboarding | Unit tests for the non-mutating qmd lifecycle preflight. |
| [`tests/test_skill_graph.py`](./tests/test_skill_graph.py) | `tests`, `routing`, `skills`, `dag` | tests, dag, topological-sort, dependencies, prerequisites | Unit tests for skill dependency DAG resolution, topological ordering, and Schema V2 conventions. |
| [`tests/test_validate_agent.py`](./tests/test_validate_agent.py) | `tests`, `ai-tooling`, `agents`, `schema-v2` | tests, validate-agent, agents | Unit tests for Schema V2 agent validation. |
| [`tests/test_validate_router_structure.py`](./tests/test_validate_router_structure.py) | `tests`, `docs`, `validation`, `results` | tests, validate_router_structure, results-layout | Unit tests for router structure validator results-layout check. |
| [`tests/test_validate_skill.py`](./tests/test_validate_skill.py) | `tests`, `ai-tooling`, `skills`, `schema-v2` | tests, validate-skill, skills | Unit tests for Schema V2 skill validation. |
| [`tests/test_validate_structure_fast.py`](./tests/test_validate_structure_fast.py) | `tests`, `docs`, `validation` | tests, validate_structure_fast, markdown | Unit tests for fast structural validator. |
| [`tests/test_validate_wiki_structure.py`](./tests/test_validate_wiki_structure.py) | `tests`, `docs`, `validation`, `results` | tests, validate_wiki_structure, results-layout | Unit tests for wiki structure validator results-layout check. |

## By tag

- **agents:** `ai-tooling/validate_agent.py`, `tests/test_validate_agent.py`
- **ai-tooling:** `ai-tooling/model_memory.py`, `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `tests/test_hybrid_dispatch.py`, `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **ast-grep:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`
- **change-history:** `change-history/append_change_history.py`, `change-history/ensure_change_history_quarter.py`
- **confluence:** `tests/test_confluence_sync.py`
- **dag:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`
- **docs:** `docs/run_markdownlint.py`, `docs/validate_router_structure.py`, `docs/validate_structure_fast.py`, `docs/validate_wiki_structure.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`, `tests/test_validate_wiki_structure.py`
- **downstream:** `sync/sync_and_push_downstreams.py`
- **drift:** `tests/test_confluence_sync.py`
- **export:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **git:** `sync/sync_and_push_downstreams.py`
- **github:** `github/resolve_github_path.py`, `repos/scaffold_public_repos.py`, `tests/test_pretty_docs_security.py`
- **headroom:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`
- **isolation:** `routing/spawn_worktree.py`
- **lint:** `docs/validate_structure_fast.py`
- **markdown:** `docs/run_markdownlint.py`
- **memory:** `ai-tooling/model_memory.py`
- **pacing:** `tests/test_pacing.py`
- **qmd:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `qmd/qmd_preflight.py`, `qmd/refresh_qmd_index.py`, `qmd/setup_qmd_collections.py`, `qmd/validate_qmd_retrieval.py`, `tests/test_qmd_preflight.py`
- **quota:** `tests/test_pacing.py`
- **repos:** `repos/scaffold_public_repos.py`
- **results:** `tests/test_validate_router_structure.py`, `tests/test_validate_wiki_structure.py`
- **routing:** `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `docs/validate_router_structure.py`, `docs/validate_wiki_structure.py`, `routing/generate_routing_index.py`, `routing/generate_script_index.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `routing/resolve_skill_graph.py`, `routing/spawn_worktree.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pacing.py`, `tests/test_skill_graph.py`
- **scaffold:** `repos/scaffold_public_repos.py`
- **schema-v2:** `tests/test_validate_agent.py`, `tests/test_validate_skill.py`
- **security:** `sync/sync_public_repos.py`, `tests/test_pretty_docs_security.py`
- **skills:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`, `tests/test_validate_skill.py`
- **storage-format:** `tests/test_confluence_sync.py`
- **sync:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`, `tests/test_confluence_sync.py`
- **tests:** `tests/test_confluence_sync.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pacing.py`, `tests/test_pretty_docs_security.py`, `tests/test_qmd_preflight.py`, `tests/test_skill_graph.py`, `tests/test_validate_agent.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_skill.py`, `tests/test_validate_structure_fast.py`, `tests/test_validate_wiki_structure.py`
- **validation:** `docs/validate_structure_fast.py`, `tests/test_validate_router_structure.py`, `tests/test_validate_structure_fast.py`, `tests/test_validate_wiki_structure.py`
