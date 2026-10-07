---
schema_version: "2.0.0"
name: git-basics
description: >-
  Simple git operations: fetch, status, log, diff, branch list, pull/sync on the
  current branch. Use when you need fast git inspection or sync. Do not use for commits, PRs,
  force-push, or merges to protected defaults. In ai-router, use `github-workflow` / `github-ops`;
  standalone repositories follow their documented Git and PR procedure or report a capability gap.
owner_agent: git-fast-operator
rank: low
isolation: mutate
contracts:
  inputs:
    - Allowed git op (fetch, status, log, diff, branch list, pull/sync) on the current branch
  outputs:
    - Summarized git state for the parent (not full log dumps)
---

# Git basics

## When to use

Fetch, status, log, diff, branch list, or pull/sync on the **current** branch.

## When not to use

Creating commits, opening PRs, `gh`, force-push, or merge to protected defaults. In ai-router, use `github-workflow` / `github-ops`; standalone repositories use their local workflow and protected-branch rules or report a capability gap. Complex branching strategy work.

## Criticality

Low: hygiene/inspection. Do not expand into commit/PR workflows.

## Source of truth

- Local git in the isolated worktree
- Branch discipline via `qmd` on supporting/github topic pages (not README for ops)
- `ai-tooling/agents/github-ops/AGENT.md` (`../../../agents/github-ops/AGENT.md`; ai-router-only, optional provenance) for off-ramp

## Isolation

Standalone dispatch: Follow the destination's Git isolation and PR rules. Use a registered local Git operator or continue in-session when permitted; report a capability gap if no local path supports the request.

`mutate` when updating refs or writing a short note under `results/`; stay in the parent worktree.

## How to use

1. Run only allowed ops: fetch, status, log, diff, branch list, pull/sync on current branch.
2. Summarize for the parent — do not dump full logs (Headroom/summarize if bulky).
3. If the ask needs commit/PR/force-push/merge, **stop**. In ai-router, recommend `github-workflow`; standalone repositories follow their local PR procedure or report a capability gap.

## Dry run

Read-only `git status` / `git log -5` in the worktree without mutating remotes.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No force-push, no tokens in output. In ai-router, commits/PRs stay on `github-ops`; standalone repositories follow their local PR workflow.

## Completion gates

Short status summary for parent. Confirm no commit/PR was created.
