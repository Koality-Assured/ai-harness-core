# Docs AGENTS

`docs/` is the corpus for decisions, requirements, reinforcement, and security MUST — especially `standards/` and [`agent-session-security.md`](./agent-session-security.md). Not the home for router/agent operating procedure (that lives in area AGENTS, skills, or `supporting/`).

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md).

## Rules

- Every durable page: kebab-case filename + YAML frontmatter (`doc_kind`, `canonical_id`, `purpose`, optional `rank`).
- Prefer updating an existing standard over near-duplicates.
- Keep controls portable — no employer/studio-specific org names in generalized standards.
- Standards under `standards/` are normative intent. Root `docs/*.md` should stay thin (security MUST + any remaining tagged corpus).
- `README.md` is human-only (root [`../AGENTS.md`](../AGENTS.md) High README rule).
- After add/remove/rename of indexed Markdown: `python scripts/qmd/refresh_qmd_index.py` (parent session-end gate — do not mint a specialist for it).
- Spawn `documentation-ops` / matching skill owner when a catalogued docs skill is material. Nested files MUST NOT undo root spawn-if-material.

## Maintenance (folded)

- Prefer actionable controls over title-only pages.
- Controlled purpose tags: `decision`, `requirement`, `reinforcement`, `security`.
- Stable filenames; `canonical_id` matches intent.
- Avoid destroying manual improvements unless clearly stale or contradictory.
- When content does not fit cleanly, ask rather than forcing the nearest folder.
- Semantic `topics:` sparingly (e.g. `identity-and-access`, `agents`, `cloudflare`, `github`); expand only under real taxonomy pressure.

## Layout

| Path | Contents |
| --- | --- |
| `standards/` | Generalized reusable standards |
| `standards/wiki-harness-template.md` | Generic template vs this fed instance (`ai-harness-core`) |
| `agent-session-security.md` | Critical session security MUST |
| `anti-slop.md` | Deliverable prose/UI quality (anti-slop + humanizer) |
| `README.md` | Human folder index only |
