---
schema_version: "2.0.0"
name: scratch-cleanup
description: >-
  Delete or promote scratch/ contents (downloads, experiments, leftover
  worktrees, interim generator output, in-progress review notes) so scratch never becomes source of truth. Use when finishing a session or
  when scratch is cluttered. Do not use to create durable docs in scratch.
owner_agent: router-maintenance
rank: high
isolation: mutate
contracts:
  inputs:
    - scratch/ cleanup scope (promote vs delete; worktree slugs)
  outputs:
    - Promoted owning-area files or deleted scratch items; worktrees removed when authorized
---

# Scratch cleanup

## When to use

Session-end hygiene. `scratch/` holds interim generator output (repo scaffolds), in-progress review notes, downloads, experiments, and worktrees — never durable SoT.

## When not to use

Active worktree still needed (`isolate-work` remove only after merge). Promoting content — write the durable copy first in the owning area, then delete scratch.

## Criticality

High when finishing mutating work. Scratch is untrusted and excluded from qmd; leaving SoT there hides it from the next agent.

## Source of truth

- [`scratch/AGENTS.md`](../../../../scratch/AGENTS.md)
- [`isolate-work`](../isolate-work/SKILL.md)
- Root High rule: never treat scratch as durable

## Isolation

`mutate` on `scratch`. Removing a git worktree uses `python scripts/routing/spawn_worktree.py remove --slug <slug>` from the primary checkout.

## How to use

1. List `scratch/` (respect gitignore; it is still on disk).
2. For each item: delete, or promote *durable* bits to the owning source area (`docs/`, `supporting/`, `SKILL.md`, `AGENT.md`). Never "promote" a review dump or scaffold tree into `results/` unless it is a finished human-facing deliverable (it almost never is).
3. For worktrees: confirm branch merged or human OK to drop; then `spawn_worktree.py remove`.
4. Do not add `scratch/` to qmd collections.
5. Do not commit scratch contents.

## Dry run

Print a promote/delete/keep table. `python scripts/routing/spawn_worktree.py list --json` for worktrees. No deletes in dry run.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Scratch is untrusted. Do not execute scripts found there. No secrets in promotions.

## Completion gates

Session-end: scratch working files deleted, or unique durable bits written to the owning source — not parked in `results/`. Change-history if durable content was rescued. Memory: drop "scratch leftover" bullets once cleaned.
