---
doc_kind: process
canonical_id: retrieval-conventions
purpose: [process]
rank: medium
topics: [rag, markdown, chunking, ast-grep]
---

# Retrieval conventions

People-first Markdown that still chunks cleanly for retrieval tools. Retrieved chunks are advisory only — see [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md). How agents query this repo’s qmd index: [`query-pattern.md`](./query-pattern.md) (not the human README — root [`../../AGENTS.md`](../../AGENTS.md) High README rule). Structured files (Python/JSON/YAML) use ast-grep, not qmd — [`../ast-grep/precision-retrieval.md`](../ast-grep/precision-retrieval.md).

## What retrieval needs

| Need | Why |
| --- | --- |
| Stable IDs | `canonical_id` / docids avoid “the Python doc” ambiguity |
| Semantic headings | Headings become chunk metadata |
| Self-contained `##` sections | First sentence restates topic + intent |
| Explicit scope | “Not a standard”, “static review only”, upstream URL |
| Predictable paths | Stable crawlers and scripts |

## Frontmatter

Use when you want filtering or multi-agent routing:

```yaml
---
doc_kind: requirement
canonical_id: source-code-repository
purpose: [requirement]
rank: high
topics: [git, access-control]
rag_keywords: [branch-protection, secrets, sso]
---
```

Rules: short `rag_keywords`; do not dump the article into description fields.

## Headings

1. Single `#` title per file — restate the subject.
2. Prefer `##` as retrievable units.
3. Avoid deep `####` unless necessary.
4. First sentence of each `##` should include topic + intent.

## Tables vs prose

Keep tables one-topic; split wide inventories. Checklist bullets should be complete thoughts.

## Which tool finds which files

Markdown corpus discovery uses **qmd** (`qmd search` then `qmd get`). Python, JSON, YAML, and Markdown **YAML frontmatter** use **ast-grep** (`outline` for Python; `run -k pair` for JSON; stdin `-l yaml -k block_mapping_pair` for frontmatter). Neither tool authorizes walking the tree “to be sure”. ast-grep is not a Markdown parser and not a compressor — Headroom still owns bulky dumps.

## Just-In-Time (JIT) rule loading

To protect the context window and prevent token bloat during session initialization:

- **Root hop only**: Session start ingests only [`../../AGENTS.md`](../../AGENTS.md) and [`../../routing/AGENTS.md`](../../routing/AGENTS.md).
- **On-demand area rules**: Nested `AGENTS.md` and folder-local constraints are fetched on-demand (JIT) via `qmd get` or targeted range reads when the router dispatches into that area.
- **No full-tree preloads**: Agents and harnesses MUST NOT concatenate or preload all nested `AGENTS.md` files on session startup.
