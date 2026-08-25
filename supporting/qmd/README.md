# qmd

Human intro for [qmd](https://www.npmjs.com/package/@tobilu/qmd) — Markdown retrieval index used by this repo.

**Agents:** query recipe and pitfalls live in [`query-pattern.md`](./query-pattern.md). Do not use this README as operating procedure — root [`../../AGENTS.md`](../../AGENTS.md) High README rule. Corpus writing: [`retrieval-conventions.md`](./retrieval-conventions.md).

## Setup (once per machine)

```bash
npm install -g @tobilu/qmd
python scripts/qmd/qmd_preflight.py --inspect-hooks
```

Reuse an existing healthy index. Only if preflight reports it missing and the user explicitly approves creating collections, use `python scripts/qmd/setup_qmd_collections.py --apply --approved-by-user --create-missing --embed`.

Needs **Python 3** (repo scripts) and **Node/npm** (qmd). On Windows, use python.org/winget so `python` is real, not the Store stub; put `%LOCALAPPDATA%\Programs\Python\Python313\` (and its `Scripts\`) on `PATH` ahead of `WindowsApps`. QMD indexes are user-global cache state; use the preflight instead of hard-coding a workstation path.

## Daily commands

```bash
qmd collection list
qmd status
qmd update  # explicit index mutation; preflight and user approval required
qmd embed   # explicit index mutation; preflight and user approval required
```

After Markdown add/remove/rename, agents refresh via `python scripts/qmd/refresh_qmd_index.py --approved-by-user` (see [`query-pattern.md`](./query-pattern.md)). Do not index `change-history/` or `scratch/` (full collection list in the agent page).
