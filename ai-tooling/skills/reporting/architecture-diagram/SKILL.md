---
schema_version: "2.0.0"
name: architecture-diagram
description: >-
  Produces architecture diagrams under results/diagrams/ or beside a host
  report. Use when drawing system/context/component views. Use Mermaid for
  explicit components and relationships that benefit
  from text source; use Excalidraw for direct spatial composition, sketching,
  annotations, or images. Do not use for STRIDE threat-model assembly
  (threat-model) or pure narrative reports.
owner_agent: artifact-agent
rank: medium
isolation: mutate
contracts:
  inputs:
    - Actors, trust boundaries, components, and topic slug
  outputs:
    - Architecture diagram in the selected format, with editable source and an export when required
---

# Architecture diagram

## When to use

General architecture diagrams for a named system or change. Choose Mermaid when the view is a graph-like model of named components, trust boundaries, and relationships, particularly when the source belongs in Markdown or Git review. Choose Excalidraw when the author needs direct spatial composition, freehand annotation, images, or a sketch-style explanation. These are recommendations inferred from the documented editing models, not comparative benchmark results. Shared evidence and publishing checks: [`format-selection.md`](../../../../supporting/diagramming/format-selection.md).

## When not to use

Threat-model package (`threat-model`). Single-format asks that already fit [`mermaid-diagram`](../mermaid-diagram/SKILL.md) or [`excalidraw-diagram`](../excalidraw-diagram/SKILL.md). As-code module graphs that belong under `as-code-builder`.

## Criticality

Medium: apply the documented format-selection policy; keep one diagram job per run folder unless attaching to a report.

## Source of truth

- Format policy: [`supporting/diagramming/format-selection.md`](../../../../supporting/diagramming/format-selection.md) (ai-router-only, optional provenance)
- Mermaid rendering: `supporting/mermaid/agent-diagram-notes.md` (`../../../../supporting/mermaid/agent-diagram-notes.md`; ai-router-only, optional provenance) and [`mermaid-diagram`](../mermaid-diagram/SKILL.md)
- Excalidraw authoring: [`excalidraw-diagram`](../excalidraw-diagram/SKILL.md)
- `python scripts/results/render_diagram.py --input <file> --topic <slug>`
- `python scripts/results/new_run_dir.py --family diagrams --topic <slug>`
- `results/AGENTS.md` (`../../../../results/AGENTS.md`; ai-router-only, optional provenance)

## Isolation

Standalone dispatch: Follow the destination's isolation and dispatch rules. Use a registered local operator or continue in-session when those rules permit; report a capability gap if no local path supports the work.

`mutate`. In ai-router, the parent spawns `artifact-agent` with area `results`.

## How to use

1. Scope actors, trust boundaries, and components via parent prompt + `qmd search`.
2. `python scripts/results/new_run_dir.py --family diagrams --topic <slug>` → `results/diagrams/<topic>/<YYYY-MM-DD>/` unless attaching beside another report.
3. Apply the format split in `supporting/diagramming/format-selection.md`: use Mermaid when the architecture is a text-defined model; use Excalidraw when direct visual composition is central. Follow the selected skill's storage and render/export steps.
4. Keep labels accurate; do not invent undocumented services.
5. Return paths and a one-line legend for the orchestrator.
6. Apply [`anti-slop`](../anti-slop/SKILL.md) then [`humanizer`](../humanizer/SKILL.md) in this session to labels, legends, and layout descriptions — do not re-spawn artifact-agent for a quality pass on your own draft. Skip pure structural Mermaid with no human-facing copy.

## Dry run

```bash
python scripts/results/new_run_dir.py --family diagrams --topic <slug> --dry-run
python scripts/results/render_diagram.py --input <file> --topic <slug> --dry-run
```

Read-only: outline the intended view, candidate format, and destination in chat; write/render/export only in a worktree.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No secrets or real account IDs in diagrams.

## Completion gates

Diagram paths returned to parent. Human-facing labels/legends passed anti-slop then humanizer (or skipped as out of scope). Memory if tracked.
