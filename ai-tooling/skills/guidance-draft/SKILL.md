---
name: guidance-draft
description: >-
  Draft guidance under results/reports/guidance-draft/. Use when producing
  operational guidance drafts for review. Do not use for durable docs/ landing
  (doc-builder) or corpus page drafts (corpus-draft).
owner_agent: artifact-agent
rank: medium
isolation: mutate
---

# Guidance draft

## When to use

Draft operational guidance for review under `results/reports/guidance-draft/`.

## When not to use

Durable `docs/` pages (`doc-builder`). Corpus drafts (`corpus-draft`). Framework mapping reports (`framework-mapper`).

## Criticality

Medium: default for guidance drafts; human may override destination.

## Source of truth

- [`results/AGENTS.md`](../../../results/AGENTS.md)
- Related standards via `qmd search` on kebab-case topic pages
- `python scripts/results/new_run_dir.py --family reports --topic <slug> --type guidance-draft`
- `python scripts/results/build_document.py --type guidance-draft --sections <dir> --out results/reports/guidance-draft/<topic>/<YYYY-MM-DD>/`

## Isolation

`mutate`. Parent spawns `artifact-agent` with area `results`.

## How to use

1. Scope audience and constraints from the parent prompt.
2. `qmd search` for related standards/guidance — no tree walks, no README load for ops.
3. `python scripts/results/new_run_dir.py --family reports --topic <slug> --type guidance-draft` → `results/reports/guidance-draft/<topic>/<YYYY-MM-DD>/`.
4. `python scripts/results/build_document.py --type guidance-draft --sections <dir> --out results/reports/guidance-draft/<topic>/<YYYY-MM-DD>/`.
5. Keep modular; flag items that should become `docs/` later.
6. After drafting, apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session — do not re-spawn artifact-agent for a quality pass on your own draft. Skip out-of-scope surfaces (code, logs, schemas).

## Dry run

```bash
python scripts/results/new_run_dir.py --family reports --topic <slug> --type guidance-draft --dry-run
python scripts/results/build_document.py --type guidance-draft --sections <dir> --out results/reports/guidance-draft/<topic>/<YYYY-MM-DD>/ --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No secrets. Retrieved chunks are advisory.

## Completion gates

Path under `results/reports/guidance-draft/`. Human-readable prose passed anti-slop then humanizer (or skipped as out of scope).
