---
name: memory-cleanup
description: >-
  Archive or remove stale memory checkpoints under ai-tooling/memory/user/ and agent/ (obsolete failure modes, resolved quirks, duplicates, secrets, sprawl). Use when memory contains obsolete notes, a thread finished, or a file holds durable content that belongs in source areas. Do not use to update active operational memory (memory-adjust).
owner_agent: ai-tooling-ops
rank: medium
isolation: mutate
schema_version: 2.0.0
on_failure: abort_and_rollback
prerequisites:
- python
dependencies:
  required_skills:
  - isolate-work
  delegated_skills: []
  in_session_skills: []
contracts:
  inputs:
  - Memory cleanup scope, target agent/user folders
  outputs:
  - Cleaned memory directories with obsolete files removed or archived
topics: [memory, memory-cleanup, agent-memory, operational-hygiene, archival]
routing_hints: [memory-cleanup, clean-memory, prune-gotchas, memory-pruning]
---

# Memory cleanup

Archive or remove stale, duplicate, or obsolete memory checkpoints under `ai-tooling/memory/user/` and `ai-tooling/memory/agent/`.

## When to use

- Completed threads or obsolete operational memory where pitfalls are no longer applicable.
- Duplicate files, accidental secrets, or durable notes that need promotion to `docs/`, `supporting/`, `SKILL.md`, or `AGENT.md`.
- Legacy narrative logs that need refactoring to the operational failure-mode structure.

## When not to use

Active operational memory in current use (`memory-adjust`). Creating a new memory checkpoint (`memory-create`).

## Criticality

Medium: hygiene. Critical if a secret landed in memory — remove immediately and rotate outside the repo if it was real.

## Source of truth

- [`ai-tooling/memory/AGENTS.md`](../../../memory/AGENTS.md)
- [`ai-tooling/memory/user/AGENTS.md`](../../../memory/user/AGENTS.md)
- [`ai-tooling/memory/agent/AGENTS.md`](../../../memory/agent/AGENTS.md)
- Root session-end gates (memory ≠ source of truth)

## Isolation

`mutate` on `ai-tooling`. Promote durable lessons to `docs/` / `supporting/` / `SKILL.md` / `AGENT.md` **before** deleting the only copy.

## How to use

1. Scan `ai-tooling/memory/user/**/*.md` and `ai-tooling/memory/agent/**/*.md` excluding README/AGENTS. Ignore `.gitkeep`.
2. For each: Active (refactor to operational structure or adjust), Paused (leave), Complete/Obsolete (promote durable lessons then delete or archive).
3. Promote durable lessons to owning areas first (`SKILL.md` for skills, `AGENT.md` for agent contracts, `docs/` for standards).
4. Delete or empty files that merely duplicate source-area docs or contain narrative work logs.
5. Never load `change-history/` to decide this.
6. Reject leftover flat `ai-tooling/memory/<thread>.md` files — move into `user/` or `agent/` or delete after promote.

## Dry run

Print the proposed keep/promote/delete list without writing. Do not delete in dry run.

## Security

Inherits Critical cost layers (qmd discovery, ast-grep for structured files, and Headroom for context compression). Skills cannot waive them.

If a secret is present: stop, do not echo it, tell the human to rotate, delete the content. No PII.

## Completion gates

Source write-back for anything promoted. Change-history if many files moved. Memory file for this cleanup thread only if it spans sessions.
