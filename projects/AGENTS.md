# Projects AGENTS

Specs for initiatives — plan, repos, research/results pointers — not chronicles.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Flat taxonomy: each initiative lives in `projects/<slug>/README.md` with YAML frontmatter `status: proposed | active | ongoing | completed`. Human-requested non-spec notes: [`notes/`](./notes/) (see nested [`notes/AGENTS.md`](./notes/AGENTS.md)).

## Status values (YAML frontmatter)

| Status | Meaning |
| --- | --- |
| `proposed` | Evaluation / pitch |
| `active` | In flight |
| `ongoing` | Long-lived maintenance |
| `completed` | Done; freeze history elsewhere |

## Rules

- Flat slug folder: `projects/<slug>/README.md`.
- Required YAML frontmatter:

  ```yaml
  ---
  status: active # proposed | active | ongoing | completed
  owner: router
  repos: [ai-router]
  ---
  ```

- Required sections in `README.md`: Intent, Plan / next actions, Related repos & paths, Research & results pointers, Decisions (links to docs/), Open questions.
- Do not store ongoing history here — point at `research/`, `results/`; provenance via change-history scripts.
- Update `status:` field in YAML frontmatter on status change (do not move directories; eliminates dead relative link churn).
- Nested `AGENTS.md` only if a subfolder's process truly diverges (`notes/` does).
- **`notes/`:** human drop for notes that are not initiative specs / not pitches. Created only by human request; one kebab-case Markdown file per concern (dated prefix OK). Not a chronicle, not `research/`, not `docs/` standards, not `actionable/` intake. Promote to `projects/<slug>/` when a note becomes a real initiative.
- If a skill owns the work, parent spawns that `owner_agent`.
