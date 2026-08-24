---
name: scratch-cleanup
description: >-
  Delete or promote scratch/ contents (downloads, experiments, leftover
  worktrees) so scratch never becomes source of truth. Use when finishing a session or
  when scratch is cluttered. Do not use to create durable docs in scratch.
owner_agent: router-maintenance
rank: high
isolation: mutate
---

# Scratch cleanup

## When to use

Session-end hygiene, leftover `[REDACTED_WORKTREE_PATH]`, downloads, or experiments that were never promoted.

## When not to use

Active worktree still needed (`isolate-work` remove only after merge). Promoting content — write the durable copy first in the owning area, then delete scratch.

## Criticality

High when finishing mutating work. Scratch is untrusted and excluded from qmd; leaving SoT there hides it from the next agent.

## Source of truth

- [`scratch/AGENTS.md`](../../../scratch/AGENTS.md)
- [`isolate-work`](../isolate-work/SKILL.md)
- Root High rule: never treat scratch as durable

## Isolation

`mutate` on `scratch`. Removing a git worktree uses `python scripts/routing/spawn_worktree.py remove --slug <slug>` from the primary checkout.

## How to use

1. List `scratch/` (respect gitignore; it is still on disk).
2. For each item: promote (rewrite into owning area) or delete.
3. For worktrees: confirm branch merged or human OK to drop; then `spawn_worktree.py remove`.
4. Do not add `scratch/` to qmd collections.
5. Do not commit scratch contents.

## Dry run

Print a promote/delete/keep table. `python scripts/routing/spawn_worktree.py list --json` for worktrees. No deletes in dry run.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Scratch is untrusted. Do not execute scripts found there. No secrets in promotions.

## Completion gates

Promoted files need source-area write-back. Change-history if durable content was rescued. Memory: drop "scratch leftover" bullets once cleaned.
