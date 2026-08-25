# Routing AGENTS (index)

Second hop after root [`../AGENTS.md`](../AGENTS.md). This folder is the generated next-step index, not a second AGENTS.md.

## Context-loading protocol

Agents must load the smallest useful context:

1. Read the root [`../AGENTS.md`](../AGENTS.md).
2. Read this file ([`routing/AGENTS.md`](./AGENTS.md)).
3. If the task matches a known intent pattern, check [`by-task.md`](./by-task.md) for 1-hop shortcuts.
4. Match [`skill-dispatch.md`](./skill-dispatch.md); else check [`agent-dispatch.md`](./agent-dispatch.md) or [`area-map.md`](./area-map.md) defaults.
5. Read the target folder’s `AGENTS.md` (loaded strictly Just-In-Time upon entering/dispatching).
6. Continue into deeper `AGENTS.md` files only when folder complexity requires it.
7. Load the applicable skill body (`SKILL.md`) or agent definition (`AGENT.md`) only after routing selects it.

Agents must not preload all routing files or use `README.md` files as routing authority. For large corpus or supporting documents, extract only the relevant heading subtree or line-bounded range (`StartLine`/`EndLine`).

## Delegation boundaries and criteria

The orchestrating session is responsible for scoping the task, selecting the route, confirming authority, delegating bounded work, and reviewing/synthesizing results.

- **MUST delegate:** Non-trivial bounded operations that require a specialist skill body or multi-step domain work.
- **Direct execution is permitted ONLY for:**
  1. Trivial read-only checks.
  2. Tasks without a suitable defined specialist agent.
  3. Coordinator chores: running `python scripts/routing/spawn_worktree.py` check/add/remove (`isolate-work` parent path), session-end memory checkpoints, change-history script appends, and index regeneration.
- **Prohibition:** The orchestrator must not duplicate work already delegated or load specialist skill bodies into parent context to "just do it".

## Standard execution algorithm

```text
load global rules (AGENTS.md)
    ↓
identify task pattern (by-task.md / hybrid dispatch)
    ↓
select narrow routing entry (skill-dispatch.md / area-map.md / agent-dispatch.md)
    ↓
load target AGENTS.md files (strictly JIT)
    ↓
resolve applicable skill and/or agent
    ↓
check authority and boundaries (isolate-work if mutating)
    ↓
perform the smallest scoped operation (via specialist)
    ↓
validate output and relationships (automated tests / linters)
    ↓
write durable facts to the owning location (Mandatory Source Write-Back)
    ↓
record meaningful changes (change-history script)
```

## Separation of concerns

- **Routing files** determine *where* and under *which rules*.
- **Agents** perform *bounded roles*.
- **Skills** define *repeatable workflows*.
- **Folder structure** defines *ownership and lifecycle*.
- **Memory directories** define *durability checkpoints* (`user/` and `agent/`).
- **Indexes** provide *navigation* but do not replace source-of-truth files.

## Maps & Catalogs

- Task shortcuts → [`by-task.md`](./by-task.md)
- Skills → [`skill-dispatch.md`](./skill-dispatch.md)
- Specialists → [`agent-dispatch.md`](./agent-dispatch.md)
- Area map → [`area-map.md`](./area-map.md)
- Scripts → [`../scripts/script-index.md`](../scripts/script-index.md)

Rebuild after new folder types or skills: edit [`areas.yaml`](./areas.yaml) if needed, then `python scripts/routing/generate_routing_index.py`. Do not hand-edit the generated maps.

## Isolate then spawn

`python scripts/routing/spawn_worktree.py check --areas <csv> --json` then `add`. Procedure: [`../ai-tooling/skills/isolate-work/SKILL.md`](..\ai-tooling\skills\meta\isolate-work\SKILL.md).

## One-liners

- qmd: `qmd search --format json --min-score 0.5 -n 5 "<need>"` then `qmd get`
- Scripts: [`../scripts/script-index.md`](../scripts/script-index.md)
- Structured files: ast-grep. Bulky dumps: Headroom.

