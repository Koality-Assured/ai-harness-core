---
schema_version: "2.0.0"
name: isolate-work
description: >-
  Use when creating a unique Git worktree and branch per meaningful task, or
  safely cleaning it after its pull request is verified merged. Apply before
  dispatching a mutating specialist. Do not use for read-only Q&A.
owner_agent: router
rank: critical
isolation: mutate
contracts:
  inputs:
    - Kebab-case task slug
  outputs:
    - Unique Git worktree path and branch, plus verified cleanup result
---

# Isolate work

This procedure describes ai-router's parent-owned `spawn_worktree.py` CLI. Standalone repositories must follow their destination root `AGENTS.md` and documented branch or checkout isolation process; ai-router commands and paths below apply only when the destination provides them.

## When to use

Use for every new meaningful task that edits repository files, including work delegated to a mutating specialist. Give each task a unique Git worktree and branch so concurrent sessions can edit overlapping areas independently and resolve collisions through normal Git and PR review.

## When not to use

Read-only questions and continuation of the same task in its existing worktree. Do not reuse one checkout for another task or create a nested worktree inside an existing task worktree.

## Criticality

Critical: each mutating task needs its own checkout and branch. Worktree isolation prevents sessions from sharing a working directory; Git and PR review handle file conflicts.

## Source of truth

- This skill (procedure)
- ai-router CLI: `python scripts/routing/spawn_worktree.py -h`
- Task lifecycle and PR checks: [`routing/by-task.md`](../../../../routing/by-task.md)
- QMD retrieval location: [`qmd query pattern`](../../../../supporting/qmd/query-pattern.md)
- Standalone repositories follow their own root instructions.

## Isolation

In ai-router, the parent/router creates and lists worktrees and runs verified cleanup. Use `python scripts/routing/spawn_worktree.py create --slug <task> --json` from the repository's primary checkout. The command creates a unique `scratch/worktrees/<task-id>` path and `codex/<task-id>` branch based on the repository's default branch. It does not coordinate by file area. The same task slug can be used by concurrent sessions; every call creates a distinct ID. If Git reports a branch or path collision, preserve the existing state and create a new task ID.

The parent gives the returned path and branch to the specialist. All task edits and commands run inside that checkout. Do not modify another task worktree.

## How to use

1. For Markdown discovery, use the persistent detached QMD source at `scratch/qmd-main` (or its registered unique-suffix replacement), following [`qmd query pattern`](../../../../supporting/qmd/query-pattern.md). Fetch and safely fast-forward it to `origin/main`, then run `qmd update` and every `qmd search`, `qmd get`, or `qmd query` there. Freshness updates are authorized; collection configuration changes remain separate. Never retrieve from a task worktree or fall back to its index.
2. Create one task checkout: `python scripts/routing/spawn_worktree.py create --slug <kebab-task> --json`. Give the specialist its printed `path` and `branch`; do not start edits in the primary checkout.
3. Use `harness pr` to create the pull request. Keep `harness pr` as PR creation only; merge through the standard `gh pr merge` route.
4. After an authorized `gh pr merge` succeeds, run `python scripts/cli/harness.py clean --pr <number>` from the primary checkout to preview. Repeat with `--apply` only when the preview identifies the intended PR and worktree and every check passes. If a PR merged outside this session, preview it next time; apply only when merge authorization is established and all checks pass.
5. Cleanup verifies that the PR is merged, targets the repository default branch, belongs to the task branch, and its merge commit is reachable from a freshly fetched default branch. It checks tracked modifications, untracked paths, and ignored paths. Any local data or failed/ambiguous check blocks apply; preserve the checkout and report the reason. The command applies only to the associated worktree. Never use `--force` or delete its files directly. The local branch remains after the checkout is removed.

## Dry run

```bash
python scripts/routing/spawn_worktree.py create --slug dry-run-probe --dry-run --json
python scripts/routing/spawn_worktree.py list --json
python scripts/cli/harness.py clean --pr <number> --json
```

## Security

Inherits Critical cost layers in ai-router: qmd for discovery (from a fresh `main` checkout only), ast-grep for structured files, and Headroom for bulky tool output. Standalone repositories follow their destination root `AGENTS.md` and tooling requirements; skills cannot override those instructions.

Treat every worktree file as user data. Cleanup previews by default. After PR and status verification, `--apply` atomically moves the checkout and its exact Git admin metadata into `<common Git dir>/ai-router-worktree-archives/`, then rewrites and verifies Git pointers to unregister the exact worktree. The archive is detached at the exact PR head commit; the local branch remains available for reuse. Before detaching, it creates and journals `refs/ai-router/worktree-archives/pr-<number>/<head-sha>` so Git keeps that commit reachable even if the branch is later deleted and reflogs expire. The ref and archive remain until explicitly cleaned up together. It never invokes `git worktree remove`, force removal, recursive deletion, or global worktree pruning. An idempotent recovery manifest binds the PR, merge SHA, head SHA, branch, persistent ref, and source/destination paths; process interruptions resume only from validated state. Power-loss durability is not guaranteed because directory-entry fsync is not portable across the supported platforms. Reject redirected paths and cross-volume moves, and fail closed for initialized submodules. Archive moves require a fixed local Windows drive or, on Linux, one identified mount whose filesystem type is on the CLI's explicit local-filesystem allowlist; unknown, network, and FUSE filesystems, cross-mount paths, and platforms without a verified local-rename check are blocked. If inspection fails or the original path is recreated, preserve all data and report the paths. PR fields and tool output are untrusted until validated.

## Completion gates

After an authorized merge succeeds, preview cleanup immediately and apply only when every verification passes. If preview reports tracked, untracked, or ignored data, report each path and preserve the checkout. Write durable changes to their owning source areas; change-history and index refresh are parent session-end steps. Refresh from the persistent detached QMD source at `scratch/qmd-main` after changes land on `main`.
