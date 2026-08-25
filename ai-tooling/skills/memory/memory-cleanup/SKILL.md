---
name: memory-cleanup
description: >-
  Archive or remove stale memory checkpoints under ai-tooling/memory/user/ and
  agent/ (Complete threads, duplicates, secrets, sprawl). Use when memory is
  noisy, a thread finished, or a file holds durable content that should be
  promoted out. Do not use to update an active thread (memory-adjust).
owner_agent: ai-tooling-ops
rank: medium
isolation: mutate
---

# Memory cleanup

## When to use

Complete/paused-forever threads, duplicate files, secrets accidentally written, or durable notes that never left memory.

## When not to use

Active thread still in flight (`memory-adjust`). Creating a checkpoint (`memory-create`).

## Criticality

Medium: hygiene. Critical if a secret landed in memory — remove immediately and rotate outside the repo if it was real.

## Source of truth

- [`ai-tooling/memory/AGENTS.md`](../../../memory/AGENTS.md)
- [`ai-tooling/memory/user/AGENTS.md`](../../../memory/user/AGENTS.md)
- [`ai-tooling/memory/agent/AGENTS.md`](../../../memory/agent/AGENTS.md)
- Root session-end gates (memory ≠ source of truth)

## Isolation

`mutate` on `ai-tooling`. Promote reusable bullets to `docs/` / `supporting/` / skills **before** deleting the only copy.

## How to use

1. Scan `ai-tooling/memory/user/**/*.md` and `ai-tooling/memory/agent/**/*.md` excluding README/AGENTS. Ignore `.gitkeep`.
2. For each: Active (leave or adjust), Paused (leave), Complete (promote then delete or keep a one-line tombstone if the human wants).
3. Promote durable lessons first.
4. Delete or empty files that duplicate source-area docs.
5. Never load `change-history/` to decide this.
6. Reject leftover flat `ai-tooling/memory/<thread>.md` files — move into `user/` or `agent/` or delete after promote.

## Dry run

Print the proposed keep/promote/delete list without writing. Do not delete in dry run.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

If a secret is present: stop, do not echo it, tell the human to rotate, delete the content. No PII.

## Completion gates

Source write-back for anything promoted. Change-history if many files moved. Memory file for this cleanup thread only if it spans sessions.
