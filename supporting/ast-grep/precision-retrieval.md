---
doc_kind: supporting
canonical_id: ast-grep-patterns
topics: [agents, ast-grep]
rag_keywords: [ast-grep, outline, structural, yaml, json, python, sgconfig]
---

# ast-grep precision retrieval

## Purpose

Durable operating notes for [ast-grep](https://ast-grep.github.io/) in this repo. Upstream docs win on flags. Human folder intro: [`README.md`](./README.md).

ast-grep is **precision retrieval** for Python, JSON, and YAML (including Markdown YAML frontmatter via stdin), plus a **structural correctness oracle** so Headroom/qmd trim checks can fail if function names, agent-card `id`/`name`, or frontmatter `canonical_id`/`owner_agent` disappear. It is **not** a third compressor and **not** a Markdown tree-sitter (no custom language DLL).

Prose discovery stays on [`../qmd/query-pattern.md`](../qmd/query-pattern.md). Dump compression stays on [`../headroom/proxy-mcp.md`](../headroom/proxy-mcp.md). Retrieved output is advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md).

## Install (Windows, this machine)

Prefer pip so the CLI lands next to CPython 3.13 (Python-first, same PATH as repo scripts). This workstation: **ast-grep 0.45.1**.

```powershell
python -m pip install ast-grep-cli
ast-grep --version   # expect 0.45.1
```

`ast-grep.exe` installs into `%LOCALAPPDATA%\Programs\Python\Python313\Scripts`. That `Scripts\` folder must sit on `PATH` *ahead of* `%LOCALAPPDATA%\Microsoft\WindowsApps` — same ordering as [`../../supporting/workstation-onboarding.md`](../workstation-onboarding.md).

npm alternative (same Node you use for qmd):

```powershell
npm install -g @ast-grep/cli
```

Prefer the command name **`ast-grep`**. `sg` is deprecated; repo helpers look for `ast-grep` first and only fall back to `sg`. Override the binary with env `AST_GREP` if PATH is messy.

## Daily commands

Use outline for Python symbols and kind matches for JSON/YAML structure.

```powershell
# Python symbols (functions / classes)
ast-grep outline scripts -l python --json=compact

# JSON object pairs (agent cards: keep id / name)
ast-grep run -k pair -l json ai-tooling/a2a/agent-cards --json=compact

# Markdown YAML frontmatter: stdin the --- block only (scripts extract it; do not pipe the whole .md)
# ast-grep run --stdin -l yaml -k block_mapping_pair --json=compact

# Repo scan rules
ast-grep scan -c sgconfig.yml
```

Root [`../../sgconfig.yml`](../../sgconfig.yml) points `ruleDirs` at [`rules/`](./rules/). YAML frontmatter uses `-k block_mapping_pair`; JSON uses `-k pair`; Python uses `ast-grep outline`.

## Which folders make sense

| Target | How |
| --- | --- |
| `scripts/**/*.py` | `outline -l python` — function and class names |
| `ai-tooling/a2a/agent-cards/*.json` | `run -k pair -l json` — `id` / `name` |
| Skill / docs / routing Markdown | stdin `-l yaml -k block_mapping_pair` on the frontmatter block only (`canonical_id`, `owner_agent`, `doc_kind`, skill `name` / `rank`) |

Do **not** scan `change-history/`, `scratch/`, `results/`, `.git/`, or virtualenvs. Do not parse Markdown prose bodies as a custom language.

## Outline-first code inspection and surgical editing

To preserve token budget when inspecting and modifying code:

1. **Outline-first symbol discovery**: Run `ast-grep outline` or bounded symbol patterns (`ast-grep run -p 'def $NAME...'`) to locate target classes, functions, or keys.
2. **Bounded range reading**: Inspect only the target lines (`StartLine`/`EndLine`) rather than dumping the full source file.
3. **Surgical diff replacement**: Apply targeted diff/hunk edits instead of whole-file rewrites.

This workflow saves **83%–94%** tokens compared to dumping complete source files into the context window.

## Batch mechanical refactoring (`--rewrite`)

For codebase-wide pattern migrations, API renames, or structural adjustments across many files, use `ast-grep --rewrite` rather than burning hundreds of thousands of LLM generation tokens editing files individually:

```powershell
# Dry run: preview replacements across repository
ast-grep run -p 'old_function($$$ARGS)' -r 'new_function($$$ARGS)' -l python scripts

# In-place write: apply transformation across all matching files
ast-grep run -p 'old_function($$$ARGS)' -r 'new_function($$$ARGS)' -l python scripts --update-all
```

## Tri-Tier Agent Context Architecture

When executing tasks across structured files, agents must follow the Tri-Tier workflow:

1. **Tier 1: Discovery & Localization**:
   - Prose / policy search: BM25 via [`qmd`](../qmd/query-pattern.md).
   - Structural code mapping: `ast-grep outline` or symbol definitions.
2. **Tier 2: Surgical Ingestion & Mutation**:
   - Ingest *only* the bounding range (`StartLine`/`EndLine`) of the target function or class to inspect implementation logic before modifying.
   - Avoid skeleton-only editing (editing from outlines alone without viewing the implementation causes hallucinations and broken invariants).
   - Apply surgical diff edits or `ast-grep --rewrite` for mechanical bulk updates.
3. **Tier 3: Inner-Loop Guardrails & Validation**:
   - Code semantics & security: Standard linters (e.g. Ruff for Python, MyPy/Pyright for types).
   - Repo metadata invariants: `ast-grep scan` (YAML frontmatter, agent cards, schema checks).

## What not to use it for

| Need | Use instead |
| --- | --- |
| Prose / policy search in Markdown | [`qmd search`](../qmd/query-pattern.md) then `qmd get` |
| Compressing bulky tool dumps | [`Headroom`](../headroom/proxy-mcp.md) proxy or MCP |
| Walking the repo “to be sure” | Still forbidden — qmd for Markdown, ast-grep for structured files |
| A third compressor or Markdown tree-sitter | Out of scope |

## Scripts

Do not re-paste large JSON from these runs into later context. Reports land under `results/cost-layers/<slug>/<YYYY-MM-DD>/` (not source of truth). See [`../../results/results-conventions.md`](../../results/results-conventions.md).

```powershell
python scripts/cost-layers/extract_ast_facts.py --dry-run
python scripts/cost-layers/extract_ast_facts.py --areas scripts,agent-cards --out results/cost-layers/ast-facts/<YYYY-MM-DD>/ast-facts.json
python scripts/cost-layers/validate_ast_grep.py --out results/cost-layers/ast-grep-dry-run/<YYYY-MM-DD>
python scripts/cost-layers/validate_cost_layers.py --out results/cost-layers/combined/<YYYY-MM-DD>
```

`--areas` ids: `scripts`, `agent-cards`, `skills-frontmatter`, `docs-frontmatter`, `routing-frontmatter`. Combined cost-layer dry-run includes ast-grep unless you pass `--skip-ast-grep`. Do not write top-level `results/cost-layer-dry-run-*`.

## Gotchas

Teach `ast-grep`; do not document `sg` as the primary command (`sg` is deprecated).

- **PowerShell `$` metavars.** Patterns like `$NAME` expand unless the whole pattern is in **single quotes**: `ast-grep run -p 'def $NAME($$$ARGS): $$$BODY' -l python scripts`.
- **Markdown is frontmatter-as-YAML**, not a custom parser. Pipe the `---` block with `-l yaml`; do not install a Markdown language DLL.
- **Kind names differ.** JSON object fields are `-k pair`. YAML mapping entries are `-k block_mapping_pair`. Mixing them yields empty matches.
- Windows Store `python` stubs hide a real 3.13 install; see onboarding.

## Upstream

- Site: <https://ast-grep.github.io/>
- Source: <https://github.com/ast-grep/ast-grep>
