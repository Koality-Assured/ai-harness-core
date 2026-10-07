# Skills AGENTS

Each skill is a subdirectory with `SKILL.md` (optional `references/`, `scripts/`, `assets/`). Authoring SoT: [`skill-conventions.md`](./skill-conventions.md).

This file is maintained at `ai-router/ai-tooling/skills/` and may be exported as `skills/` into a standalone repository. That export omits `ai-router`'s root and area `AGENTS.md` files, routing catalog, and generator. Relative links and commands below that target those files apply only in the full `ai-router` checkout; downstream trees follow their destination repository's own instructions and catalog, when provided.

## Standalone export contract

The skills-only export is not a copy of the ai-router harness. Any reference to a path outside this skills tree, including a `scripts/...` command, an `owner_agent` value, a router catalog, or a router-only validator, is optional ai-router provenance and must not be a standalone prerequisite. Keep excluded source references as non-clickable code paths labeled ai-router-only; keep links between files inside this skills tree relative and clickable.

Standalone users follow the destination repository's root `AGENTS.md` or `CLAUDE.md`, local dispatch/catalog rules, and local validation tools. For provider operations, use an authorized destination tool or the official vendor CLI/API and its documentation. If none can perform a required operation, stop and report the specific capability gap; do not claim the task succeeded. Use the destination's output convention instead of ai-router result helpers.

`owner_agent` is ai-router routing metadata. A standalone dispatcher may map it to a registered local agent or ignore it; no exported skill may require an ai-router agent. Explicit agent invocations in a skill need a local dispatch path or a clear capability-gap outcome. Preserve each skill's inline safety and quality requirements; for omitted ai-router policy references, apply the destination's local policy and official vendor guidance.

Root Critical cost layers and references to the root `AGENTS.md` apply only in a full ai-router checkout. Standalone users follow destination instructions and tools; use local search, structured-file, and output-compression capabilities where available, and report a capability gap when a required check cannot be performed safely.

Ingest simply; do not duplicate skills or paste root Critical. In the full `ai-router` checkout, follow the root `AGENTS.md` and area `ai-tooling/AGENTS.md`, spawn `owner_agent` when catalogued skill work is material, and preserve the root spawn-if-material rule. Standalone downstream repositories follow their own `AGENTS.md` and dispatch rules. Do not embed skill bodies here or rely on `.cursor/skills/` auto-invoke.

## Rules

- Update the source doc first when behavior changes; then the skill.
- Follow [`skill-conventions.md`](./skill-conventions.md) (frontmatter + required headings). Author via `skill-builder`.
- Keep `SKILL.md` short; link out instead of duplicating standards.
- In the full `ai-router` checkout, prefer calling tagged Python scripts from root `scripts/`. Such commands are ai-router-only examples in a standalone export; use destination-local tools or official vendor clients instead, and report a capability gap if neither is available.
- Catalog in the full `ai-router` checkout only: run `python scripts/routing/generate_skill_dispatch.py` to update `routing/skill-dispatch.md`. Both the generator and catalog are outside the skills-only export; do not run that command in a downstream skills repository. README is human-thin only.
