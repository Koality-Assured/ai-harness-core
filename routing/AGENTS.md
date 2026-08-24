# Routing AGENTS (index)

Second hop after root [`../AGENTS.md`](../AGENTS.md). This folder is the generated next-step index, not a second AGENTS.md.

## Maps

1. **ALWAYS spawn** when a catalogued skill, area default, or cleanly delegable unit applies. Match [`skill-dispatch.md`](./skill-dispatch.md); isolate if `mutate`; spawn `owner_agent`. Do not load or execute the skill in the parent.
2. Else [`area-map.md`](./area-map.md) default agent (same isolate-then-spawn).
3. Open only that destination area’s `AGENTS.md` (loaded strictly JIT upon dispatch — never preload all area files).

Parent is coordinator/validator. It MAY do only undelegable work and MUST notify the human when that happens.

Rebuild after new folder types or skills: edit [`areas.yaml`](./areas.yaml) if needed, then `python scripts/routing/generate_routing_index.py`. Do not hand-edit the generated maps.

## Isolate then spawn

`python scripts/routing/spawn_worktree.py check --areas <csv> --json` then `add`. Procedure: [`../ai-tooling/skills/isolate-work/SKILL.md`](../ai-tooling/skills/isolate-work/SKILL.md).

## One-liners

- qmd: `qmd search --format json --min-score 0.5 -n 5 "<need>"` then `qmd get`
- Scripts: [`../scripts/script-index.md`](../scripts/script-index.md)
- Structured files: ast-grep. Bulky dumps: Headroom.

## Catalogs (not README)

- Skills → [`skill-dispatch.md`](./skill-dispatch.md)
- Areas → [`area-map.md`](./area-map.md)
- Specialists → `ai-tooling/agents/<id>/AGENT.md`
- Scripts → [`../scripts/script-index.md`](../scripts/script-index.md)
