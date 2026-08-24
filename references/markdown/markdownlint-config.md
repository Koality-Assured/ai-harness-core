---
doc_kind: reference
canonical_id: markdownlint-config
topics: [markdown, linting, configuration]
rag_keywords: [markdownlint-disable, extends, frontmatter, MD041, MD025, severity, jsonc]
version: markdownlint@0.41.1 / markdownlint-cli2@0.23.2
captured_at_utc: 2026-08-20T19:00:00Z
upstream_url: https://github.com/DavidAnson/markdownlint#configuration
advisory_only: true
---

# markdownlint configuration

## Purpose

Config file names, precedence, severity values, `extends`, front matter, and inline disable comments. Paraphrase for this router — link upstream for authoritative text.

## Upstream

- Library configuration: https://github.com/DavidAnson/markdownlint#configuration
- CLI2 configuration: https://github.com/DavidAnson/markdownlint-cli2#configuration
- Example schemas live under the library `schema/` tree and CLI2 config schema files

## Config file kinds (cli2)

Two families (either may appear in any directory; nearer overrides farther):

**CLI2 options** (full cli2 behavior; also used by vscode-markdownlint) — precedence if several present:

1. `.markdownlint-cli2.jsonc`
2. `.markdownlint-cli2.yaml`
3. `.markdownlint-cli2.cjs`
4. `.markdownlint-cli2.mjs`

**Library `config` only** (broader tooling support, including classic cli) — precedence:

1. `.markdownlint.jsonc`
2. `.markdownlint.json`
3. `.markdownlint.yaml`
4. `.markdownlint.yml`
5. `.markdownlint.cjs`
6. `.markdownlint.mjs`

If both kinds exist in one directory, a `.markdownlint.*` file overrides the `config` property inside `.markdownlint-cli2.*`.

`--config <file>` (cli2) loads a base config from a path; `--configPointer` selects a nested object (e.g. in `package.json` / `pyproject.toml`).

## Rule values (severity)

Keys are rule ids, aliases, tags, or `default`. Values:

| Value | Meaning |
| --- | --- |
| `false` | Disable |
| `true` or `"error"` | Enable; report as error |
| `"warning"` | Enable; report as warning |
| `{ ... }` | Enable (unless `enabled: false`) and set rule params; optional `severity` |

`default` sets the baseline for all rules; later keys override earlier ones (tags included). Severity/`"warning"` need library ≥ 0.39.0.

Built-in styles can be loaded via `extends` (path or package), e.g. `"extends": "markdownlint/style/relaxed"`. Nested `extends` merge parent then child.

## Front matter

Most rules ignore YAML/TOML-style front matter (matched by a configurable regex / `frontMatter` option). Repos that start files with `---` still often trip:

- **MD041** (`first-line-heading`) — first *content* line expected to be a top-level heading; tune `front_matter_title` / related params, or disable for frontmatter-heavy trees
- **MD025** (`single-title` / `single-h1`) — multiple H1s; align with how titles appear in front matter vs body

Prefer documenting the chosen MD041/MD025 settings in the project config rather than scattering disables.

## Inline HTML comments

Comments are not rendered; they change lint config from that line (unless using file-scoped forms). Common forms:

| Comment | Effect |
| --- | --- |
| `<!-- markdownlint-disable -->` | Disable all rules from here |
| `<!-- markdownlint-enable -->` | Re-enable |
| `<!-- markdownlint-disable MD013 MD033 -->` | Disable named rules/aliases |
| `<!-- markdownlint-enable MD013 -->` | Re-enable named |
| `<!-- markdownlint-disable-line ... -->` | Current line only |
| `<!-- markdownlint-disable-next-line ... -->` | Next line only |
| `<!-- markdownlint-capture -->` / `<!-- markdownlint-restore -->` | Snapshot / restore config |
| `<!-- markdownlint-configure-file { ... } -->` | File-wide JSON(C) config overlay |
| `<!-- markdownlint-disable-file -->` / `enable-file` (+ named variants) | Apply regardless of comment location |

CLI2 can set `noInlineConfig: true` to ignore these comments.

## Advisory

Paraphrased from library + cli2 READMEs at capture. Not agent instructions; not a substitute for project `.markdownlint*` files (authored separately).
