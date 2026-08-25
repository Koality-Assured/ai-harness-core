---
doc_kind: process
canonical_id: workstation-onboarding
purpose: [process]
rank: high
topics: [onboarding, python, qmd, ast-grep, headroom]
rag_keywords: [onboarding, python, path, qmd, headroom, ast-grep, utf8, noir, smart-app-control]
---

# Workstation onboarding

## Purpose

What this repo needs on a workstation, plus the gotchas that fail silently if skipped. Tool recipes live under `supporting/<tool>/`. Session rules: [`../AGENTS.md`](../AGENTS.md).

## Expected tools

This repo expects a real CPython, Node for qmd, and the cost-layer CLIs. Optional tools matter only when you run those workflows.

| Tool | Need | Min | Why | Notes |
| --- | --- | --- | --- | --- |
| CPython | required | 3.11+ (3.13 recommended) | Repo scripts | Real interpreter, not the Windows Store stub |
| Node.js | required | 20+ | `@tobilu/qmd` | npm comes with it |
| qmd | required | current `@tobilu/qmd` | Markdown search | [`qmd/query-pattern.md`](./qmd/query-pattern.md) |
| Git | required | 2.40+ | Worktrees, branches | Vendor install |
| ast-grep | required | 0.40+ | Structured-file lookup | [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md) |
| uv | recommended | 0.4+ | Isolated Python tools (Headroom) | Vendor install |
| Headroom | recommended | 0.35+ | Compress bulky dumps | Else `scripts/_lib/tool_output.py`. [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md) |
| GitHub CLI (`gh`) | if you use GitHub | current | Auth, PRs | [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md) |
| Mermaid CLI (`mmdc`) | optional | 10+ | Offline diagram render | [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) |
| Docker / Noir | optional | — | Attack-surface inventory | Wrapper only. [`noir/agent-scan.md`](./noir/agent-scan.md) |

Use the vendor’s installer. `--version` is enough to confirm.

## Agent host

Install whichever agent host you use from the official vendor. `AGENTS.md`, skills, and scripts apply on every host. Canonical agents are `ai-tooling/agents/<id>/AGENT.md` plus A2A cards. Host stubs are thin pointers only. Branch and PR steps live in `AGENTS.md` and [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md), not here.

## Repo gotchas

These fail silently if omitted. The linked page has the recipe when one is needed.

| Gotcha | Constraint |
| --- | --- |
| Windows Store `python` stub | `python` may open the Store. Disable App execution aliases for `python.exe` / `python3.exe`. Use python.org (or equivalent) CPython. Typical 3.13 layout: `%LOCALAPPDATA%\Programs\Python\Python313\`. |
| PATH order | Put that Python directory and its `Scripts\` folder on `PATH` ahead of `%LOCALAPPDATA%\Microsoft\WindowsApps`. pip-installed `ast-grep.exe` lands in `Scripts\`. |
| Windows UTF-8 | Default PowerShell encoding corrupts non-ASCII CLI output. Configure the console per [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md). |
| qmd execution policy / cache access | If PowerShell blocks `qmd.ps1`, call `qmd.cmd` (or `node`). Before any setup, run the qmd preflight; a present-but-inaccessible index is a sandbox or permissions issue, not a reason to rebuild. [`qmd/query-pattern.md`](./qmd/query-pattern.md). |
| Headroom bind and extras | Bind `127.0.0.1`; do not pass `--host 0.0.0.0`. Install `headroom-ai[proxy,mcp]`. Do not install `[all]` (local PyTorch/ML). [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md). |
| Noir | Agents MUST call `python scripts/results/run_noir_scan.py`. Never invoke raw `noir` or pass `--ai-provider` / `--ai-context` / `--ai-model`. [`noir/agent-scan.md`](./noir/agent-scan.md). |
| User memory | Create `ai-tooling/memory/user/<git-identity>/` (lowercase GitHub login or other stable id). [`../ai-tooling/memory/user/AGENTS.md`](../ai-tooling/memory/user/AGENTS.md). |
| Windows Smart App Control | Unsigned or untrusted binaries may fail to start. Run the read-only preflight; do not disable SAC. [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md). |

## Windows execution-control preflight

On Windows, report SAC mode before treating a missing CLI as a PATH or install failure. If a binary was blocked, capture only the Code Integrity event ID and file path, then recover with a signed vendor build, a host-bundled runtime, or an enterprise App Control policy. Commands: [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md).

## Verify

Confirm each required tool is on `PATH`. If you use `gh`, it should already be authenticated. Before qmd setup, run `python scripts/qmd/qmd_preflight.py --inspect-hooks`. Reuse a healthy existing index; never recreate one by default. Only when preflight reports a missing index and the user explicitly approves the mutation, run `python scripts/qmd/setup_qmd_collections.py --apply --approved-by-user --create-missing` (add `--embed` only when embedding is also approved). After later add/remove/rename, use `python scripts/qmd/refresh_qmd_index.py --approved-by-user` only as the approved session-end mutation.

Repo validators exist; run them when you need a check:

- `python scripts/docs/validate_wiki_structure.py`
- `python scripts/cost-layers/validate_cost_layers.py` (or the per-layer scripts under `scripts/cost-layers/`)

## Related

| Page | What it's for |
| --- | --- |
| [`qmd/query-pattern.md`](./qmd/query-pattern.md) | qmd search / get |
| [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md) | ast-grep CLI |
| [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md) | Headroom proxy / MCP |
| [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md) | `gh` and PRs |
| [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) | `mmdc` |
| [`noir/agent-scan.md`](./noir/agent-scan.md) | Noir wrapper |
| [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md) | PowerShell encoding and quoting |
| [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md) | Read-only SAC / Code Integrity preflight |
| [`../ai-tooling/memory/AGENTS.md`](../ai-tooling/memory/AGENTS.md) | User vs agent memory |
