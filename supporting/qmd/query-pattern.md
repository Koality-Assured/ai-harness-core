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

## The QMD Retrieval Suite & Decision Matrix

QMD provides four complementary retrieval primitives and three lifecycle operations. All retrieval MUST execute from `scratch/qmd-main` (the persistent detached checkout of `origin/main`).

| Primitive | Technology | When to Use | Command Pattern | Latency |
| :--- | :--- | :--- | :--- | :--- |
| **`qmd search`** | BM25 lexical keyword index (No LLM) | Exact terms, filenames, code symbols, titles, constants, and known phrase anchors. **Default first-hop.** | `qmd search --format json --min-score 0.5 -n 5 "keywords"` | ~5–15ms |
| **`qmd vsearch`** | Dense vector cosine similarity (Gemma embeddings) | Conceptual / semantic discovery when exact terms are unknown, phrasing diverges from source, or vocabulary is uncertain. No LLM reranker penalty. | `qmd vsearch --format json --min-score 0.4 -n 5 "concept"` | ~1–3s |
| **`qmd query`** | Hybrid Search (BM25 + Vectors + HyDE + LLM Reranking) | Complex, multi-intent, or ambiguous discovery. Agent authors structured query documents (`intent:`, `lex:`, `vec:`, `hyde:`). | `qmd query --format json --min-score 0.5 -n 5 $'intent: ...\nlex: ...\nvec: ...'` | ~30–60s |
| **`qmd get`** | Exact line-numbered document reader | Reading a single targeted document or specific line window by docid or path. | `qmd get "#docid"` or `qmd get "#docid:10:30"` | <5ms |
| **`qmd multi-get`**| Batch document reader | Fetching multiple candidate documents in a single atomic tool call via comma-separated `#docids` or glob patterns. | `qmd multi-get "#doc1,#doc2" --format md -l 100` | ~10–30ms |

### Anti-Fallback Hard Gate

Agents MUST NOT bypass QMD with recursive shell searches (`Get-ChildItem -Recurse`, `Select-String`, `git grep`, raw `find`, or PowerShell loops). Shell crawling is strictly prohibited unless:
1. QMD search and vsearch across all relevant collections returned zero candidates, OR
2. The search explicitly targets untracked/dirty local scratch files deliberately excluded from QMD collections.

## 1. Default Lexical Search (`qmd search`)

Use `qmd search` first for fast, deterministic lexical precision:

```bash
pushd scratch/qmd-main
qmd search --format json --min-score 0.5 -n 5 "your search terms"
popd
```

When the target area is known, filter with `-c <collection>` so `results/` reports or unrelated areas do not dilute rankings:

```bash
pushd scratch/qmd-main
qmd search --format json --min-score 0.5 -n 5 -c docs "session security"
popd
```

## 2. Pure Vector Similarity (`qmd vsearch`)

When exact keywords are unknown or lexical search returns zero hits because the user's phrasing does not match the source text, use `qmd vsearch`. It computes embedding cosine similarity across pre-embedded chunks without paying the heavy LLM reranking latency of `qmd query`:

```bash
pushd scratch/qmd-main
qmd vsearch --format json --min-score 0.4 -n 5 "isolated subagent execution environment"
popd
```

## 3. Structured Hybrid Query (`qmd query`)

Use `qmd query` when the query is highly nuanced, conceptual, or requires active disambiguation. Rather than passing a bare sentence and relying on the small local model's expander, author a structured query document with `intent:`, `lex:`, `vec:`, and `hyde:` lines:

```bash
pushd scratch/qmd-main
qmd query --format json --min-score 0.5 -n 5 $'intent: Find rules for subagent state isolation and firebreaks, avoiding general Docker containers.\nlex: clean-slate specialist dispatch subagent fork_turns context\nvec: isolated context window without transcript inheritance\nhyde: Subagents execute in isolated context windows with clean state. Do not pass parent conversation transcripts.'
popd
```

### Structured Query Grammar Rules
- `intent:`: Express what to retrieve AND what to reject. Essential for steering away from false positives.
- `lex:`: Exact keywords, code symbols, filenames, and rare vocabulary you expect in the document.
- `vec:`: Natural language paraphrasing in source-like wording.
- `hyde:`: Hypothetical answer excerpt that would satisfy the retrieval need.

## 4. Batch Retrieval (`qmd multi-get`)

Avoid serial single-file `qmd get` loops that pollute context with redundant tool calls. Use `qmd multi-get` to batch-fetch candidates:

```bash
# Fetch multiple documents by comma-separated docids
pushd scratch/qmd-main
qmd multi-get "#e22229,#860a46" --format md -l 100
popd

# Batch fetch using glob patterns
pushd scratch/qmd-main
qmd multi-get "standards/*.md" --max-bytes 32768 --format md
popd
```

Parameters:
- `-l <num>`: Maximum lines per document (prevents dumping massive files).
- `--max-bytes <num>`: Skip files larger than byte limit (default 65536).
- `--format <md|json|cli>`: Output format. Prefer `md` for readable LLM ingestion.

## 5. Index Lifecycle & Maintenance Protocol

Keep the repository QMD index healthy and synchronized across three operations:

1. **Incremental BM25 Freshness (`qmd update`)**:
   - Authorized and routine before lookup from `scratch/qmd-main` after syncing with `origin/main`.
   - Indexes new, updated, and removed Markdown files into the SQLite BM25 full-text index in sub-seconds.
   - Does not require user confirmation or reconfiguration approval. Never run with `--pull` from a worktree.

2. **Vector Embedding Hydration (`qmd embed`)**:
   - Generates 300M Gemma vector representations for newly modified/added document chunks.
   - Run from `scratch/qmd-main` when `qmd update` reports pending hashes (`Run 'qmd embed' to update embeddings`).
   - Caps memory and timeout gracefully (`--timeout 10`).

3. **Orphan Reclaiming & Compaction (`qmd cleanup`)**:
   - Drops stale document records, purges orphaned vector chunks, compacts FTS5, and vacuums SQLite.
   - Run periodically or when `qmd update` reports orphaned embedding chunks. Safe and deterministic.

## Validation

Repeatable health/relevance/token/accuracy check: `python scripts/qmd/validate_qmd_retrieval.py`. Empirical benchmark comparing QMD suite primitives against grep fallbacks: `python scripts/qmd/benchmark_qmd_suite.py`. Combined with Headroom and ast-grep: `python scripts/cost-layers/validate_cost_layers.py`. Cost-layer reports land under `results/cost-layers/<slug>/<YYYY-MM-DD>/` — [`../../results/results-conventions.md`](../../results/results-conventions.md).

## Query pitfalls (validated 2026-08-19)

- **Installed CLI missing only in an agent shell.** Compare process `PATH` with persisted Windows User/Machine PATH before reinstalling. A desktop host started before a PATH update can keep passing its old environment to new shells. Restart the desktop host after confirming the installed shim and existing index; a fresh child of the stale host alone does not refresh inherited PATH. For an active diagnostic, prepend persisted User PATH to that process, then verify `qmd search` and `qmd get`. Do not pin a copied machine PATH in portable configuration or recreate the index.
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
