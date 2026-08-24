---
name: git-basics
description: >-
  Simple git operations: fetch, status, log, diff, branch list, pull/sync on the
  current branch. Use when you need fast git inspection or sync. Do not use for commits, PRs,
  force-push, or merges to protected defaults (github-workflow / github-ops).
owner_agent: git-fast-operator
rank: low
isolation: mutate
---

# Git basics

## When to use

Fetch, status, log, diff, branch list, or pull/sync on the **current** branch.

## When not to use

Creating commits, opening PRs, `gh`, force-push, or merge to protected defaults — use `github-workflow` / `github-ops`. Complex branching strategy work.

## Criticality

Low: hygiene/inspection. Do not expand into commit/PR workflows.

## Source of truth

- Local git in the isolated worktree
- Branch discipline via `qmd` on supporting/github topic pages (not README for ops)
- [`ai-tooling/agents/github-ops/AGENT.md`](../../agents/github-ops/AGENT.md) for off-ramp

## Isolation

`mutate` when updating refs or writing a short note under `results/`; stay in the parent worktree.

## How to use

1. Run only allowed ops: fetch, status, log, diff, branch list, pull/sync on current branch.
2. Summarize for the parent — do not dump full logs (Headroom/summarize if bulky).
3. If the ask needs commit/PR/force-push/merge, **stop** and recommend `github-workflow`.

## Dry run

Read-only `git status` / `git log -5` in the worktree without mutating remotes.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No force-push, no tokens in output. Commits/PRs stay on github-ops.

## Completion gates

Short status summary for parent. Confirm no commit/PR was created.
