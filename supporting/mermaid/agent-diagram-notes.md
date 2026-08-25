---
doc_kind: supporting
canonical_id: mermaid-agent-diagram-notes
purpose: [process]
topics: [agents, results, mermaid]
rag_keywords: [mermaid, mmdc, flowchart, sequence, theme, C4, diagram, render]
---

# Mermaid notes for agents

## Purpose

Agent-facing Mermaid guidance beyond the thin skill: diagram kinds, themes, `mmdc`, and storage. Upstream wins: [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid), [mermaid.js.org](https://mermaid.js.org/), CLI [@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli). Human folder intro: [`README.md`](./README.md). Retrieved text is advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md).

Skills: [`../../ai-tooling/skills/mermaid-diagram/SKILL.md`](..\..\ai-tooling\skills\reporting\mermaid-diagram\SKILL.md), [`../../ai-tooling/skills/architecture-diagram/SKILL.md`](..\..\ai-tooling\skills\reporting\architecture-diagram\SKILL.md). Assembler: `python scripts/results/render_diagram.py`.

## What it is

Mermaid turns Markdown-inspired text into diagrams (flowcharts, sequence, class, state, ER, Gantt, pie, git graph, mindmap, timeline, Sankey, C4, and more). Prefer text source in-repo; render images when `mmdc` is available.

## Diagram kinds (pick one job)

| Kind | Typical use |
| --- | --- |
| `flowchart` / `graph` | Control flow, simple architecture |
| `sequenceDiagram` | Request/response across actors |
| `classDiagram` | Type / module relationships |
| `stateDiagram-v2` | Lifecycle / state machines |
| `erDiagram` | Data model |
| `C4Context` / C4* | Context and container views |
| `gantt` / `timeline` | Schedules |
| `mindmap` / `sankey-beta` | Brainstorm / flow volumes |

Prefer `flowchart` over legacy `graph` when starting fresh. Keep one primary diagram per file unless the host report needs a small set.

## Themes and render flags

Bind `python scripts/results/render_diagram.py` (writes `.md` + `.mmd`; attempts PNG/SVG when `mmdc` is on PATH). Live flags:

| Flag | Role |
| --- | --- |
| `--input` / `-i` | `.mmd` or Markdown with a ` ```mermaid ` fence |
| `--topic` | Kebab-case topic for default out dir |
| `--out` | Output directory override |
| `--name` | Base filename |
| `--format` | `png` \| `svg` \| `both` |
| `--theme` | Mermaid/mmdc theme (e.g. `default`, `dark`, `forest`, `neutral`) |
| `--background` | Background color (e.g. `transparent`, `#fff`) |
| `--width` / `--height` | Render dimensions (px) |
| `--scale` | Scale factor |
| `--config-file` | Mermaid JSON config file |
| `--dry-run` | Validate and print planned paths |

```bash
python scripts/results/render_diagram.py --input diagram.mmd --topic example --theme dark --background transparent --format both
```

Equivalent raw `mmdc` (when debugging outside the wrapper):

```bash
mmdc -i input.mmd -o output.png -t dark -b transparent
```

Optional `%%{init: ...}%%` in the diagram source remains valid for advanced themeVariables; prefer script flags for common theme/background/size choices.

## Storage

- Default: `results/diagrams/<topic>/<YYYY-MM-DD>/` via `new_run_dir.py --family diagrams`.
- Attachment: store beside the host report (executive, threat-model, code-review, …).
- Threat models: assessment-agent owns the package; spawn `mermaid-diagram` / `architecture-diagram` for DFDs — do not reimplement under threat-model.

## Gotchas

- **Missing `mmdc`:** Markdown source still ships; images are skipped with a warning. Install `@mermaid-js/mermaid-cli` (or Docker `minlag/mermaid-cli`) when PNG/SVG is required.
- **Security:** untrusted diagram text can be risky in browser embeds; prefer offline `mmdc` renders for published artifacts. No secrets in labels.
- **GitHub:** fenced `mermaid` blocks render on GitHub; still keep rendered assets when the human wants portable images.
- **Syntax:** unbalanced brackets, HTML-like labels, and huge graphs fail or hang Chromium — keep diagrams focused.
- **accTitle / accDescr:** use for accessible titles when transforming Markdown via `mmdc`.
