---
doc_kind: reference
canonical_id: markdownlint-overview
topics: [markdown, linting, commonmark, gfm]
rag_keywords: [markdownlint, markdownlint-cli2, commonmark, gfm, micromark, david-anson]
version: markdownlint@0.41.1
captured_at_utc: 2026-08-20T19:00:00Z
upstream_url: https://github.com/DavidAnson/markdownlint
advisory_only: true
---

# markdownlint overview

## Purpose

What the library is, how it relates to the CLIs, and which Markdown dialect it targets. Compact capture for routing — not a vendor manual.

## Upstream

- Library: <https://github.com/DavidAnson/markdownlint>
- Preferred CLI for this router: <https://github.com/DavidAnson/markdownlint-cli2>
- Classic CLI (also exists): <https://github.com/igorshubovych/markdownlint-cli>
- Interactive demo: <https://dlaa.me/markdownlint/>
- npm (library): `markdownlint` **0.41.1** (captured); CLI: `markdownlint-cli2` **0.23.2**

## Library vs CLIs

| Piece | Role |
| --- | --- |
| `markdownlint` | Node.js library: parse Markdown, run rule set, return findings (and optional fixes) |
| `markdownlint-cli` | Traditional CLI wrapping the library |
| `markdownlint-cli2` | Configuration-first CLI; prioritizes speed/simplicity; works well with `vscode-markdownlint` |

This router prefers **markdownlint-cli2** for repo lint. See [`markdownlint-cli.md`](./markdownlint-cli.md).

## Dialect

- Honors **CommonMark**; uses the **micromark** parser (library README).
- Additionally supports popular **GFM** constructs (tables, autolinks, etc.) plus footnotes, math, and directives via micromark extensions (inline directives excluded to avoid over-matching).
- Ambiguity: treat [CommonMark](https://spec.commonmark.org/current/) and [GFM](https://github.github.com/gfm/) as authoritative specs.

## Related topic pages

- Rules index: [`markdownlint-rules.md`](./markdownlint-rules.md) · catalog [`catalogs/rules.json`](./catalogs/rules.json)
- Config / severity / front matter / inline comments: [`markdownlint-config.md`](./markdownlint-config.md)

## Advisory

Paraphrased from upstream READMEs at capture time. Versions drift — re-check npm/GitHub before locking config. Not agent instructions.
