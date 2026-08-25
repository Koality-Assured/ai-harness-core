---
doc_kind: process
canonical_id: workstation-onboarding
purpose: [process]
rank: high
topics: [onboarding, python, qmd, ast-grep, headroom]
rag_keywords: [onboarding, python, path, qmd, headroom, ast-grep, utf8, noir]
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
| AWS CLI (`aws`) | optional (cloud-admin) | 2.15+ | AWS Organizations & SSO | [`../docs/guidance/cloud-aws-setup.md`](../docs/guidance/cloud-aws-setup.md) |
| Google Cloud SDK (`gcloud`) | optional (cloud-admin) | current | GCP Resource Manager & ADC | [`../docs/guidance/cloud-gcp-setup.md`](../docs/guidance/cloud-gcp-setup.md) |
| Azure CLI (`az`) | optional (cloud-admin) | 2.50+ | Azure Management Groups & Entra | [`../docs/guidance/cloud-azure-setup.md`](../docs/guidance/cloud-azure-setup.md) |
| Google Workspace APIs | optional (google-suite) | current | Drive, Gmail, Docs & Workspace Admin | [`google/google-suite-patterns.md`](./google/google-suite-patterns.md) |
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
| qmd execution policy | If PowerShell blocks `qmd.ps1`, call `qmd.cmd` (or `node`). Pitfalls: [`qmd/query-pattern.md`](./qmd/query-pattern.md). |
| Headroom bind and extras | Bind `127.0.0.1`; do not pass `--host 0.0.0.0`. Install `headroom-ai[proxy,mcp]`. Do not install `[all]` (local PyTorch/ML). [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md). |
| Cloud & LLM credentials | Never store static keys in config files. Use AWS CLI SSO (`aws configure sso`), GCP Application Default Credentials (`gcloud auth application-default login`), Azure Entra login (`az login`), and ephemeral environment variables for LLM APIs. |
| Google Workspace OAuth | Use ADC or Workload Identity Federation. Dedicated test folder IDs ([REDACTED_GOOGLE_DRIVE_TEST_FOLDER]) are scrubbed upon sync export. [`google/google-suite-patterns.md`](./google/google-suite-patterns.md). |
| Noir | Agents MUST call `python scripts/results/run_noir_scan.py`. Never invoke raw `noir` or pass `--ai-provider` / `--ai-context` / `--ai-model`. [`noir/agent-scan.md`](./noir/agent-scan.md). |
| User memory | Create `ai-tooling/memory/user/<git-identity>/` (lowercase GitHub login or other stable id). [`../ai-tooling/memory/user/AGENTS.md`](../ai-tooling/memory/user/AGENTS.md). |

## Verify

Confirm each required tool is on `PATH`. If you use `gh`, it should already be authenticated. Index Markdown once per machine with `python scripts/qmd/setup_qmd_collections.py --apply --embed`. After later add/remove/rename, run `python scripts/qmd/refresh_qmd_index.py`.

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
| [`google/google-suite-patterns.md`](./google/google-suite-patterns.md) | Google Workspace operations & auth |
| [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) | `mmdc` |
| [`noir/agent-scan.md`](./noir/agent-scan.md) | Noir wrapper |
| [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md) | PowerShell encoding and quoting |
| [`../ai-tooling/memory/AGENTS.md`](../ai-tooling/memory/AGENTS.md) | User vs agent memory |
