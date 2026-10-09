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

## Collections & Main-Checkout Retrieval

Collections are dynamically derived from [`routing/areas.yaml`](../../routing/areas.yaml) via `scripts/qmd/setup_qmd_collections.py` and stored with relative paths in repository-local `.qmd/index.yml`.

### Use a fresh `main` checkout

For ai-router, every Markdown retrieval command (`qmd search`, `qmd get`, and `qmd query`) MUST run from a fresh checkout of `main`. Never retrieve from a task worktree: its branch can contain unmerged guidance, and QMD chooses an index local to the current checkout.

Identify the main checkout from any location with `git worktree list --porcelain`; select the `worktree <path>` entry paired with `branch refs/heads/main`. Verify it with `git -C "<path>" rev-parse --show-toplevel` and `git -C "<path>" branch --show-current`, then fetch and compare commits:

```bash
git -C "<main-path>" fetch --no-tags origin refs/heads/main:refs/remotes/origin/main
git -C "<main-path>" rev-parse HEAD
git -C "<main-path>" rev-parse origin/main
```

Use the persistent detached QMD checkout at `<repo-root>/scratch/qmd-main` for all retrievals. It is a registered `origin/main` snapshot, not a task branch. Locate it through `git worktree list --porcelain`; do not create a new QMD checkout for each lookup. If the path is occupied by unrelated data or another checkout, preserve it and choose a unique suffix such as `scratch/qmd-main-<UTC>-<random>` for one persistent replacement. Fetch `origin/main` from the repository root before each retrieval. Confirm the dedicated checkout has no tracked or untracked changes; its ignored `.qmd/index.sqlite` is expected and must be preserved. If `HEAD` is behind `origin/main`, verify it is an ancestor with `git -C "<qmd-path>" merge-base --is-ancestor HEAD origin/main`, then advance the clean dedicated checkout with `git -C "<qmd-path>" merge --ff-only origin/main`. If it is dirty, diverged, or cannot be fast-forwarded, leave it untouched and create or reuse another dedicated path. Never reset or remove another checkout.

The tracked `.qmd/index.yml` is present in a fresh worktree; QMD creates the ignored local SQLite index there. Do not copy or overwrite the index database, reconfigure collections, or remove the dedicated QMD checkout while ignored index data remains. If the tracked config is missing or inaccessible, stop and report the setup gap rather than using a task worktree.

Run `qmd update` from the persistent QMD root before retrieval. This incremental local freshness update is authorized and does not change collection configuration; do not use `qmd update --pull`. Then run QMD search/get/query from that same root. Preserve any untracked or ignored data in the selected checkout.

Each checkout may have its own `.qmd/index.sqlite` and `.qmd/index.yml`, but only the persistent detached QMD source at `scratch/qmd-main` (or its registered unique-suffix replacement) is an authorized retrieval source for ai-router. Relative collection paths make the setup portable; they do not make a task worktree an approved retrieval source.

| Collection | Glob / path | Context description |
| --- | --- | --- |
| `routing` | `routing/**/*.md` | Second-hop maps — read early |
| `docs` | `docs/**/*.md` | Decisions, requirements, reinforcement |
| `projects` | `projects/**/*.md` | Specs and plans |
| `references` | `references/**/*.md` | External frameworks (advisory) |
| `research` | `research/**/*.md` | Topic deep-dives |
| `supporting` | `supporting/**/*.md` | Tool patterns (Cloudflare, GitHub, qmd, …) |
| `ai-tooling` | `ai-tooling/**/*.md` | Skills, memory templates, A2A |
| `scripts` | `scripts/**/*.md` | Script index and Python automation docs |
| `actionable` | `actionable/**/*.md` | Human drop-zone items |
| `results` | `results/**/*.md` | Generated Markdown reports only |

Do **not** add: `change-history/`, `scratch/`, large binaries under `results/`, `.git/`, virtualenvs, caches. Root `AGENTS.md` and `README.md` are **not** in any collection (Critical rules stay in the hop; README ignore is applied automatically).

## Preflight before setup or collection reconfiguration

Reuse the machine's existing qmd index. Do not run `init`, `collection add`, `update`, or `embed` merely because onboarding or a worktree starts. For an actual lookup, `qmd update` from the verified main root is authorized when the index may lag. Before setup or collection reconfiguration, use the no-mutation inspector:

```bash
python scripts/qmd/qmd_preflight.py --inspect-hooks
```

Its state determines the next action:

| State | Action |
| --- | --- |
| `healthy_reusable` | Reuse it. Do not set up collections again. |
| `existing_unprobed` | Treat it as reusable candidate. Use `--probe-cli` only when an explicit status diagnostic is needed. |
| `inaccessible_sandbox_or_permissions` | Do not recreate it. Retry the read probe on a clean/full host and investigate sandbox or file permissions. |
| `missing` | Ask the user before setup. Inspect hooks, then use `setup_qmd_collections.py --apply --approved-by-user`; add `--embed` only when the user approved embedding. |
| `cli_unavailable` | Install/repair qmd, then rerun preflight; an existing index is not evidence that it should be recreated. |

The setup script refuses mutation without explicit approval and writes project-local `.qmd/index.yml` by default. Record a host-specific wrapper path, index location label, successful reuse method, or inaccessible-state recovery in `ai-tooling/memory/user/<stable-id>/`; keep general pages and skills free of personal paths.

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

## Lookup freshness and separate index maintenance

Before retrieval, run `qmd update` from the persistent detached QMD root after syncing it to current `origin/main`. This routine freshness step is authorized, incremental, and does not need setup approval. Never run it from a task worktree or use `--pull`. Collection changes remain separate: use the preflight and required approval before setup or reconfiguration. Any additional embedding/cleanup workflow through `python scripts/qmd/refresh_qmd_index.py` remains a separate maintenance action and follows its own preflight and approval requirements.

## Validation

Repeatable health/relevance/token/accuracy check: `python scripts/qmd/validate_qmd_retrieval.py`. Combined with Headroom and ast-grep: `python scripts/cost-layers/validate_cost_layers.py`. Cost-layer reports land under `results/cost-layers/<slug>/<YYYY-MM-DD>/` — [`../../results/results-conventions.md`](../../results/results-conventions.md).

## Query pitfalls (validated 2026-08-19)

- **Re-index after new Markdown.** A stale index missed pages until `qmd update` + `qmd embed`.
- **Ampersands zero BM25.** `qmd search "MITRE ATT&CK"` returned no hits; `qmd search "mitre attack"` ranked the right page. Avoid `&` in lookup strings.
- **Windows multiline query docs and PowerShell execution policies.** `qmd.cmd` goes through cmd.exe and drops `lex:`/`vec:` newlines. Running `qmd` directly in PowerShell can trigger `PSSecurityException` on `qmd.ps1` if PowerShell execution policy is default (`Restricted` or undefined). Resolve for the current user via `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force` (no admin elevation required), or invoke `qmd.cmd` / Python scripts (which use `resolve_qmd()` to prefer `qmd.cmd` and `node.exe`). For structured query documents with embedded newlines, invoke `node.exe` with the CLI directly or use BM25 `qmd search`.
- **Vague area questions rank indexes.** Prefer distinctive tokens from the owning page, or pass `-c <collection>`.
- **Extra query words AND-zero BM25.** Keep lookup strings to tokens that actually appear in the target.
- **Structured `lex`+`vec` without rerank** can rank the wrong area. Reranked hybrid recovered those; BM25 with distinctive keywords did not need it.
- **`results/` is indexed.** Generated reports can pollute later searches. Pass `-c`.
- **Broad needs shrink savings.** Tighten terms or pass `-c`.
- Token savings vs walking trees are **context-window** savings. qmd does not cut host-plan model bills unless the host routes through Headroom.

## Windows PATH command resolution (validated 2026-10-07)

Use this recovery only when `qmd` is not found in a shell. Compare the process PATH with persisted User and Machine PATH before reinstalling. By default, a process inherits its environment from its parent when it starts, so shells launched by a desktop host that predates a PATH update can keep the old PATH ([Microsoft process environment variables](https://learn.microsoft.com/en-us/windows/win32/procthread/environment-variables)). After confirming the installed `qmd` shim and existing project index, restart that host; a child shell alone still inherits its stale environment. For a one-shell diagnostic, prepend the persisted User PATH with `$env:PATH = "$([Environment]::GetEnvironmentVariable('Path', 'User'));$env:PATH"`, then verify command resolution with `Get-Command qmd` and run `qmd search` and `qmd get`. Do not copy a machine PATH into portable configuration or recreate the index for a command-resolution failure. If `qmd` resolves but PowerShell raises `PSSecurityException`, follow the [PowerShell execution-policy guidance](../powershell/powershell-python-patterns.md#pattern-i-script-execution-policy-and-npm-global-shims-qmdps1-vs-qmdcmd).
