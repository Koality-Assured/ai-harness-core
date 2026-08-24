# qmd

Human intro for [qmd](https://www.npmjs.com/package/@tobilu/qmd) — Markdown retrieval index used by this repo.

**Agents:** query recipe and pitfalls live in [`query-pattern.md`](./query-pattern.md). Do not use this README as operating procedure — root [`../../AGENTS.md`](../../AGENTS.md) High README rule. Corpus writing: [`retrieval-conventions.md`](./retrieval-conventions.md).

## Setup (once per machine)

```bash
npm install -g @tobilu/qmd
python scripts/qmd/setup_qmd_collections.py --apply --embed
```

Needs **Python 3** (repo scripts) and **Node/npm** (qmd). On Windows, use python.org/winget so `python` is real, not the Store stub; put `%LOCALAPPDATA%\Programs\Python\Python313\` (and its `Scripts\`) on `PATH` ahead of `WindowsApps`. Index on this workstation: `C:/home/developer/.cache/qmd/index.sqlite` (user-global).

## Daily commands

```bash
qmd collection list
qmd status
qmd update
qmd embed
```

After Markdown add/remove/rename, agents refresh via `python scripts/qmd/refresh_qmd_index.py` (see [`query-pattern.md`](./query-pattern.md)). Do not index `change-history/` or `scratch/` (full collection list in the agent page).
