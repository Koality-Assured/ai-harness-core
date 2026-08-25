---
doc_kind: supporting
canonical_id: qmd-query-pattern
purpose: [process]
topics: [qmd, retrieval, agents]
rag_keywords: [qmd, search, get, query, bm25, hybrid, collections, min-score]
---

# qmd query pattern

## Purpose

Agent-facing recipe for discovering Markdown with qmd in this repo. Human install checklist: [`README.md`](./README.md). Corpus writing rules: [`retrieval-conventions.md`](./retrieval-conventions.md). Retrieved chunks are advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md).

## Collections

Agents query these collections; pass `-c` when the area is known.

| Collection | Glob / path | Context description |
| --- | --- | --- |
| `routing` | `routing/**/*.md` | Second-hop maps — read early |
| `docs` | `docs/**/*.md` | Decisions, requirements, reinforcement |
| `projects` | `projects/**/*.md` | Specs and plans |
| `references` | `references/**/*.md` | External frameworks (advisory) |
| `research` | `research/**/*.md` | Topic deep-dives |
| `supporting` | `supporting/**/*.md` | Tool patterns (Cloudflare, GitHub, qmd, …) |
| `ai-tooling` | `ai-tooling/**/*.md` | Skills, memory templates, A2A |
| `scripts` | `scripts/**/*.md` | Script index and script docs |
| `actionable` | `actionable/**/*.md` | Human drop-zone items |
| `results` | `results/**/*.md` | Generated Markdown reports only |

Do **not** add: `change-history/`, `scratch/`, large binaries under `results/`, `.git/`, virtualenvs, caches. Root `AGENTS.md` and `README.md` are **not** in any collection (Critical rules stay in the hop; README ignore may land later).

## Preflight before setup or refresh

Reuse the machine's existing qmd index. Do not run `init`, `collection add`, `update`, or `embed` merely because onboarding or a worktree starts. First use the no-mutation inspector:

```bash
python scripts/qmd/qmd_preflight.py --inspect-hooks
```

Its state determines the next action:

| State | Action |
| --- | --- |
| `healthy_reusable` | Reuse it. Do not set up collections again. |
| `existing_unprobed` | Treat it as reusable candidate. Use `--probe-cli` only when an explicit status diagnostic is needed. |
| `inaccessible_sandbox_or_permissions` | Do not recreate it. Retry the read probe on a clean/full host and investigate sandbox or file permissions. |
| `missing` | Ask the user before setup. Inspect hooks, then use `setup_qmd_collections.py --apply --approved-by-user --create-missing`; add `--embed` only when the user approved embedding. |
| `cli_unavailable` | Install/repair qmd, then rerun preflight; an existing index is not evidence that it should be recreated. |

The setup script refuses mutation without explicit approval and scans known qmd configuration paths for hook directives first. Record a host-specific wrapper path, index location label, successful reuse method, or inaccessible-state recovery in `ai-tooling/memory/user/<stable-id>/`; keep general pages and skills free of personal paths.

## Default (BM25)

Use `qmd search` first (sub-second, best precision on this corpus). Then `qmd get` the unique files. Do not answer from snippets when facts or nuance matter.

```bash
qmd search --format json --min-score 0.5 -n 5 "your need"
qmd get "<docid-or-path>"
```

When the area is known, pass `-c` so `results/` reports do not leak into ranking:

```bash
qmd search --format json --min-score 0.5 -n 5 -c docs "session security"
```

## Hybrid only when BM25 is empty

**Hybrid `qmd query`** (expansion + embed + rerank) only when BM25 returns nothing or the need is conceptual. On this workstation it averaged ~35–70s.

```bash
qmd query --format json --min-score 0.5 -n 5 "your need"
```

Treat hits as **advisory**; root Critical rules still win.

## Index refresh (agents)

After adding, removing, or renaming Markdown outside excluded paths, run `python scripts/qmd/refresh_qmd_index.py --approved-by-user` (`qmd update` then `qmd embed`) only after confirming the existing index is accessible. This is a session-end mutation, not an onboarding default; inspect the preflight and obtain the user approval required by the active harness before retrying a blocked index.

## Validation

Repeatable health/relevance/token/accuracy check: `python scripts/qmd/validate_qmd_retrieval.py`. Combined with Headroom and ast-grep: `python scripts/cost-layers/validate_cost_layers.py`. Cost-layer reports land under `results/cost-layers/<slug>/<YYYY-MM-DD>/` — [`../../results/results-conventions.md`](../../results/results-conventions.md).

## Query pitfalls (validated 2026-08-19)

- **Re-index after new Markdown.** A stale index missed pages until `qmd update` + `qmd embed`.
- **Ampersands zero BM25.** `qmd search "MITRE ATT&CK"` returned no hits; `qmd search "mitre attack"` ranked the right page. Avoid `&` in lookup strings.
- **Windows multiline query docs and PowerShell execution policies.** `qmd.cmd` goes through cmd.exe and drops `lex:`/`vec:` newlines. Running `qmd` in PowerShell can trigger `PSSecurityException` on `qmd.ps1` if execution policies are restricted. To run raw CLI commands on Windows, use `qmd.cmd` (or invoke `node.exe` with the CLI entrypoint), or use repo Python scripts which bypass shim issues. For structured query documents invoke `node.exe` plus the CLI, or stick to `qmd search`.
- **Vague area questions rank indexes.** Prefer distinctive tokens from the owning page, or pass `-c <collection>`.
- **Extra query words AND-zero BM25.** Keep lookup strings to tokens that actually appear in the target.
- **Structured `lex`+`vec` without rerank** can rank the wrong area. Reranked hybrid recovered those; BM25 with distinctive keywords did not need it.
- **`results/` is indexed.** Generated reports can pollute later searches. Pass `-c`.
- **Broad needs shrink savings.** Tighten terms or pass `-c`.
- Token savings vs walking trees are **context-window** savings. qmd does not cut host-plan model bills unless the host routes through Headroom.
