---
doc_kind: process
canonical_id: workstation-onboarding
purpose: [process]
rank: high
topics: [agents, qmd, ast-grep, headroom, python, node, github, mermaid, noir, powershell]
rag_keywords: [onboarding, python, uv, node, qmd, headroom, ast-grep, sg, gh, github, mermaid, mmdc, noir, owasp-noir, powershell, utf8, cursor, vscode, chatgpt, codex, antigravity]
---

# Workstation onboarding & tooling reference

## Purpose & architecture overview

One-time workstation setup, daily operations, and self-test verification reference for **any** supported AI agent host, human engineer, and autonomous subagent.

This document covers 100% of the repository's tooling surfaces across four primary operational layers:
1. **Console & Encoding Layer:** Windows UTF-8 console configuration (`chcp 65001`, `$OutputEncoding`), preventing character corruption in PowerShell and Python.
2. **Execution & Package Layer:** Real CPython 3.11+ / 3.13, `uv` virtual environments and package tooling, Node.js LTS (v20+), and global CLI package management.
3. **Cost & Retrieval Triad:** Markdown indexing via `@tobilu/qmd`, local context compression via Headroom proxy (port 8787) & MCP server, and precision AST code outline retrieval via `ast-grep` (`sg`).
4. **Security & Generation Layer:** GitHub CLI (`gh`) authentication and PR workflow, Mermaid CLI (`@mermaid-js/mermaid-cli` / `mmdc`) diagram generation, and OWASP Noir attack-surface container scanning (`docker run ... noir`).

Canonical repository rules live in [`../AGENTS.md`](../AGENTS.md) and apply host-agnostically across all environments.

---

## Agent hosts

Install at least the hosts you will use. Official vendor links only; Windows-first with cross-platform pointers. Do not invent unofficial installers.

| Host | Install / Resource |
| --- | --- |
| **Cursor** | [cursor.com](https://cursor.com) — download editor installer. CLI: `cursor` |
| **VS Code** | [code.visualstudio.com](https://code.visualstudio.com/) — installer or `winget install Microsoft.VisualStudioCode` |
| **ChatGPT / Codex** | ChatGPT desktop via `winget` (below) or vendor site. Codex CLI via vendor installer (below). |
| **Antigravity / Gemini** | [antigravity.google/download](https://antigravity.google/download) (Windows x64/ARM64). Optional CLI installer (below). |

Vendor installers are **OS-shell-only** (not repository scripts):

```powershell
# ChatGPT desktop (Microsoft Store ID)
winget install --id 9PLM9XGG6VKS -s msstore

# Codex CLI (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"

# Antigravity CLI (Windows PowerShell)
irm https://antigravity.google/cli/install.ps1 | iex
```

Repository rules are host-agnostic: `AGENTS.md`, skills, and scripts apply in all hosts above. Canonical agent definitions are `AGENT.md` + A2A cards under [`../ai-tooling/agents/`](../ai-tooling/agents/) and [`../ai-tooling/a2a/agent-cards/`](../ai-tooling/a2a/agent-cards/). Host stubs are thin pointers only.

---

## Cost layer triad

| Layer | What it saves | When it applies | Tooling surface |
| --- | --- | --- | --- |
| **qmd** | Context tokens: agents search Markdown collections instead of recursive tree walks | Every session in this repository | `@tobilu/qmd` via Node.js |
| **Headroom** | Tokens and API costs: compresses tool outputs, compiler logs, and search dumps | Provider API calls routed through `http://127.0.0.1:8787` or Headroom MCP | `headroom-ai[proxy,mcp]` via `uv` |
| **ast-grep** | Context & precision: structural AST outline and symbol queries on Python/JSON/YAML | Code and structured configuration inspection before edits | `ast-grep-cli` / `ast-grep` binary |

`qmd` saves context on every host. Headroom compresses API traffic when the client's base URL is pointed at `http://127.0.0.1:8787` (custom BYOK base URL) or when the agent invokes Headroom MCP tools. If the host does not route through Headroom, agents must summarize or truncate bulky tool dumps using `scripts/_lib/tool_output.py`. `ast-grep` provides precision structural filtering without replacing `qmd` or Headroom.

---

## 1. Windows UTF-8 console configuration

To prevent Unicode encoding corruption (such as box-drawing characters, emoji, quotes, and non-ASCII characters) and escape sequence collision in PowerShell on Windows:

### Active session configuration

Run this in your active PowerShell session before running complex CLI workflows:

```powershell
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001
$env:PYTHONUTF8 = "1"
```

### Persistent PowerShell profile setup

Persist UTF-8 encoding across all future PowerShell sessions by adding the configuration to your `$PROFILE`:

```powershell
if (!(Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
}
Add-Content -Path $PROFILE -Value '$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()'
Add-Content -Path $PROFILE -Value '$env:PYTHONUTF8 = "1"'
```

### Shell quoting and script execution patterns

- **Forward slashes:** Always use forward slashes (`/`) for paths across Python, git, npm, and qmd (e.g. `python scripts/cost-layers/validate_cost_layers.py`).
- **Inline `python -c` trap:** Avoid multi-line inline Python with backslashes (`\a`, `\r`, `\t` get corrupted). Write temporary scripts under `scratch/` instead.
- **Detailed notes:** See [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md).

---

## 2. Python 3.11+ & uv package manager

Repo scripts and the Headroom CLI require a genuine CPython runtime (Python 3.11+; Python 3.13 recommended), not the Windows Store execution alias stub.

### Python installation and PATH ordering

Windows: Python 3.13 standard installation path is `%LOCALAPPDATA%\Programs\Python\Python313\`.
Ensure both the root directory and `Scripts\` folder are placed on `PATH` *ahead of* `%LOCALAPPDATA%\Microsoft\WindowsApps`:

```powershell
# Verify Python version and installation location
python --version   # Expect Python 3.11.x - 3.13.x
Get-Command python | Select-Object -ExpandProperty Source
```

> [!IMPORTANT]
> If `python` opens the Microsoft Store, disable the App execution aliases for `python.exe` and `python3.exe` (Windows Settings → Apps → Advanced app settings → App execution aliases).

### uv installation & virtual environment management

`uv` provides ultra-fast Python package resolution, virtual environment creation, and isolated CLI tool management:

```powershell
# 1. Install uv via pip or official installer
python -m pip install --upgrade uv
# Standalone alternative:
# powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Verify uv installation
uv --version

# 3. Create a project virtual environment
uv venv .venv --python 3.13

# 4. Activate the virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# 5. Install dependencies into virtualenv via uv pip
uv pip install -r requirements.txt   # if requirements file exists
```

---

## 3. Node.js (v20+) & @tobilu/qmd

`qmd` is the repository's Markdown search engine providing fast BM25 keyword search and vector embedding retrieval across all docs, skills, agents, and research notes.

### Node.js installation

Install Node.js LTS (version 20 or later):

```powershell
# Via winget
winget install OpenJS.NodeJS.LTS

# Verify Node.js and npm versions
node --version   # Expect v20.x or higher
npm --version    # Expect 10.x or higher
```

### Global qmd CLI installation

Install the `@tobilu/qmd` package globally:

```powershell
npm install -g @tobilu/qmd
```

### Collection indexing and setup

Initialize and index repository Markdown collections:

```powershell
# Apply collections and generate local vector embeddings
python scripts/qmd/setup_qmd_collections.py --apply --embed

# Re-index when Markdown files are added, modified, or moved
python scripts/qmd/refresh_qmd_index.py
```

### Windows execution policy note (`PSSecurityException`)

If PowerShell blocks `qmd.ps1` execution, invoke `qmd.cmd` or call via `node`:

```powershell
# Direct invocation
qmd.cmd search "workstation onboarding"

# Or query with JSON output
qmd.cmd query --json --min-score 0.5 -n 3 "workstation onboarding"
```

Agent query patterns and collection lists: [`qmd/query-pattern.md`](./qmd/query-pattern.md).

---

## 4. ast-grep (sg CLI) structural code retrieval

`ast-grep` (`sg`) provides precision Abstract Syntax Tree search, structural pattern matching, and symbol outline extraction for Python, JavaScript, TypeScript, JSON, and YAML.

### Installation pathways

Choose the installation method suited to your environment:

```powershell
# 1. Python pip (Recommended for Python-centric workstations)
python -m pip install ast-grep-cli

# 2. npm global install
npm install -g @ast-grep/cli

# 3. Cargo (Rust)
cargo install ast-grep --locked

# 4. Scoop (Windows)
scoop install ast-grep

# 5. Homebrew (macOS / Linux)
brew install ast-grep
```

### Verification & usage

Verify that `ast-grep` (or legacy alias `sg`) is available:

```powershell
# Prefer the command name 'ast-grep' ('sg' is a legacy alias)
ast-grep --version   # Expect 0.40+ (e.g. 0.45.1)

# Quick structural scan test across repository scripts
ast-grep scan --inline-rules 'id: test, language: python, rule: {kind: function_definition}' scripts/

# Run repository ast-grep structural survival validator
python scripts/cost-layers/validate_ast_grep.py
```

Daily commands and AST query recipes: [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md).

---

## 5. Headroom local compression proxy & MCP server

[Headroom](https://headroom-docs.vercel.app/) is a local context-compression layer running between your agent host/client and LLM provider APIs. It automatically compresses bulky tool outputs, grep/search dumps, and compiler logs while preserving critical structural facts and error signatures.

### Installation via uv tool

Install `headroom-ai` into an isolated tool environment:

```powershell
uv tool install --python 3.13 "headroom-ai[proxy,mcp]"
uv tool update-shell   # Adds %USERPROFILE%\.local\bin to PATH; open a new terminal after
headroom --version     # Expect 0.35.0 or higher
```

> [!NOTE]
> Prefer `win_amd64` wheels. Do **not** install `[all]` unless you specifically require local PyTorch/ML models.

### Running the proxy server

Start the local proxy on localhost port 8787:

```powershell
# Start proxy server on default port 8787 (localhost only)
headroom proxy --port 8787
```

> [!CAUTION]
> Always bind to `127.0.0.1` (default). Do not pass `--host 0.0.0.0` unless you explicitly require network-accessible compression and understand the exposure.

### Dashboard & metrics verification

While the proxy is running, verify the monitoring endpoints:
- Dashboard: `http://127.0.0.1:8787/dashboard`
- Stats JSON: `http://127.0.0.1:8787/stats`

```powershell
# Verify proxy health via PowerShell
Invoke-RestMethod -Uri "http://127.0.0.1:8787/stats"
```

### Client configuration & wrap helpers

```powershell
# Cursor wrap helper (prints project-scoped base URL)
headroom wrap cursor

# Claude Code CLI wrap helper
headroom wrap claude
# (Sets $env:ANTHROPIC_BASE_URL="http://127.0.0.1:8787" and starts proxy)
```

#### Cursor configuration

In Cursor, configure custom OpenAI / Anthropic base URLs:
- Settings → Models → OpenAI API Key → Override OpenAI Base URL:
  `http://127.0.0.1:8787/p/ai-router/v1`
- Anthropic base URL override:
  `http://127.0.0.1:8787/p/ai-router`

#### MCP configuration (`mcp.json`)

Configure Cursor or Claude MCP settings using the absolute path to `headroom.exe`:

```json
{
  "mcpServers": {
    "headroom": {
      "command": "C:\\Users\\<USER>\\.local\\bin\\headroom.exe",
      "args": ["mcp", "serve", "--proxy-url", "http://127.0.0.1:8787"]
    }
  }
}
```

### Offline fallback & validation

- Validate compression: `python scripts/cost-layers/validate_headroom_compression.py`
- Combined cost validation: `python scripts/cost-layers/validate_cost_layers.py`
- Offline truncation fallback: If the proxy is offline, scripts and agents use [`scripts/_lib/tool_output.py`](../scripts/_lib/tool_output.py) to truncate logs and dumps.

Full proxy and MCP guide: [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md).

---

## 6. GitHub CLI (gh) & PR workflow

The GitHub CLI (`gh`) manages authentication, repository inspection, issue tracking, and pull request workflows.

### Installation & authentication

```powershell
# Install GitHub CLI
winget install --id GitHub.cli

# Authenticate with GitHub
gh auth login -w -s repo,read:org,workflow

# Configure Git credential helper to use gh credentials
gh auth setup-git

# Verify authentication status
gh auth status
gh api user --jq ".login,.name"
```

### Pull request workflow & branch discipline

Direct pushes to default/protected branches (`main`/`master`) are **strictly prohibited**. All changes must go through a feature branch and pull request:

```bash
# 1. Create a feature branch or isolate mutating work in a worktree
python scripts/routing/spawn_worktree.py check
python scripts/routing/spawn_worktree.py add --slug feature-onboarding

# 2. Stage changes and commit using Conventional Commits
git add <files>
git commit -m "docs(onboarding): overhaul workstation onboarding guide"

# 3. Push feature branch to origin
git push -u origin <branch-name>

# 4. Create pull request
gh pr create --title "docs(onboarding): overhaul workstation onboarding guide" --body "Detailed summary..."

# 5. Check CI/CD checks and merge
gh pr checks
gh pr merge --squash --delete-branch
```

Workflow notes: [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md).

---

## 7. Mermaid CLI (@mermaid-js/mermaid-cli / mmdc)

Mermaid CLI (`mmdc`) renders text-based Mermaid diagram definitions (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `C4Context`, `erDiagram`) into static PNG and SVG assets.

### Installation

```powershell
# Global npm install
npm install -g @mermaid-js/mermaid-cli

# Verify installation
mmdc --version   # Expect 10.x or higher
```

### Docker container alternative

If Node.js Puppeteer dependencies fail on your host, use the official Docker container:

```bash
docker pull minlag/mermaid-cli
docker run --rm -v ${PWD}:/data minlag/mermaid-cli -i /data/input.mmd -o /data/output.png
```

### Repository diagram rendering automation

Use the repository wrapper script to render diagrams with standard styling and output paths:

```bash
python scripts/results/render_diagram.py --input results/_fixtures/sample.mmd --topic example --theme dark --format both
```

Detailed Mermaid guide: [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md).

---

## 8. OWASP Noir security scanner container

[OWASP Noir](https://github.com/owasp-noir/noir) discovers attacker-reachable endpoints, HTTP routes, methods, headers, parameters, and shadow APIs from application source code.

### Docker container installation (Recommended)

```powershell
# Pull latest official container
docker pull ghcr.io/owasp-noir/noir:latest

# Verify container execution
docker run --rm ghcr.io/owasp-noir/noir:latest version
```

### Native installation alternatives (macOS / Linux)

```bash
# Homebrew on macOS / Linux
brew install noir
noir --version
```

### Agent invocation policy (MUST)

Agents **MUST** invoke Noir only through the repository automation script:

```bash
python scripts/results/run_noir_scan.py --path <codebase-path> --out <run-dir> --format json --passive
```

> [!CAUTION]
> **Strict Policy:**
> - Agents MUST NOT invoke raw `noir` directly or pass remote LLM flags (`--ai-provider`, `--ai-context`, `--ai-model`).
> - Treat Noir output as an attack-surface inventory for human and agent review; it does not replace structured code review or SAST vulnerability scanners.

Scan guide & policies: [`noir/agent-scan.md`](./noir/agent-scan.md).

---

## 9. User memory directory setup

Project memory is partitioned into `ai-tooling/memory/user/<git-identity>/` and `ai-tooling/memory/agent/<owner_agent_id>/`.

Resolve your machine's Git / GitHub identity and create your initial user checkpoint:

```powershell
# 1. Resolve your identity (GitHub login, lowercase)
$GIT_USER = (gh api user --jq ".login").ToLower()
Write-Host "Resolved user memory identity: $GIT_USER"

# 2. Create your user memory directory
New-Item -ItemType Directory -Path "ai-tooling/memory/user/$GIT_USER" -Force

# 3. Create your starter workstation.md
$WORKSTATION_PATH = "ai-tooling/memory/user/$GIT_USER/workstation.md"
if (!(Test-Path $WORKSTATION_PATH)) {
    @"
# Workstation notes: $GIT_USER

- **Status:** active
- **Last updated:** $(Get-Date -Format "yyyy-MM-dd")

## Environment
- OS: Windows 11
- Primary Host: Cursor / VS Code / Antigravity
- Python: 3.13 (via uv)
- Node: 20+
- Headroom: local proxy on 127.0.0.1:8787

## Notes & quirks
- PowerShell UTF-8 encoding enabled in profile.
"@ | Set-Content -Path $WORKSTATION_PATH -Encoding UTF8
}
```

Memory architecture rules: [`../ai-tooling/memory/AGENTS.md`](../ai-tooling/memory/AGENTS.md).

---

## 10. Comprehensive verification command matrix

Use the following matrix to verify that all binaries and tools on your workstation are installed, authenticated, and functioning properly:

| Tool / Surface | Verification Command | Expected Status / Output |
| --- | --- | --- |
| **Python** | `python --version` | `Python 3.11.x` - `3.13.x` (genuine CPython) |
| **uv** | `uv --version` | `uv 0.4.x` or higher |
| **Node.js** | `node --version` | `v20.x` or higher |
| **npm** | `npm --version` | `10.x` or higher |
| **qmd** | `qmd search "onboarding"` | Returns indexed Markdown matches |
| **ast-grep** | `ast-grep --version` | `ast-grep 0.40.x` or higher |
| **Headroom CLI** | `headroom --version` | `headroom 0.35.x` or higher |
| **Headroom Proxy** | `curl -s http://127.0.0.1:8787/stats` | JSON response with proxy status (when running) |
| **GitHub CLI** | `gh auth status` | `Logged in to github.com account <user>` |
| **Mermaid CLI** | `mmdc --version` | `10.x` or higher |
| **OWASP Noir** | `docker run --rm ghcr.io/owasp-noir/noir:latest version` | `Noir version ...` |
| **UTF-8 Console** | `[Console]::OutputEncoding.EncodingName` | `Unicode (UTF-8)` |
| **Wiki Structure** | `python scripts/docs/validate_wiki_structure.py` | `OK wiki structure` |
| **Cost Layers** | `python scripts/cost-layers/validate_ast_grep.py` | `{"pass": true}` |

### Automated verification script

Run the following test script in PowerShell to validate your workstation setup and print a consolidated PASS / FAIL status report:

```powershell
$checks = @(
    @{ Name = "Python 3.11+"; Cmd = { python --version } },
    @{ Name = "uv CLI"; Cmd = { uv --version } },
    @{ Name = "Node.js (v20+)"; Cmd = { node --version } },
    @{ Name = "npm CLI"; Cmd = { npm --version } },
    @{ Name = "ast-grep"; Cmd = { ast-grep --version } },
    @{ Name = "Headroom CLI"; Cmd = { headroom --version } },
    @{ Name = "GitHub CLI Auth"; Cmd = { gh auth status } },
    @{ Name = "Mermaid CLI"; Cmd = { mmdc --version } },
    @{ Name = "OWASP Noir Container"; Cmd = { docker run --rm ghcr.io/owasp-noir/noir:latest version } },
    @{ Name = "Wiki Structure"; Cmd = { python scripts/docs/validate_wiki_structure.py } }
)

Write-Host "`n=== WORKSTATION ONBOARDING VERIFICATION MATRIX ===" -ForegroundColor Cyan
foreach ($c in $checks) {
    try {
        $out = & $c.Cmd 2>&1
        if ($LASTEXITCODE -eq 0 -or $?) {
            Write-Host (" [PASS] " + $c.Name.PadRight(25) + " -> " + ($out | Select-Object -First 1)) -ForegroundColor Green
        } else {
            Write-Host (" [FAIL] " + $c.Name.PadRight(25) + " -> Exit code: $LASTEXITCODE") -ForegroundColor Red
        }
    } catch {
        Write-Host (" [FAIL] " + $c.Name.PadRight(25) + " -> " + $_.Exception.Message) -ForegroundColor Red
    }
}
Write-Host "==================================================`n" -ForegroundColor Cyan
```

---

## Related references

| Document | Purpose / Role |
| --- | --- |
| [`../AGENTS.md`](../AGENTS.md) | Repository canonical agent instructions & MUST rules |
| [`../routing/AGENTS.md`](../routing/AGENTS.md) | Generated next-step index and skill dispatch map |
| [`../ai-tooling/agents/model-tiers.md`](../ai-tooling/agents/model-tiers.md) | Platform-native model tier mapping at agent spawn |
| [`qmd/README.md`](./qmd/README.md) | qmd human install & collection overview |
| [`qmd/query-pattern.md`](./qmd/query-pattern.md) | Agent qmd query recipes & collection parameters |
| [`headroom/README.md`](./headroom/README.md) | Headroom architecture & setup guide |
| [`headroom/proxy-mcp.md`](./headroom/proxy-mcp.md) | Headroom proxy, dashboard, and MCP integration patterns |
| [`ast-grep/README.md`](./ast-grep/README.md) | ast-grep installation & precision retrieval guide |
| [`ast-grep/precision-retrieval.md`](./ast-grep/precision-retrieval.md) | ast-grep AST queries and structural rules |
| [`github/gh-workflow-notes.md`](./github/gh-workflow-notes.md) | GitHub CLI PR workflow & branch protection discipline |
| [`mermaid/agent-diagram-notes.md`](./mermaid/agent-diagram-notes.md) | Mermaid CLI diagram rendering & theme configuration |
| [`noir/agent-scan.md`](./noir/agent-scan.md) | OWASP Noir attack-surface discovery & scan wrapper |
| [`powershell/powershell-python-patterns.md`](./powershell/powershell-python-patterns.md) | Windows PowerShell encoding, escaping, and execution patterns |
| [`../docs/agent-session-security.md`](../docs/agent-session-security.md) | Security policy: untrusted context, secret handling, prompt injection |
| [`../ai-tooling/memory/AGENTS.md`](../ai-tooling/memory/AGENTS.md) | User memory vs agent memory structure |
