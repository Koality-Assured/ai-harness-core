---
doc_kind: routing_map
canonical_id: by-task
topics: [routing, tasks, shortcuts, entrypoints]
generator: manual
---

# Routing by task (entry-point shortcuts)

Fast-path task-to-entrypoint mapping for common operational patterns. Match this table for 1-hop intent resolution, then load the target area's `AGENTS.md` strictly JIT.

When work requires mutating the repository, create one unique Git worktree and branch for the task with `python scripts/routing/spawn_worktree.py create --slug <task>` before dispatching the specialist. Concurrent tasks may edit overlapping areas; use ordinary Git and PR review to resolve collisions.

## Task dispatch matrix

| Task / Intent | Entry area | Default agent | Primary skill | Key verification / scripts |
| --- | --- | --- | --- | --- |
| **Adversarial audit & code review** | `scratch/` | [`detailed-activity`](../ai-tooling/agents/detailed-activity/AGENT.md) | [`antagonistic-review`](../ai-tooling/skills/meta/antagonistic-review/SKILL.md) | `python scripts/docs/validate_structure_fast.py --all` |
| **CWE / ATT&CK code-review report** | `results/reports/code-review/` | [`artifact-agent`](../ai-tooling/agents/artifact-agent/AGENT.md) | [`code-review-report`](../ai-tooling/skills/reporting/code-review-report/SKILL.md) | `python scripts/results/build_document.py --help` |
| **Author / revise standards or docs** | `docs/standards/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) | [`doc-builder`](../ai-tooling/skills/meta/doc-builder/SKILL.md) | `python scripts/docs/validate_router_structure.py` |
| **US primary-law locate, compare, interpret, or advisory court draft** | `legal-router` (domain spoke) | `legal-research-operator` *(on legal-router)* | Defer to spoke | Defer to spoke; licensed attorney review mandatory |
| **Markdown lint & format cleanup** | `docs/`, `references/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) | [`markdownlint`](../ai-tooling/skills/meta/markdownlint/SKILL.md) | `python scripts/docs/run_markdownlint.py` |
| **Deep research & empirical inquiry** | `research/`, `results/research/` | [`research-operator`](../ai-tooling/agents/research-operator/AGENT.md) | [`deep-research`](../ai-tooling/skills/meta/deep-research/SKILL.md) | Primary source verification against `references/valid-sources/` |
| **Fast git inspection & local branch sync** | Local checkout | [`git-fast-operator`](../ai-tooling/agents/git-fast-operator/AGENT.md) | [`git-basics`](../ai-tooling/skills/git/git-basics/SKILL.md) | `git status`, `git diff` |
| **GitHub PRs, issues, and remotes** | Remote repository | [`github-ops`](../ai-tooling/agents/github-ops/AGENT.md) | [`github-workflow`](../ai-tooling/skills/git/github-workflow/SKILL.md) | `gh auth status`, `gh pr status` |
| **Worktree isolation (mutate)** | `scratch/worktrees/` | [`router`](../ai-tooling/agents/router/AGENT.md) *(in-parent)* | [`isolate-work`](../ai-tooling/skills/meta/isolate-work/SKILL.md) | `python scripts/routing/spawn_worktree.py create --slug <task>` (see skill) |
| **Cost layers & context dry runs** | `supporting/`, `results/cost-layers/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`cost-layer-dry-run`](../ai-tooling/skills/cost-layers/cost-layer-dry-run/SKILL.md) | `python scripts/cost-layers/validate_cost_layers.py --dry-run` |
| **qmd search & collection health** | `supporting/qmd/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`qmd-usage`](../ai-tooling/skills/meta/qmd-usage/SKILL.md) | `python scripts/qmd/validate_qmd_retrieval.py` |
| **ast-grep structural fact extraction** | Codebase symbols | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`ast-grep`](../ai-tooling/skills/cost-layers/ast-grep/SKILL.md) | `python scripts/cost-layers/validate_ast_grep.py` |
| **Author / dry-run new skills** | `ai-tooling/skills/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`skill-builder`](../ai-tooling/skills/meta/skill-builder/SKILL.md) | `python scripts/ai-tooling/validate_skill.py` |
| **Author / revise agent definitions** | `ai-tooling/agents/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`agent-builder`](../ai-tooling/skills/meta/agent-builder/SKILL.md) | `python scripts/ai-tooling/validate_agent.py` |
| **Public downstream repo sync** | Public slice repos | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`sync-downstream-repos`](../ai-tooling/skills/meta/sync-downstream-repos/SKILL.md) | `python scripts/sync/sync_public_repos.py --dry-run` |
| **Scratch & worktree hygiene** | `scratch/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | [`scratch-cleanup`](../ai-tooling/skills/meta/scratch-cleanup/SKILL.md) | `python scripts/routing/spawn_worktree.py list` (see skill) |
| **Community analysis & developer OSINT** | Reddit / X / HN / Discord | [`research-operator`](../ai-tooling/agents/research-operator/AGENT.md) | [`community-pattern-analysis`](../ai-tooling/skills/community/community-pattern-analysis/SKILL.md) | `python scripts/research/community_analyzer.py` |
| **Legal analysis, contracts & primary-law research** | `legal-router` (domain spoke) | `legal-research-operator` *(on legal-router)* | `contract-clause-review`, `citation-verification` | Defer to spoke; licensed attorney review mandatory; zero hallucination check |
| **Financial modeling & quantitative advisory research** | `financial-advisement-router` (domain spoke) | `portfolio-strategy-operator` *(on financial-advisement-router)* | `portfolio-optimization`, `dcf-valuation-model` | Defer to spoke; strict Decimal math; non-discretionary advisory stamp required |
| **UI/UX engineering & accessibility verification** | `ui-ux-router` (domain spoke) | `design-system-architect` *(on ui-ux-router)* | `wcag-accessibility-audit`, `design-token-manage` | Defer to spoke; WCAG 2.2 AA non-regression; DTCG Format Module 2025.10 |
| **Game development & playtest balance simulation** | `game-dev-router` (domain spoke) | `game-systems-operator` *(on game-dev-router)* | `game-loop-spec`, `playtest-balance-harness` | Defer to private spoke; deterministic seeded sweeps; secpanic-idler isolated |
| **Local artistic generation & media synthesis** | `art-router` (domain spoke) | `artistic-production` *(on art-router)* | `video-generation`, `danbooru-tagging` | `harness video`, `harness prompt` (strictly operator opt-in; never default; outputs to `~/Videos/Generated`) |

---

## Related

- Full skill catalog: [`skill-dispatch.md`](./skill-dispatch.md)
- Specialist agent catalog: [`agent-dispatch.md`](./agent-dispatch.md)
- Area map: [`area-map.md`](./area-map.md)
- Worktree isolation: [`../ai-tooling/skills/meta/isolate-work/SKILL.md`](../ai-tooling/skills/meta/isolate-work/SKILL.md)
