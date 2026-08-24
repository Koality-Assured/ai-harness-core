---
name: architecture-diagram
description: >-
  Produce architecture diagrams (prefer Mermaid) under results/diagrams/ or
  beside a host report. Use when drawing system/context/component views. Do not use for
  STRIDE threat-model assembly (threat-model) or pure narrative reports.
owner_agent: artifact-agent
rank: medium
isolation: mutate
---

# Architecture diagram

## When to use

General architecture diagrams for a named system or change. Prefer Mermaid; same storage rules as `mermaid-diagram`.

## When not to use

Threat-model package (`threat-model`). Single small mermaid-only ask that already fits `mermaid-diagram`. As-code module graphs that belong under `as-code-builder`.

## Criticality

Medium: prefer Mermaid; keep one diagram job per run folder unless attaching to a report.

## Source of truth

- Prefer Mermaid; shared notes: [`supporting/mermaid/agent-diagram-notes.md`](../../../supporting/mermaid/agent-diagram-notes.md) and [`mermaid-diagram`](../mermaid-diagram/SKILL.md)
- `python scripts/results/render_diagram.py --input <file> --topic <slug>`
- `python scripts/results/new_run_dir.py --family diagrams --topic <slug>`
- [`results/AGENTS.md`](../../../results/AGENTS.md)

## Isolation

`mutate`. Parent spawns `artifact-agent` with area `results`.

## How to use

1. Scope actors, trust boundaries, and components via parent prompt + `qmd search`.
2. `python scripts/results/new_run_dir.py --family diagrams --topic <slug>` → `results/diagrams/<topic>/<YYYY-MM-DD>/` unless attaching beside another report.
3. Prefer Mermaid; call `python scripts/results/render_diagram.py --input <file> --topic <slug> [--out <dir>]`.
4. Keep labels accurate; do not invent undocumented services.
5. Return paths and a one-line legend for the orchestrator.
6. Apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session to labels, legends, and layout descriptions — do not re-spawn artifact-agent for a quality pass on your own draft. Skip pure structural Mermaid with no human-facing copy.

## Dry run

```bash
python scripts/results/new_run_dir.py --family diagrams --topic <slug> --dry-run
python scripts/results/render_diagram.py --input <file> --topic <slug> --dry-run
```

Outline boxes/edges in chat; write/render only in a worktree.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No secrets or real account IDs in diagrams.

## Completion gates

Diagram paths returned to parent. Human-facing labels/legends passed anti-slop then humanizer (or skipped as out of scope). Memory if tracked.
