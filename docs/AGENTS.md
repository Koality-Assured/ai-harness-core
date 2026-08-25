# Docs AGENTS

`docs/` is the corpus for decisions, requirements, reinforcement, and security MUST — especially `standards/` and [`agent-session-security.md`](./agent-session-security.md). Not the home for router/agent operating procedure (that lives in area AGENTS, skills, or `supporting/`).

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md).

## Rules

- **Protected Corpus of Record:** `docs/` contains protected, normative corpus-of-record material. Agents MUST NOT create, modify, or delete content under `docs/` based on inferred need. Drafts, proposals, investigations, and generated deliverables belong under `projects/`, `research/`, or `results/` until explicitly authorized for corpus promotion.
- Every durable page: kebab-case filename + YAML frontmatter (`doc_kind`, `canonical_id`, `purpose`, optional `rank`).
- Prefer updating an existing standard over near-duplicates.
- Keep controls portable — no employer/studio-specific org names in generalized standards.
- Standards under `standards/` are normative intent. Root `docs/*.md` should stay thin (security MUST + any remaining tagged corpus).
- `README.md` is human-only (root [`../AGENTS.md`](../AGENTS.md) High README rule).
- After add/remove/rename of indexed Markdown: `python scripts/qmd/refresh_qmd_index.py` (parent session-end gate — do not mint a specialist for it).
- Spawn `documentation-ops` / matching skill owner when a catalogued docs skill is material. Nested files MUST NOT undo root spawn-if-material.

## Folder-Level AGENTS.md 8-Point Schema

When authoring or maintaining area `AGENTS.md` files, define:
1. **Content ownership:** Which agent and area owns this content.
2. **Placement:** Exact layout and subfolder rules.
3. **Lifecycle:** How content advances, archives, or moves.
4. **Relationships:** Allowed and prohibited dependencies (e.g. `project -> supporting` one-way).
5. **Source-of-truth boundaries:** What this folder is SoT for, and what it is not.
6. **Validation:** Automated scripts/linters required before done.
7. **Escalation:** When to trigger the Ambiguity Gate or spawn research.
8. **Local exceptions:** Folder-specific overrides or deltas.

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
| `guidance/` | Repeatable operational playbooks and how-to guides |
| `standards/wiki-harness-template.md` | Generic template vs this fed instance (`ai-harness-core`) |
| `agent-session-security.md` | Critical session security MUST |
| `anti-slop.md` | Deliverable prose/UI quality (anti-slop + humanizer) |
| `README.md` | Human folder index only |
