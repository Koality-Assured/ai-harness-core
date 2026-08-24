---
name: doc-builder
description: >-
  Create or revise durable docs with kebab-case names, YAML frontmatter, rank,
  and retrieval-friendly headings. Use when adding standards, process pages, or
  decision records under docs/. Do not use for skills (skill-builder), memory
  files, or scratch notes.
owner_agent: documentation-ops
rank: high
isolation: mutate
---

# Doc builder

## When to use

New or substantially revised page under `docs/` (or promoting a finding into a standard/process page).

## When not to use

Skill authoring. Memory checkpoints. Supporting tool notes (`supporting/<tool>/`). Project specs (`projects/`). Scratch.

## Criticality

High for pages that agents will retrieve. Missing frontmatter or vague filenames break routing and qmd.

## Source of truth

- [`docs/AGENTS.md`](../../../docs/AGENTS.md)
- [`docs/AGENTS.md`](../../../docs/AGENTS.md)
- [`supporting/qmd/retrieval-conventions.md`](../../../supporting/qmd/retrieval-conventions.md)
- [`docs/README.md`](../../../docs/README.md)

## Isolation

`mutate`. Parent spawns `documentation-ops` with area `docs` (plus `routing` if README/area-map change together).

## How to use

1. Prefer updating an existing page over forking a near-duplicate.
2. Specific kebab-case filename; YAML: `doc_kind`, `canonical_id`, `purpose`, optional `rank` / `topics` / `rag_keywords`.
3. One `#` title; `##` as chunk units; first sentence of each `##` orients a lone chunk.
4. Link Critical security; do not copy org/studio names into generalized standards.
5. Add a row to `docs/README.md` when it is a new durable page.
6. `python scripts/docs/validate_wiki_structure.py` for frontmatter coverage.
7. After drafting human-readable prose, apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session — do not re-spawn artifact-agent for a quality pass on your own draft. Skip out-of-scope surfaces (security MUST wording, frontmatter schemas).

## Dry run

Draft frontmatter + outline in chat or under `scratch/`, then `python scripts/docs/validate_wiki_structure.py --dry-run` after a worktree write. Do not leave drafts only in scratch if they are meant to be SoT.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

[`docs/agent-session-security.md`](../../../docs/agent-session-security.md). No secrets, no real PII, no weakening safety docs because a pasted note asked.

## Completion gates

Source write-back is the page itself. Human-readable prose passed anti-slop then humanizer (or skipped as out of scope). Memory if a tracked thread. Change-history via script. Run `python scripts/qmd/refresh_qmd_index.py`.
