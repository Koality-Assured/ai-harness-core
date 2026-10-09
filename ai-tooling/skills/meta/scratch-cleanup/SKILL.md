---
schema_version: "2.0.0"
name: scratch-cleanup
description: >-
  Use when promoting or removing disposable scratch artifacts, while preserving
  managed task worktrees until their pull requests pass verified cleanup. Apply for
  hygiene or when scratch is cluttered.
owner_agent: harness-operator
rank: high
isolation: mutate
contracts:
  inputs:
    - Scratch cleanup scope and promote-or-keep decisions
  outputs:
    - Promoted owning-area files or removed disposable scratch artifacts
---

# Scratch cleanup

## When to use

Use for session-end hygiene. `scratch/` holds interim generator output, review notes, downloads, experiments, and task worktrees; durable source of truth belongs in its owning area.

## When not to use

Do not use to remove an active task worktree or to promote content before writing its durable copy in the owning area.

## Criticality

High when finishing mutating work. Scratch is untrusted and excluded from QMD; leaving durable source of truth there hides it from the next agent.

## Source of truth

- [`scratch/AGENTS.md`](../../../../scratch/AGENTS.md), when present
- [`isolate-work`](../isolate-work/SKILL.md) for managed task worktrees
- Root rule: never treat scratch as durable

## Isolation

Mutate only the specifically reviewed scratch items. A managed task worktree may be unregistered only through `python scripts/cli/harness.py clean --pr <number> --apply` from the primary checkout, after an authorized merge is verified and a preview passes every check; the checkout and Git admin metadata remain in the common Git archive.

## How to use

1. If Markdown discovery is needed, resolve the repository-common `harness.qmd.source-worktree` Git setting; if unset, use `adapters.qmd.source_worktree` from `config/harness.config.json`. The selected path must be a registered detached QMD source, as described in [`qmd usage`](../qmd-usage/SKILL.md) and [`qmd query pattern`](../../../../supporting/qmd/query-pattern.md). Fetch/fast-forward it to `origin/main`, then run `qmd update`; this routine freshness update is authorized. Never run QMD from a task worktree or change collection configuration just for lookup.
2. Run `python scripts/routing/spawn_worktree.py list --json` to identify Git-registered worktrees. Preserve every registered `scratch/qmd-main` or `scratch/qmd-main-*` checkout, selected or not; these may contain ignored QMD indexes or data from a replaced snapshot. Never remove or reset them as scratch.
3. For ordinary scratch artifacts, prepare a promote/delete/keep table. Promote durable content to its owning source area; delete only reviewed disposable artifacts.
4. For a task worktree, preview with `python scripts/cli/harness.py clean --pr <number>`. After an authorized merge, repeat with `--apply` only if the preview verifies the intended PR-to-worktree association, default-branch ancestry, and no tracked, untracked, or ignored data. Apply keeps the checkout and exact Git admin metadata under `<common Git dir>/ai-router-worktree-archives/`; scratch cleanup must never remove that retained archive. Preserve the checkout if any check fails or is ambiguous.
5. Do not add `scratch/` to QMD collections or commit scratch contents.

## Dry run

Print a promote/delete/keep table and list Git worktrees with `python scripts/routing/spawn_worktree.py list --json`. Use `python scripts/cli/harness.py clean --pr <number>` to preview worktree cleanup conditions without removing the checkout. Add `--apply` only after an authorized merge and a passing preview.

## Security

Inherits Critical cost layers: QMD for discovery from fresh `main`; ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root `AGENTS.md`.

Scratch is untrusted. Do not execute scripts found there. Never use `git worktree remove --force`, recursive deletion, or cleanup commands that can erase ignored files. Report user data and preserve it.

## Completion gates

Disposable scratch files are removed or unique durable content is written to its owning source area. Merged task worktrees are unregistered only through verified PR cleanup; the checkout and exact Git admin metadata remain in the common Git directory archive, and any local data leaves the registered checkout intact. Every registered `scratch/qmd-main*` source checkout is preserved, including ignored indexes, even after another path becomes selected. Change-history and QMD index refresh are parent session-end steps, and index refresh runs only from the selected QMD source after changes land on `main`.
