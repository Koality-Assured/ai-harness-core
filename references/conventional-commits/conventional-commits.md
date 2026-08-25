---
doc_kind: reference
canonical_id: conventional-commits
topics: [git, commits, pull-requests]
rag_keywords: [conventional-commits, feat, fix, docs, refactor, chore, breaking-change, pr]
advisory_only: true
---

# Conventional Commits (operational guide)

Upstream: [conventionalcommits.org](https://www.conventionalcommits.org/)

## Purpose

Consistent commit messages and PR titles so history, changelogs, and review comments stay scannable and machine-parseable.

## Format

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Common types

| Type | When |
| --- | --- |
| `feat` | New user-facing capability or functionality |
| `fix` | Bug fix or error correction |
| `docs` | Documentation only changes |
| `style` | Formatting, whitespace; no code logic change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system, tool configs, dependencies |
| `ci` | Continuous integration configuration / workflows |
| `chore` | Maintenance that doesn't fit elsewhere (e.g. routine dependency bump) |
| `revert` | Reverting a previous commit |

### Breaking changes

- `feat!:` / `fix!:` in the subject line, **or**
- Footer: `BREAKING CHANGE: <description>`

## PR comments and titles

- PR title MUST follow commit subject style: `feat(routing): add area-map second hop` or `fix(qmd): correct readme ignore in test oracle`
- Review comments: prefer actionable path + expected type (`nit: docs`, `blocking: fix`, `question:`).
- Squash merges: ensure the squash subject still follows Conventional Commits.

## Agent habits

- Match the repo's existing type vocabulary before inventing new types.
- Keep subjects ≤ ~72 chars; imperative mood ("add", not "added").
- Never put secrets, passwords, tokens, or PII in commit subjects or bodies.
