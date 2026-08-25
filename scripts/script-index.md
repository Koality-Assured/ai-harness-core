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
| [`ai-tooling/validate_agent.py`](./ai-tooling/validate_agent.py) | `ai-tooling`, `routing`, `agents` | agents, validate, dry-run, schema-v2 | Validate one or all agents against Schema V2 frontmatter and agent conventions. |
| [`ai-tooling/validate_skill.py`](./ai-tooling/validate_skill.py) | `ai-tooling`, `routing` | skills, dry-run, template | Validate one or all skills against skill-conventions.md. |
| [`change-history/append_change_history.py`](./change-history/append_change_history.py) | `change-history` | provenance, session-end, completion-gate | Append a change-history entry for the active year/quarter. |
| [`change-history/ensure_change_history_quarter.py`](./change-history/ensure_change_history_quarter.py) | `change-history` | provenance, scaffold | Ensure change-history year/quarter entries file exists. |
| [`cost-layers/extract_ast_facts.py`](./cost-layers/extract_ast_facts.py) | `qmd`, `headroom`, `ast-grep` | structural-facts, outline, cost-layers | Extract structural facts via ast-grep outline/kind JSON (not full files). |
| [`cost-layers/validate_ast_grep.py`](./cost-layers/validate_ast_grep.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, structural-facts | Dry-run ast-grep precision retrieval and Headroom structural-fact survival. |
| [`cost-layers/validate_cost_layers.py`](./cost-layers/validate_cost_layers.py) | `qmd`, `headroom`, `ast-grep` | validation, dry-run, tokens, cost-layers | Run qmd + Headroom + ast-grep cost-layer dry runs and write a combined report. |
| [`cost-layers/validate_headroom_compression.py`](./cost-layers/validate_headroom_compression.py) | `headroom`, `qmd` | validation, dry-run, tokens, compression | Dry-run Headroom compression: token savings vs gold-fact accuracy. |
| [`docs/run_markdownlint.py`](./docs/run_markdownlint.py) | `docs`, `markdown` | markdownlint, lint, markdownlint-cli2, dry-run | Run markdownlint-cli2 over repo Markdown (read-only by default). |
| [`docs/validate_structure_fast.py`](./docs/validate_structure_fast.py) | `docs`, `validation`, `lint` | validate, structure, frontmatter, links, markdown | Fast structural validator for Markdown documents in ai-router. |
| [`docs/validate_wiki_structure.py`](./docs/validate_wiki_structure.py) | `docs`, `routing` | wiki, structure, validation | Validate router wiki structure (areas, catalogs, frontmatter, dispatch). |
| [`github/resolve_github_path.py`](./github/resolve_github_path.py) | `github` | blob, main, path, url | Resolve local repo paths to GitHub https blob/tree URLs on main. |
| [`qmd/refresh_qmd_index.py`](./qmd/refresh_qmd_index.py) | `qmd` | index, embed, session-end, completion-gate | Refresh the local qmd index after indexed Markdown changes (update then embed). |
| [`qmd/setup_qmd_collections.py`](./qmd/setup_qmd_collections.py) | `qmd` | index, collections, embed | Print qmd collection/context setup commands for this repo (and optionally run them). |
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
| [`tests/test_cloud_admin.py`](./tests/test_cloud_admin.py) | `tests`, `cloud`, `admin` | tests, cloud-admin, aws, gcp, azure | Unit tests for scripts/cloud/cloud_admin.py. |
| [`tests/test_google_suite.py`](./tests/test_google_suite.py) | `tests`, `google`, `drive`, `gmail`, `security`, `redaction` | — | Tests for Google Suite operations, administration, security gates, and downstream redaction. |
| [`tests/test_harness_core.py`](./tests/test_harness_core.py) | `tests`, `harness`, `core` | harness, tests, core, isolation, a2a, cache | Comprehensive unit tests for the decoupled bare-metal .harness engine. |
| [`tests/test_hybrid_dispatch.py`](./tests/test_hybrid_dispatch.py) | `tests`, `routing`, `ai-tooling` | tests, hybrid-dispatch, bm25, ambiguity-gate, schema-v2 | Unit tests for 3-Tier Hybrid Dispatch Pipeline and Schema V2 Indexing. |
| [`tests/test_pretty_docs_security.py`](./tests/test_pretty_docs_security.py) | `tests`, `security`, `github` | tests, href, github-paths | Stdlib unit tests for href allow-list and GitHub path helpers. |
| [`tests/test_public_llm_admin.py`](./tests/test_public_llm_admin.py) | `tests`, `llm`, `admin` | tests, public-llm-admin, openai, anthropic, gemini | Unit tests for scripts/llm/public_llm_admin.py. |
| [`tests/test_scaffold_public_repos.py`](./tests/test_scaffold_public_repos.py) | `tests`, `repos`, `scaffold` | tests, scaffold_public_repos, agent-skills, agent-standards, ai-research, wiki-template | Unit tests for public ecosystem repositories scaffolding automation. |
| [`tests/test_skill_graph.py`](./tests/test_skill_graph.py) | `tests`, `routing`, `skills`, `dag` | tests, dag, topological-sort, dependencies, prerequisites | Unit tests for skill dependency DAG resolution, topological ordering, and Schema V2 conventions. |
| [`tests/test_validate_agent.py`](./tests/test_validate_agent.py) | `tests`, `ai-tooling`, `agents`, `schema-v2` | tests, validate-agent, agents | Unit tests for Schema V2 agent validation. |
| [`tests/test_validate_structure_fast.py`](./tests/test_validate_structure_fast.py) | `tests`, `docs`, `validation` | tests, validate_structure_fast, markdown | Unit tests for fast structural validator. |

## By tag

- **admin:** `tests/test_cloud_admin.py`, `tests/test_public_llm_admin.py`
- **agents:** `ai-tooling/validate_agent.py`, `tests/test_validate_agent.py`
- **ai-tooling:** `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `tests/test_hybrid_dispatch.py`, `tests/test_validate_agent.py`
- **ast-grep:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`
- **change-history:** `change-history/append_change_history.py`, `change-history/ensure_change_history_quarter.py`
- **cloud:** `tests/test_cloud_admin.py`
- **core:** `tests/test_harness_core.py`
- **dag:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`
- **docs:** `docs/run_markdownlint.py`, `docs/validate_structure_fast.py`, `docs/validate_wiki_structure.py`, `tests/test_validate_structure_fast.py`
- **downstream:** `sync/sync_and_push_downstreams.py`
- **drive:** `tests/test_google_suite.py`
- **export:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **git:** `sync/sync_and_push_downstreams.py`
- **github:** `github/resolve_github_path.py`, `repos/scaffold_public_repos.py`, `tests/test_pretty_docs_security.py`
- **gmail:** `tests/test_google_suite.py`
- **google:** `tests/test_google_suite.py`
- **harness:** `tests/test_harness_core.py`
- **headroom:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`
- **isolation:** `routing/spawn_worktree.py`
- **lint:** `docs/validate_structure_fast.py`
- **llm:** `tests/test_public_llm_admin.py`
- **markdown:** `docs/run_markdownlint.py`
- **qmd:** `cost-layers/extract_ast_facts.py`, `cost-layers/validate_ast_grep.py`, `cost-layers/validate_cost_layers.py`, `cost-layers/validate_headroom_compression.py`, `qmd/refresh_qmd_index.py`, `qmd/setup_qmd_collections.py`, `qmd/validate_qmd_retrieval.py`
- **redaction:** `tests/test_google_suite.py`
- **repos:** `repos/scaffold_public_repos.py`, `tests/test_scaffold_public_repos.py`
- **routing:** `ai-tooling/validate_agent.py`, `ai-tooling/validate_skill.py`, `docs/validate_wiki_structure.py`, `routing/generate_routing_index.py`, `routing/generate_script_index.py`, `routing/generate_skill_dispatch.py`, `routing/hybrid_dispatch.py`, `routing/resolve_skill_graph.py`, `routing/spawn_worktree.py`, `tests/test_hybrid_dispatch.py`, `tests/test_skill_graph.py`
- **scaffold:** `repos/scaffold_public_repos.py`, `tests/test_scaffold_public_repos.py`
- **schema-v2:** `tests/test_validate_agent.py`
- **security:** `sync/sync_public_repos.py`, `tests/test_google_suite.py`, `tests/test_pretty_docs_security.py`
- **skills:** `routing/resolve_skill_graph.py`, `tests/test_skill_graph.py`
- **sync:** `sync/sync_and_push_downstreams.py`, `sync/sync_public_repos.py`
- **tests:** `tests/test_cloud_admin.py`, `tests/test_google_suite.py`, `tests/test_harness_core.py`, `tests/test_hybrid_dispatch.py`, `tests/test_pretty_docs_security.py`, `tests/test_public_llm_admin.py`, `tests/test_scaffold_public_repos.py`, `tests/test_skill_graph.py`, `tests/test_validate_agent.py`, `tests/test_validate_structure_fast.py`
- **validation:** `docs/validate_structure_fast.py`, `tests/test_validate_structure_fast.py`
