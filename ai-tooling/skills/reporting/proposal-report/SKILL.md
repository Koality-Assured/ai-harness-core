---
schema_version: "2.0.0"
name: proposal-report
description: >-
  Proposal report based on projects/ specs via build_document.py --type
  proposal. Use when turning a project slug into a proposal under
  results/reports/proposal/. Do not use for durable docs/ pages (doc-builder)
  or exec-only summaries (executive-report).
owner_agent: artifact-agent
rank: medium
isolation: mutate
contracts:
  inputs:
    - projects/ spec slug
  outputs:
    - Proposal report under results/reports/proposal/ with open decisions for the orchestrator
---

# Proposal report

## When to use

Build a proposal from an existing `projects/` spec (or human-named plan inputs).

## When not to use

Landing a standard in `docs/` (`doc-builder`). Short exec note (`executive-report`). Threat model (`threat-model`).

## Criticality

Medium: grounded in the project spec; do not invent scope.

## Source of truth

- `projects/<slug>/` via `qmd search` / `qmd get`
- `python scripts/results/new_run_dir.py --family reports --topic <slug> --type proposal`
- `python scripts/results/build_document.py --type proposal --sections <dir> --out results/reports/proposal/<topic>/<YYYY-MM-DD>/`

## Isolation

`mutate`. Parent spawns `artifact-agent` with area `results` (read `projects` as needed).

## How to use

1. Locate the project spec with `qmd search` — do not walk trees.
2. Map plan, repos, risks, and next actions from the spec into section files.
3. `python scripts/results/new_run_dir.py --family reports --topic <slug> --type proposal` → `results/reports/proposal/<topic>/<YYYY-MM-DD>/`.
4. `python scripts/results/build_document.py --type proposal --sections <dir> --out results/reports/proposal/<topic>/<YYYY-MM-DD>/`.
5. Return path + open decisions for the orchestrator.
6. After drafting, apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session — do not re-spawn artifact-agent for a quality pass on your own draft. Skip out-of-scope surfaces (code, logs, schemas).

## Dry run

```bash
python scripts/results/new_run_dir.py --family reports --topic <slug> --type proposal --dry-run
python scripts/results/build_document.py --type proposal --sections <dir> --out results/reports/proposal/<topic>/<YYYY-MM-DD>/ --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No secrets from project notes into the proposal.

## Completion gates

Proposal path. Human-readable prose passed anti-slop then humanizer (or skipped as out of scope). Memory if tracked.
