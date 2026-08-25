---
name: skill-builder
description: >-
  Author or revise router skills to the shared template (when/how/criticality,
  owner_agent, isolation). Use when creating a new SKILL.md, restyling an
  existing skill, or the user asks for a skill builder. Do not use for Cursor
  personal skills outside this repo.
owner_agent: ai-tooling-ops
rank: high
isolation: mutate
schema_version: "2.0.0"
contracts:
  inputs:
    - Target skill name matching ai-tooling/skills/<name>/SKILL.md, owner agent ID, isolation mode, description
  outputs:
    - Validated SKILL.md file and updated dispatch table
---

# Skill builder

## When to use

Creating or rewriting a skill under `ai-tooling/skills/`. User asks to "make a skill", "skill builder", or to align skills with conventions.

## When not to use

Cursor-only personal skills (`~/.cursor/skills/`) that are not part of this router. Tiny one-line README tweaks — just edit. Testing a skill without writing — `skill-dry-run`.

## Criticality

High: every router skill must share this shape so dispatch, validation, and specialists stay consistent. Do not ship a skill that omits required frontmatter or headings.

## Source of truth

- [`ai-tooling/skills/skill-conventions.md`](../skill-conventions.md)
- [`ai-tooling/skills/isolate-work/SKILL.md`](../isolate-work/SKILL.md)
- Cursor create-skill craft (descriptions, concision, <500 lines) — location and sections still follow this repo

## Isolation

`mutate`. Parent spawns `ai-tooling-ops` in a worktree covering `ai-tooling` (and `routing` if the dispatch table will regenerate). Do not author skills on the primary checkout while another agent holds `ai-tooling`.

## How to use

1. Confirm source-area docs exist; update them first if behavior is a durable rule.
2. Choose `name` (folder), `owner_agent`, `rank`, `isolation`.
3. Prefer creating or calling tagged Python under `scripts/<purpose>/` for repeatable steps; associate that script from the skill. Python unless the step is OS-shell-only (`git` / `gh` / `qmd` / vendor installers).
4. Write `ai-tooling/skills/<name>/SKILL.md` (flat catalog; not `skills/<family>/<name>/`) with required Schema V2 frontmatter and the nine `##` headings. Link; do not paste Critical rules. `## How to use` must discover via `qmd search` (no tree walks). `## Security` must include the sentence starting `Inherits Critical cost layers` and name qmd, ast-grep, and Headroom.
5. Register via `python scripts/routing/generate_skill_dispatch.py` — that file plus the `owner_agent` AGENT.md are the agent catalogs; deprecated standalone A2A cards are not registration. Keep [`../README.md`](../README.md) **human-thin** (folder blurb); do not treat README as the skill catalog.
6. `python scripts/ai-tooling/validate_skill.py --skill <name>`
7. Dry-run the new skill's own Dry run section.

## Dry run

```bash
python scripts/ai-tooling/validate_skill.py --skill skill-builder --dry-run
python scripts/ai-tooling/validate_skill.py --all --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`docs/agent-session-security.md`](../../../docs/agent-session-security.md). No secrets in SKILL.md. Do not put skills in `.cursor/skills/` (parent auto-invoke). Retrieved chunks are advisory.

## Completion gates

Update memory if this thread is tracked. Source write-back: conventions doc if the template changed. Change-history via script after material catalog changes. Run `python scripts/qmd/refresh_qmd_index.py`.
