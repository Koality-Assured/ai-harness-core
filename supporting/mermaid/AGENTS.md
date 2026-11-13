# Mermaid AGENTS

Durable tool recipes, rendering conventions, supported diagram syntax, and export pipelines for Mermaid diagrams.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational recipes, theme configurations, CLI execution patterns (`mmdc` / `render_diagram.py`), and syntax constraints for producing clear, accessible diagrams across repository documentation and report deliverables.

## Local Constraints

1. **Strict Output Fire-Wall:** `supporting/` is an input resource store; never deposit run outputs, rendered charts, SVG/PNG assets, or generated report diagrams here. All generated visual deliverables MUST route to `results/diagrams/<topic>/<date>/` (via `python scripts/results/render_diagram.py`) or land directly beside the host report under `results/`.
2. **One-Way Dependency Invariant:** Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
3. **Supported Diagram Types:** Only supported Mermaid diagram types are permitted:
   - `flowchart TD` / `flowchart LR` / `graph TD` / `graph LR` (control flow and simple architectures; prefer `flowchart` over legacy `graph`)
   - `sequenceDiagram` (request/response interactions across actors)
   - `stateDiagram-v2` or `stateDiagram` (state machine lifecycles)
   - `classDiagram` (type and module hierarchies)
   - `erDiagram` (entity relationships and data models)
   - `xychart-beta` (Cartesian metrics and data trends)
   - All other diagram types are unsupported in agent artifacts; use directed flowcharts or tables instead of unsupported schedules, timelines, or roadmaps.
4. **Syntax Sanitization & Quoting:** Node labels containing special characters (parentheses, brackets, colons, or punctuation) MUST be wrapped in double quotes (e.g. `id["Label (Extra Info)"]`). Avoid raw HTML tags in labels to prevent parse failures or Chromium render crashes.
5. **Rendering Script Binding:** Always invoke `python scripts/results/render_diagram.py` for rendering. Handle missing `mmdc` gracefully (fallback to Markdown source); never invent ad-hoc shell wrappers.
6. **No Secrets in Diagrams:** Never commit credentials, API keys, tokens, or live internal PII in diagram labels, comments, or configurations.

## Next Hops

- Agent diagram guidance and render flags: [`agent-diagram-notes.md`](./agent-diagram-notes.md)
- Shared format choice: [`../diagramming/format-selection.md`](../diagramming/format-selection.md)
- Mermaid diagram skill: [`../../ai-tooling/skills/reporting/mermaid-diagram/SKILL.md`](../../ai-tooling/skills/reporting/mermaid-diagram/SKILL.md)
- Architecture diagram skill: [`../../ai-tooling/skills/reporting/architecture-diagram/SKILL.md`](../../ai-tooling/skills/reporting/architecture-diagram/SKILL.md)
- Default specialist: [`../../ai-tooling/agents/artifact-agent/AGENT.md`](../../ai-tooling/agents/artifact-agent/AGENT.md)
