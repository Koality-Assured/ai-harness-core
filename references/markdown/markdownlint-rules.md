---
doc_kind: reference
canonical_id: markdownlint-rules
topics: [markdown, linting, rules]
rag_keywords: [MD001, MD013, MD025, MD033, MD041, markdownlint-rules, heading-increment]
version: markdownlint@0.41.1
captured_at_utc: 2026-08-20T19:00:00Z
upstream_url: https://github.com/DavidAnson/markdownlint/blob/main/README.md
advisory_only: true
---

# markdownlint rules (compact)

## Purpose

One-line intent for each built-in `MD###` rule and its alias. Not examples, rationale, or fix recipes — those live upstream.

## Upstream

- Rules / Aliases index: <https://github.com/DavidAnson/markdownlint/blob/main/README.md>
- Detailed rule docs (do not vendor wholesale): <https://github.com/DavidAnson/markdownlint/blob/HEAD/doc/Rules.md>
- Per-rule pages under `doc/mdNNN.md` in the library repo

Machine catalog: [`catalogs/rules.json`](./catalogs/rules.json) (`id`, `alias`, `summary` only).

## Compact table

| ID | Alias | Intent |
| --- | --- | --- |
| MD001 | `heading-increment` | Heading levels should only increment by one level at a time |
| MD003 | `heading-style` | Heading style |
| MD004 | `ul-style` | Unordered list style |
| MD005 | `list-indent` | Inconsistent indentation for list items at the same level |
| MD007 | `ul-indent` | Unordered list indentation |
| MD009 | `no-trailing-spaces` | Trailing spaces |
| MD010 | `no-hard-tabs` | Hard tabs |
| MD011 | `no-reversed-links` | Reversed link syntax |
| MD012 | `no-multiple-blanks` | Multiple consecutive blank lines |
| MD013 | `line-length` | Line length |
| MD014 | `commands-show-output` | Dollar signs used before commands without showing output |
| MD018 | `no-missing-space-atx` | No space after hash on atx style heading |
| MD019 | `no-multiple-space-atx` | Multiple spaces after hash on atx style heading |
| MD020 | `no-missing-space-closed-atx` | No space inside hashes on closed atx style heading |
| MD021 | `no-multiple-space-closed-atx` | Multiple spaces inside hashes on closed atx style heading |
| MD022 | `blanks-around-headings` | Headings should be surrounded by blank lines |
| MD023 | `heading-start-left` | Headings must start at the beginning of the line |
| MD024 | `no-duplicate-heading` | Multiple headings with the same content |
| MD025 | `single-title/single-h1` | Multiple top-level headings in the same document |
| MD026 | `no-trailing-punctuation` | Trailing punctuation in heading |
| MD027 | `no-multiple-space-blockquote` | Multiple spaces after blockquote symbol |
| MD028 | `no-blanks-blockquote` | Blank line inside blockquote |
| MD029 | `ol-prefix` | Ordered list item prefix |
| MD030 | `list-marker-space` | Spaces after list markers |
| MD031 | `blanks-around-fences` | Fenced code blocks should be surrounded by blank lines |
| MD032 | `blanks-around-lists` | Lists should be surrounded by blank lines |
| MD033 | `no-inline-html` | Inline HTML |
| MD034 | `no-bare-urls` | Bare URL used |
| MD035 | `hr-style` | Horizontal rule style |
| MD036 | `no-emphasis-as-heading` | Emphasis used instead of a heading |
| MD037 | `no-space-in-emphasis` | Spaces inside emphasis markers |
| MD038 | `no-space-in-code` | Spaces inside code span elements |
| MD039 | `no-space-in-links` | Spaces inside link text |
| MD040 | `fenced-code-language` | Fenced code blocks should have a language specified |
| MD041 | `first-line-heading/first-line-h1` | First line in a file should be a top-level heading |
| MD042 | `no-empty-links` | No empty links |
| MD043 | `required-headings` | Required heading structure |
| MD044 | `proper-names` | Proper names should have the correct capitalization |
| MD045 | `no-alt-text` | Images should have alternate text (alt text) |
| MD046 | `code-block-style` | Code block style |
| MD047 | `single-trailing-newline` | Files should end with a single newline character |
| MD048 | `code-fence-style` | Code fence style |
| MD049 | `emphasis-style` | Emphasis style |
| MD050 | `strong-style` | Strong style |
| MD051 | `link-fragments` | Link fragments should be valid |
| MD052 | `reference-links-images` | Reference links and images should use a label that is defined |
| MD053 | `link-image-reference-definitions` | Link and image reference definitions should be needed |
| MD054 | `link-image-style` | Link and image style |
| MD055 | `table-pipe-style` | Table pipe style |
| MD056 | `table-column-count` | Table column count |
| MD058 | `blanks-around-tables` | Tables should be surrounded by blank lines |
| MD059 | `descriptive-link-text` | Link text should be descriptive |
| MD060 | `table-column-style` | Table column style |

Gaps in the numeric sequence (e.g. no MD002 / MD006 / MD057) are intentional — those IDs are unused or retired upstream.

## Tags (high level)

Upstream groups rules under tags such as `headings`, `whitespace`, `links`, `table`, `accessibility`. Enabling/disabling a tag applies to all rules that carry it. See library README Tags section.

## Advisory

Paraphrased from the Rules / Aliases list at capture (`markdownlint` **0.41.1**). Full parameters and examples: upstream `doc/Rules.md`. Advisory only.
