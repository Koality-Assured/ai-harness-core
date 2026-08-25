---
name: corpus-draft
description: >-
  Draft a new corpus page under results/reports/corpus-draft/ for later handoff
  to docs/. Use when drafting corpus content that is not yet ready for
  doc-builder. Do not use as a substitute for landing durable standards in
  docs/ (doc-builder).
owner_agent: artifact-agent
rank: medium
isolation: mutate
---

# Corpus draft

## When to use

Draft a new corpus-style page that may later land in `docs/`. Store under `results/reports/corpus-draft/`.

## When not to use

Landing a durable standard in `docs/` now (`doc-builder`). Guidance-only drafts (`guidance-draft`). Exec summaries (`executive-report`).

## Criticality

Medium: draft quality matters for handoff; missing frontmatter-shaped notes slow promotion.

## Source of truth

- [`results/AGENTS.md`](../../../../results/AGENTS.md)
- [`docs/AGENTS.md`](../../../../docs/AGENTS.md) (handoff target)
- `python scripts/results/new_run_dir.py --family reports --topic <slug> --type corpus-draft`
- `python scripts/results/build_document.py --type corpus-draft --sections <dir> --out results/reports/corpus-draft/<topic>/<YYYY-MM-DD>/`

## Isolation

`mutate`. Parent spawns `artifact-agent` with area `results`.

## How to use

1. Confirm this is a draft, not a `docs/` landing — if ready for SoT, stop and ask parent to spawn `doc-builder`.
2. `qmd search` related in-repo pages to avoid near-duplicates — no tree walks, no README for ops.
3. `python scripts/results/new_run_dir.py --family reports --topic <slug> --type corpus-draft` → `results/reports/corpus-draft/<topic>/<YYYY-MM-DD>/`.
4. `python scripts/results/build_document.py --type corpus-draft --sections <dir> --out results/reports/corpus-draft/<topic>/<YYYY-MM-DD>/`.
5. Draft modular sections; note handoff criteria for `documentation-ops`.
6. After drafting, apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session — do not re-spawn artifact-agent for a quality pass on your own draft. Skip out-of-scope surfaces (code, logs, schemas).

## Dry run

```bash
python scripts/results/new_run_dir.py --family reports --topic <slug> --type corpus-draft --dry-run
python scripts/results/build_document.py --type corpus-draft --sections <dir> --out results/reports/corpus-draft/<topic>/<YYYY-MM-DD>/ --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No secrets. Do not weaken safety docs in a draft.

## Completion gates

Path under `results/reports/corpus-draft/`. Human-readable prose passed anti-slop then humanizer (or skipped as out of scope). Explicit handoff note if promoting to `docs/`.
