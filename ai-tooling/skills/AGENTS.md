# Skills AGENTS

Each skill is a subdirectory with `SKILL.md` (optional `references/`, `scripts/`, `assets/`). Authoring SoT: [`skill-conventions.md`](./skill-conventions.md).

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Parent **spawns** `owner_agent`; do not embed skill bodies here or rely on `.cursor/skills/` auto-invoke.

## Rules

- Update the source doc first when behavior changes; then the skill.
- Follow [`skill-conventions.md`](./skill-conventions.md) (frontmatter + required headings). Author via `skill-builder`.
- Keep `SKILL.md` short; link out instead of duplicating standards.
- Prefer calling tagged Python under `scripts/` from skills.
- Catalog: `python scripts/routing/generate_skill_dispatch.py` → [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md). README is human-thin only.
