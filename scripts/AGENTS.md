# Scripts AGENTS

Python-first automation. Prefer tagged scripts here over ad-hoc shell; bind repeatable work from skills.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Spawn `script-ops` when a catalogued scripts skill is material. Change-history via script is a parent session-end gate.

## Layout

Purpose subfolders. Keep this file, human [`README.md`](./README.md), and generated [`script-index.md`](./script-index.md) at `scripts/` root.

| Path | Role |
| --- | --- |
| `_lib/` | Shared helpers — not indexed |
| `change-history/` | Provenance append / quarter scaffold |
| `routing/` | Script index, routing index, skill dispatch, worktree spawn |
| `qmd/` / `cost-layers/` | Retrieval + combined validation |
| `ai-tooling/` / `docs/` / `projects/` | Catalog / wiki / scaffold helpers |

`REPO_ROOT` from `paths.resolve_repo_root()`. Import helpers from `_lib`.

## Tagging

Every indexed script starts with a docstring tag block (`tags:`, optional `routing_hints:`). Regenerate: `python scripts/routing/generate_script_index.py`.

## Rules

- New automation = Python 3 under `scripts/<purpose>/`.
- OS-shell-only only when no Python equivalent (`git` / `gh` / `qmd` / vendor installers).
- Idempotent when practical; clear usage on bad args; no secrets.
- Change-history mutations only via `change-history/` scripts.
- Do not index `_lib/` or files whose names start with `_`.
