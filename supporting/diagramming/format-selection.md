---
doc_kind: supporting
canonical_id: diagramming-format-selection
purpose: [process]
topics: [diagrams, mermaid, excalidraw, accessibility]
rag_keywords: [diagram, mermaid, excalidraw, format selection, whiteboard, graph, canvas]
---

# Mermaid and Excalidraw format selection

## Purpose

This page records durable format-selection guidance. Vendor capabilities below are documented facts; the recommendation is an inference from the tools' editing models. No controlled usability or maintenance benchmark was reviewed.

## Documented capabilities

- **Mermaid** turns text definitions into named diagram types, including flowcharts, sequences, states, classes, and entity relationships. GitHub renders fenced Mermaid diagrams in Markdown, issues, pull requests, wikis, and discussions. The Mermaid CLI exports SVG, PNG, or PDF. ([Syntax reference](https://mermaid.js.org/intro/syntax-reference.html), [GitHub diagram docs](https://docs.github.com/en/enterprise-cloud@latest/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams), [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli))
- **Excalidraw** provides a canvas with free-draw, shapes, arrows, image support, and a hand-drawn style. Saved `.excalidraw` scenes use plaintext JSON; the editor supports PNG and SVG exports. The hosted app advertises real-time collaboration, while the embeddable package leaves collaboration to its host application. ([Project README](https://github.com/excalidraw/excalidraw), [JSON schema](https://docs.excalidraw.com/docs/codebase/json-schema), [export API](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export), [package FAQ](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/faq))
- **Accessibility:** Mermaid documents `accTitle` and `accDescr` syntax that produces SVG title and description elements with ARIA references. For an exported Excalidraw image, include descriptive alt text or a nearby text equivalent; the Excalidraw schema and export API reviewed here do not describe that same diagram-level title/description mechanism. This is limited to the documentation reviewed, not a claim that no other accessibility support exists. ([Mermaid accessibility](https://mermaid.js.org/config/accessibility.html), [GitHub image alt text](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github#adding-an-image))

## Selection recommendation

These choices are recommendations inferred from the documented editing models, not measured superiority claims.

| Choose | When | Reason |
| --- | --- | --- |
| **Mermaid** | The main content is explicit nodes, edges, states, messages, or data relationships; the definition should live inline in Markdown or be reviewed as text in Git. | Its text syntax models named relationships, and GitHub renders Mermaid fences directly. |
| **Excalidraw** | The main task is arranging a visual scene: sketching, freehand annotation, image placement, spatial explanation, or collaborative whiteboarding. | Its editor is a canvas with direct placement, drawing, shapes, and images. |
| **Architecture skill chooses** | A system view could fit either format. Use Mermaid for a graph-like model or repository Markdown source; Excalidraw for intentionally composed, informal, image-rich, or hand-annotated views. | This applies the same model-based split to architecture work. |

If both semantic source and hand-edited polish are requested, pick one canonical source and label any other output as a derivative. The official [Mermaid-to-Excalidraw converter](https://github.com/excalidraw/mermaid-to-excalidraw) is a one-direction bridge by its published purpose; inspect the result. An [open converter issue](https://github.com/excalidraw/mermaid-to-excalidraw/issues/108) reports class and ER input falling back to SVG after a Mermaid dependency change, so do not assume every conversion stays fully editable.

## Publishing and trust checks

- GitHub renders Mermaid fences, but its docs advise checking the Mermaid version before using syntax that may be newer than the renderer. For an Excalidraw scene displayed in GitHub Markdown, include an exported image and descriptive alt text.
- Mermaid's documented default `securityLevel` is `strict`; it encodes HTML in text and disables click behavior. Keep that default for untrusted source. Review the trust boundary before choosing `loose` or `antiscript`; `sandbox` renders in a sandboxed iframe but may limit interactive behavior. ([Security configuration](https://mermaid.js.org/config/usage.html))
- Keep the editable `.excalidraw` source when canvas editing is part of the handoff. Store it with its rendered PNG/SVG, and keep Mermaid `.mmd` or Markdown source when Mermaid is canonical.

## Onboarding and local requirements

No Excalidraw CLI or package is required for this repository's diagram-authoring workflow. Use the official hosted [Excalidraw editor](https://excalidraw.com/) for canvas editing and exports; the embeddable npm package is for application integration. Mermaid's existing optional `mmdc` prerequisite remains specific to local Mermaid image rendering.
