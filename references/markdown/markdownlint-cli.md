---
doc_kind: reference
canonical_id: markdownlint-cli
topics: [markdown, linting, cli]
rag_keywords: [markdownlint-cli2, npx, --fix, globs, docker, davidanson]
version: markdownlint-cli2@0.23.2
captured_at_utc: 2026-08-20T19:00:00Z
upstream_url: https://github.com/DavidAnson/markdownlint-cli2
advisory_only: true
---

# markdownlint CLI (prefer cli2)

## Purpose

How this router should invoke Markdown linting. Prefer **markdownlint-cli2** over classic `markdownlint-cli`.

## Upstream

- <https://github.com/DavidAnson/markdownlint-cli2>
- npm: `markdownlint-cli2` **0.23.2** (captured; bundles a matching `markdownlint` version)
- Docker Hub: `davidanson/markdownlint-cli2`
- Classic CLI (not preferred here): <https://github.com/igorshubovych/markdownlint-cli>

## Why cli2 here

Configuration-based, fast, feature-parity with classic cli (sometimes with different flags), and aligned with `vscode-markdownlint`. Library overview: [`markdownlint-overview.md`](./markdownlint-overview.md). Config files: [`markdownlint-config.md`](./markdownlint-config.md).

## Typical invocation

```bash
npx markdownlint-cli2 "**/*.md" "#node_modules"
```

Auto-fix where rules emit fixes:

```bash
npx markdownlint-cli2 --fix "**/*.md" "#node_modules"
```

Notes (paraphrased from cli2 help):

- Quote globs for cross-platform shells; prefer `#` over `!` for negation when shells eat `!`
- Path separator is `/` on all platforms
- A lone `.` is remapped to `*.{md,markdown}` in the current directory (not a full tree walk); use `**` when a tree-wide lint is intended
- `--config` / `--configPointer` for non-root or nested config objects
- Exit `0` = no errors (warnings ok); `1` = errors; `2` = tool failure

## Docker (optional)

```bash
docker run -v "$PWD:/workdir" davidanson/markdownlint-cli2:v0.23.2 "**/*.md" "#node_modules"
```

Image runs as non-root `node` by default; bind-mount the project at `/workdir` (or set `-w`).

## Install options (upstream)

Global npm, local `--save-dev`, Homebrew `markdownlint-cli2`, GitHub Action `DavidAnson/markdownlint-cli2-action`, or the Docker image above.

## Advisory

Paraphrased from cli2 README at capture. Pin image/npm versions in CI deliberately. Not agent instructions; this page does not add repo config files.
