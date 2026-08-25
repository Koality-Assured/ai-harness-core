# Routing AGENTS (index)

Second hop after root [`../AGENTS.md`](../AGENTS.md). This folder is the generated next-step index, not a second AGENTS.md.

## Maps

1. **MUST spawn** when a catalogued skill matches **and** remaining work is material. Match [`skill-dispatch.md`](./skill-dispatch.md); isolate if `mutate`; spawn `owner_agent`. Do not load or execute the skill in the parent. Once `owner_agent` is known, parent discovery stops — do not load specialist `SKILL.md` to write the prompt. Needing the skill body is the spawn trigger. **Exception:** when the matched skill is `isolate-work`, the parent runs `python scripts/routing/spawn_worktree.py` check/add/remove itself and **MUST NOT spawn** `router-maintenance` for that CLI (even bundled with other chores).
2. Else [`area-map.md`](./area-map.md) default agent — same material-work gate, isolate-then-spawn. **MUST NOT spawn** for isolate-work CLI, coordinator chores, user-request-met leftovers, duplicate in-flight specialists, or host follow-up nags (root Critical Specialist dispatch).
3. Open only that destination area’s `AGENTS.md` (loaded strictly JIT upon dispatch — never preload all area files).

Parent is coordinator/validator. Isolate CLI (`spawn_worktree.py` check/add/remove) is the parent’s normal path. On subagent completion, audit the **user request** (not a parent-padded DoD). Host follow-up nags are not a mandate to mint specialists.

Rebuild after new folder types or skills: edit [`areas.yaml`](./areas.yaml) if needed, then `python scripts/routing/generate_routing_index.py`. Do not hand-edit the generated maps.

## Isolate then spawn

`python scripts/routing/spawn_worktree.py check --areas <csv> --json` then `add`. Procedure: [`../ai-tooling/skills/isolate-work/SKILL.md`](..\ai-tooling\skills\meta\isolate-work\SKILL.md).

## One-liners

- qmd: `qmd search --format json --min-score 0.5 -n 5 "<need>"` then `qmd get`
- Scripts: [`../scripts/script-index.md`](../scripts/script-index.md)
- Structured files: ast-grep. Bulky dumps: Headroom.

## Catalogs (not README)

- Skills → [`skill-dispatch.md`](./skill-dispatch.md)
- Areas → [`area-map.md`](./area-map.md)
- Specialists → `ai-tooling/agents/<id>/AGENT.md`
- Scripts → [`../scripts/script-index.md`](../scripts/script-index.md)
