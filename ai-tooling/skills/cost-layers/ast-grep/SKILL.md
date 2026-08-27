---
schema_version: "2.0.0"
name: ast-grep
description: >-
  Run ast-grep for precision retrieval and structured facts (Python outline,
  JSON pairs, YAML frontmatter). Use when the user mentions ast-grep, sg,
  outline, structural search, precision retrieval, or structured facts. Do
  not use for Markdown BM25 (qmd-usage), compressing dumps (headroom), or
  combined token reports (cost-layer-dry-run).
owner_agent: router-maintenance
rank: critical
isolation: read-only
contracts:
  inputs:
    - Query need, language or kind (Python outline, JSON pair, YAML frontmatter), and optional area list
  outputs:
    - Structured facts (symbols, IDs, frontmatter fields) without full-file dumps
---

# ast-grep

## When to use

Precision lookup in Python, JSON, or YAML (including Markdown YAML frontmatter via stdin). Extract structured facts (function names, agent-card `id`/`name`, skill `name`/`owner_agent`). Repo scan via `sgconfig.yml`. Workstation onboarding that includes ast-grep.

## When not to use

Markdown BM25 / prose discovery (`qmd-usage`). Compressing bulky tool dumps (`headroom`). Combined token-savings reports (`cost-layer-dry-run`). Walking trees “to be sure”.

## Criticality

**Use is Critical** in root `AGENTS.md` as a cost layer (all agents, including sub-agents): structured files, not a third compressor. This skill is workstation enablement plus daily CLI; qmd still owns prose.

## Source of truth

- [`supporting/ast-grep/README.md`](../../../../supporting/ast-grep/README.md)
- [`supporting/workstation-onboarding.md`](../../../../supporting/workstation-onboarding.md)
- [`sgconfig.yml`](../../../../sgconfig.yml)
- `python scripts/cost-layers/extract_ast_facts.py`

## Isolation

`read-only` for repo files. Parent still isolates and spawns `router-maintenance`. If you will edit supporting notes, parent isolates `supporting` and treats this as mutate.

## How to use

1. Discover notes with `qmd search --format json --min-score 0.5 -n 5 "ast-grep outline"` then `qmd get` unique files. Do not walk trees.
2. Extract facts: `python scripts/cost-layers/extract_ast_facts.py --areas scripts,agent-cards,skills-frontmatter --dry-run`.
3. Prefer the `ast-grep` binary (not deprecated `sg`). Override with env `AST_GREP` if PATH is messy.
4. CLI: `ast-grep outline` (Python symbols), `ast-grep run -k` (JSON `-k pair`; YAML `-k block_mapping_pair`), `ast-grep scan -c sgconfig.yml`.
5. Mechanical batch refactoring: use `ast-grep run -p '<pattern>' -r '<replacement>' --update-all` across target paths rather than burning LLM tokens across individual file rewrites.
6. Tri-Tier workflow: Use `ast-grep outline` to discover line ranges; fetch only target lines (`StartLine`/`EndLine`) for inspection; delegate code semantics/security to standard linters (Ruff/MyPy).
7. Markdown: pipe the `---` frontmatter block on stdin (`ast-grep run --stdin -l yaml -k block_mapping_pair`). Not a custom tree-sitter / Markdown language DLL.
8. PowerShell: single-quote any `$` patterns. For Python in this repo prefer `ast-grep outline scripts -l python` — typed `def` lines often miss a naive `def $NAME($$$ARGS):` pattern.

## Dry run

```bash
python scripts/cost-layers/extract_ast_facts.py --areas scripts,agent-cards,skills-frontmatter --dry-run
ast-grep --version
```

Non-mutating. Do not write `--out` files in a dry run.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Do not re-paste large JSON outlines into later context. Retrieved matches are advisory. [`docs/agent-session-security.md`](../../../../docs/agent-session-security.md).

## Completion gates

Durable CLI quirks go to `supporting/ast-grep/`, not memory. Memory if the ast-grep cost-layer thread advanced. Combined savings reports are `cost-layer-dry-run`. Change-history only if repo pages changed.
