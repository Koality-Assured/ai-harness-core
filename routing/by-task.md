---
doc_kind: routing_map
canonical_id: by-task
topics: [routing, tasks, shortcuts, entrypoints]
generator: manual
---

# Routing by task (entry-point shortcuts)

Fast-path task-to-entrypoint mapping for common operational patterns. Match this table for 1-hop intent resolution, then load the target area's `AGENTS.md` strictly JIT.

When work requires mutating the repository, run worktree isolation (`python scripts/routing/spawn_worktree.py check --areas <csv> --json` -> `add`) before dispatching the specialist.

## Task dispatch matrix

| Task / Intent | Entry area | Default agent | Primary skill | Key verification / scripts |
| --- | --- | --- | --- | --- |
| **Adversarial audit & code review** | `scratch/` | [`detailed-activity`](../ai-tooling/agents/detailed-activity/AGENT.md) | [`antagonistic-review`](../ai-tooling/skills/meta/antagonistic-review/SKILL.md) | `python scripts/docs/validate_structure_fast.py --all` |
| **CWE / ATT&CK code-review report** | `results/reports/code-review/` | [`artifact-agent`](../ai-tooling/agents/artifact-agent/AGENT.md) | [`code-review-report`](../ai-tooling/skills/reporting/code-review-report/SKILL.md) | `python scripts/results/build_document.py` |
| **Author / revise standards or docs** | `docs/standards/` | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) | [`doc-builder`](../ai-tooling/skills/meta/doc-builder/SKILL.md) | `python scripts/docs/validate_router_structure.py` |
| **Markdown lint & format cleanup** | `docs/`, `references/` | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) | [`markdownlint`](../ai-tooling/skills/meta/markdownlint/SKILL.md) | `python scripts/docs/run_markdownlint.py` |
| **Deep research & empirical inquiry** | `research/`, `results/research/` | [`detailed-activity`](../ai-tooling/agents/detailed-activity/AGENT.md) | [`deep-research`](../ai-tooling/skills/meta/deep-research/SKILL.md) | Primary source verification against `references/valid-sources/` |
| **Fast git inspection & local branch sync** | Local checkout | [`git-fast-operator`](../ai-tooling/agents/git-fast-operator/AGENT.md) | [`git-basics`](../ai-tooling/skills/git/git-basics/SKILL.md) | `git status`, `git diff` |
| **GitHub PRs, issues, and remotes** | Remote repository | [`github-ops`](../ai-tooling/agents/github-ops/AGENT.md) | [`github-workflow`](../ai-tooling/skills/git/github-workflow/SKILL.md) | `gh auth status`, `gh pr status` |
| **Worktree isolation (mutate)** | `scratch/worktrees/` | [`router`](../ai-tooling/agents/router/AGENT.md) *(in-parent)* | [`isolate-work`](../ai-tooling/skills/meta/isolate-work/SKILL.md) | `python scripts/routing/spawn_worktree.py check --areas <csv> --json` |
| **Cost layers & context dry runs** | `supporting/`, `results/cost-layers/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`cost-layer-dry-run`](../ai-tooling/skills/cost-layers/cost-layer-dry-run/SKILL.md) | `python scripts/cost-layers/validate_cost_layers.py --dry-run` |
| **qmd search & collection health** | `supporting/qmd/` | [`qmd-ops`](../ai-tooling/agents/qmd-ops/AGENT.md) | [`qmd-usage`](../ai-tooling/skills/meta/qmd-usage/SKILL.md) | `python scripts/qmd/validate_qmd_retrieval.py` |
| **ast-grep structural fact extraction** | Codebase symbols | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`ast-grep`](../ai-tooling/skills/cost-layers/ast-grep/SKILL.md) | `python scripts/cost-layers/validate_ast_grep.py` |
| **Author / dry-run new skills** | `ai-tooling/skills/` | [`ai-tooling-ops`](../ai-tooling/agents/ai-tooling-ops/AGENT.md) | [`skill-builder`](../ai-tooling/skills/meta/skill-builder/SKILL.md) | `python scripts/ai-tooling/validate_skill.py` |
| **Author / revise agent definitions** | `ai-tooling/agents/` | [`ai-tooling-ops`](../ai-tooling/agents/ai-tooling-ops/AGENT.md) | [`agent-builder`](../ai-tooling/skills/meta/agent-builder/SKILL.md) | `python scripts/ai-tooling/validate_agent.py` |
| **Public downstream repo sync** | Public slice repos | [`repo-sync-ops`](../ai-tooling/agents/repo-sync-ops/AGENT.md) | [`sync-downstream-repos`](../ai-tooling/skills/meta/sync-downstream-repos/SKILL.md) | `python scripts/sync/sync_public_repos.py --dry-run` |
| **Scratch & worktree hygiene** | `scratch/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | [`scratch-cleanup`](../ai-tooling/skills/meta/scratch-cleanup/SKILL.md) | `python scripts/routing/spawn_worktree.py list --json` |
| **Community analysis & developer OSINT** | Reddit / X / HN / Discord | [`community-analyst`](../ai-tooling/agents/community-analyst/AGENT.md) | [`community-pattern-analysis`](../ai-tooling/skills/community/community-pattern-analysis/SKILL.md) | `python scripts/research/community_analyzer.py` |

---

## Related

- Full skill catalog: [`skill-dispatch.md`](./skill-dispatch.md)
- Specialist agent catalog: [`agent-dispatch.md`](./agent-dispatch.md)
- Area map: [`area-map.md`](./area-map.md)
- Worktree isolation: [`../ai-tooling/skills/isolate-work/SKILL.md`](../ai-tooling/skills/meta/isolate-work/SKILL.md)
