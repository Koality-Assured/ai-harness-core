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

Use the `Need` column to distinguish repository-wide prerequisites (`required`) from tools needed only for specific workflows (`optional`).

| Tool | Need | Min | Why | Notes |
| --- | --- | --- | --- | --- |
| CPython | required | 3.11+ (3.13 recommended) | Repo scripts | Real interpreter, not the Windows Store stub |
| Node.js | required | 20+ | `@tobilu/qmd` | npm comes with it |
| qmd | required | current `@tobilu/qmd` | Markdown search | [`qmd/query-pattern.md`](./qmd/query-pattern.md) |
| Git | required | 2.40+ | Worktrees, branches | Vendor install |
| ast-grep | required | 0.40+ | Structured-file lookup | [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md) |
| uv | required | 0.4+ | Install and manage isolated Python tools, including Headroom | Install from Astral; see the setup below |
| Headroom | required | 0.35+ | Compress bulky tool outputs | Install `headroom-ai[proxy,mcp]`; [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md) |
| GitHub CLI (`gh`) | if you use GitHub | current | Auth, PRs | [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md) |
| AWS CLI (`aws`) | optional | current | AWS Organizations & SSO | [Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html); [configure IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) |
| Google Cloud CLI (`gcloud`) | optional | current | GCP Resource Manager & ADC | [Install](https://docs.cloud.google.com/sdk/docs/install-sdk/); [initialize and authorize](https://docs.cloud.google.com/sdk/docs/initialize) |
| Azure CLI (`az`) | optional | current | Azure Management Groups & Entra | [Install](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli); [authenticate](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli?view=azure-cli-latest) |
| Google Workspace APIs | optional | current | Drive, Gmail, Docs & Workspace Admin | [Get started](https://developers.google.com/workspace/guides/get-started); [configure credentials](https://developers.google.com/workspace/guides/create-credentials) |
| Mermaid CLI (`mmdc`) | optional | 10+ | Offline diagram render | [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) |
| Docker / Noir | optional | — | Attack-surface inventory | Wrapper only. [OWASP Noir installation](https://owasp-noir.github.io/noir/get_started/installation/) |
| Web distillation (`trafilatura`, `readability-lxml`, `markdownify`, `httpx`) | required | current | Local HTML distillation & prompt injection defense | `pip install trafilatura readability-lxml markdownify httpx`. Used by `scripts/research/local_webfetch.py`. |

Use each vendor’s installer for required tools. The commands below cover uv and Headroom.

## Install uv and Headroom

Install uv from [Astral’s official instructions](https://docs.astral.sh/uv/getting-started/installation/), then use uv’s isolated tool environment for Headroom. On Windows, run the standalone installer in PowerShell; on macOS or Linux, use Astral’s shell installer:

```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```sh
# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a fresh terminal after installing uv. Install Headroom with the proxy and MCP extras required by this repo; do not use `[all]` because it installs unrelated ML dependencies:

```powershell
uv tool install --python 3.13 "headroom-ai[proxy,mcp]"
uv tool update-shell  # if the Headroom executable directory is not on PATH
```

If Windows uv downloads CPython 3.13 but reports `Missing expected target directory for Python minor version link`, install from the downloaded interpreter’s versioned path:

```powershell
$uvExe = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
$pythonDir = & $uvExe python dir
$python313Dir = Get-ChildItem -Path $pythonDir -Directory -Filter 'cpython-3.13.*-windows-x86_64-none' |
    Sort-Object Name -Descending | Select-Object -First 1
$python313 = Join-Path $python313Dir.FullName 'python.exe'
& $uvExe tool install --python $python313 "headroom-ai[proxy,mcp]"
```

The Windows tools are normally installed under `%USERPROFILE%\.local\bin`. If the new command is not visible, confirm that directory is on `PATH` and open a fresh terminal. If selecting a system Python, use a real CPython 3.13 installation; do not select the Windows Store execution-alias stub.

Verify the install without starting a proxy:

```powershell
uv --version
headroom --version
headroom --help
```

The proxy stays stopped until a workflow explicitly needs it. Headroom is still a required workstation tool even when a session must use the summarization fallback in [`scripts/_lib/tool_output.py`](../scripts/_lib/tool_output.py). See [Headroom’s install guide](https://headroom-docs.vercel.app/docs/installation) for vendor details.

## Agent host

Install whichever agent host you use from the official vendor. `AGENTS.md`, skills, and scripts apply on every host. Canonical agents are `ai-tooling/agents/<id>/AGENT.md` plus A2A cards. Host stubs are thin pointers only. Branch and PR steps live in `AGENTS.md` and [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md), not here.

## Repo gotchas

These fail silently if omitted. The linked page has the recipe when one is needed.

| Gotcha | Constraint |
| --- | --- |
| Windows Store `python` stub | `python` may open the Store. Disable App execution aliases for `python.exe` / `python3.exe`. Use python.org (or equivalent) CPython. Typical 3.13 layout: `%LOCALAPPDATA%\Programs\Python\Python313\`. |
| PATH order | Put that Python directory and its `Scripts\` folder on `PATH` ahead of `%LOCALAPPDATA%\Microsoft\WindowsApps`. pip-installed `ast-grep.exe` lands in `Scripts\`. |
| Windows UTF-8 | Default PowerShell encoding corrupts non-ASCII CLI output. Configure the console per [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md). |
| qmd execution policy / cache access | Windows PowerShell defaults to `Restricted` script execution, blocking npm-installed `qmd.ps1` with `PSSecurityException`. Fix for current user (no admin rights needed): `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force`. Alternatively call `qmd.cmd` (or `node`). Before any setup, run the qmd preflight; a present-but-inaccessible index is a sandbox or permissions issue, not a reason to rebuild. [`qmd/query-pattern.md`](./qmd/query-pattern.md). |
| Headroom bind and extras | Bind `127.0.0.1`; do not pass `--host 0.0.0.0`. Install `headroom-ai[proxy,mcp]`. Do not install `[all]` (local PyTorch/ML). [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md). |
| Cloud & LLM credentials | Never store static keys in config files. Use AWS CLI SSO (`aws configure sso`), GCP Application Default Credentials (`gcloud auth application-default login`), Azure Entra login (`az login`), and ephemeral environment variables for LLM APIs. |
| Google Workspace OAuth | Choose OAuth 2.0 or service-account credentials for the API and data-access needs. Use least-privileged scopes and keep credentials and resource identifiers out of source control. See [Google Workspace authentication guidance](https://developers.google.com/workspace/guides/auth-overview). |
| Noir | This template does not package a Noir scan wrapper. If a task requires an OWASP Noir scan, use a locally approved tool and its current [official installation guidance](https://owasp-noir.github.io/noir/get_started/installation/); report a capability gap when no local wrapper is available. |
| User memory | Create `ai-tooling/memory/user/<git-identity>/` (lowercase GitHub login or other stable id). [`../ai-tooling/memory/user/AGENTS.md`](../ai-tooling/memory/user/AGENTS.md). |
| Windows Smart App Control | Unsigned or untrusted binaries may fail to start. Run the read-only preflight; do not disable SAC. [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md). |
| Cursor `.cursorignore` vs worktrees | `.cursorignore` blocks Agent Read/Write/Tab/@. Never list `scratch/worktrees/` there. Use `.gitignore` and `.cursorindexingignore` so extra checkouts stay out of embeddings. [Ignore file](https://cursor.com/docs/reference/ignore-file). |
| Windows Cursor Shell sandbox | The Windows sandbox helper may only provide a network proxy, so Shell cannot enforce `workspace_readwrite`. Isolate CLI and worktree Shell then need host `all` permissions. Do not treat that as a reason to skip worktrees. |

## Windows execution-control preflight

On Windows, report SAC mode before treating a missing CLI as a PATH or install failure. If a binary was blocked, capture only the Code Integrity event ID and file path, then recover with a signed vendor build, a host-bundled runtime, or an enterprise App Control policy. Commands: [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md).

## Verify

Confirm each required tool is on `PATH`. If you use `gh`, it should already be authenticated. Before qmd setup, run `python scripts/qmd/qmd_preflight.py --inspect-hooks`. Reuse a healthy existing index; never recreate one by default. Only when preflight reports a missing index and the user explicitly approves the mutation, run `python scripts/qmd/setup_qmd_collections.py --apply --approved-by-user --create-missing` (add `--embed` only when embedding is also approved). After later add/remove/rename, use `python scripts/qmd/refresh_qmd_index.py --approved-by-user` only as the approved session-end mutation.

Repo validators exist; run them when you need a check:

- `python scripts/docs/validate_router_structure.py`
- `python scripts/cost-layers/validate_cost_layers.py` (or the per-layer scripts under `scripts/cost-layers/`)

## Related

| Page | What it's for |
| --- | --- |
| [`qmd/query-pattern.md`](./qmd/query-pattern.md) | qmd search / get |
| [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md) | ast-grep CLI |
| [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md) | Headroom proxy / MCP |
| [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md) | `gh` and PRs |
| [Google Workspace developer guide](https://developers.google.com/workspace/guides/get-started) | Google Workspace operations & auth |
| [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) | `mmdc` |
| [OWASP Noir installation guide](https://owasp-noir.github.io/noir/get_started/installation/) | Noir tooling |
| [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md) | PowerShell encoding and quoting |
| [`powershell/windows-execution-control.md`](./powershell/windows-execution-control.md) | Read-only SAC / Code Integrity preflight |
| [`../ai-tooling/memory/AGENTS.md`](../ai-tooling/memory/AGENTS.md) | User vs agent memory |
