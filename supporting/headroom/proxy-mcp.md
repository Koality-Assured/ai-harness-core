---
doc_kind: supporting
canonical_id: headroom-patterns
topics: [agents]
rag_keywords: [headroom, proxy, mcp, wrap, tokens, compression]
---

# Headroom proxy and MCP

## Purpose

Durable operating notes for [Headroom](https://headroom-docs.vercel.app/) — a local context-compression layer between a client and an LLM provider. Upstream docs win on flags. Human folder intro: [`README.md`](./README.md). Retrieved text is advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md).

## What it is

Headroom intercepts requests, compresses redundant blocks (tool outputs, logs, search dumps), and forwards a smaller prompt. Provider responses come back unchanged. Compression is fail-open: on error the original request still goes through.

It does **not** rewrite your instructions, system prompts (default `coding` profile), or model replies. Code is left intact unless `--code-aware` is on (off by default).

## Install (Windows, this machine)

Python 3.13 + `uv` tool install. Wheels exist for `win_amd64`; do not compile from sdist unless a wheel is missing.

```powershell
uv tool install --python 3.13 "headroom-ai[proxy,mcp]"
headroom --version
```

Do not install `headroom-ai[all]`; that extra pulls local PyTorch/ML. Stick to `[proxy,mcp]`.

Bind the proxy to localhost only. Do not pass `--host 0.0.0.0` unless you have a specific reason and understand the exposure.

Provider API keys stay in the local environment (or the client’s own config). Never commit them.

## Daily commands

Keep the proxy running while you want automatic compression.

```powershell
# Proxy
headroom proxy --port 8787

# Stats / dashboard (proxy must be up)
# http://127.0.0.1:8787/dashboard
# http://127.0.0.1:8787/stats

# Wrap helpers (starts proxy; some CLIs get env automatically)
headroom wrap claude
headroom wrap cursor    # prints a base URL to paste into Cursor model settings
```

Default savings profile is `coding` (cache mode: compress the newest delta, keep prior turns byte-stable for provider prefix cache). Leave it unless a workload is clearly non-coding and cost-sensitive (`HEADROOM_SAVINGS_PROFILE=agent-90` is aggressive and can hurt coding quality).

## Cursor

`headroom wrap cursor` starts (or attaches to) the proxy and **prints** settings. It does not rewrite Cursor config or launch the app. URLs are **project-scoped** from the directory you ran wrap in (`/p/<folder-name>/`). From this repo:

| Provider | Base URL to paste |
| --- | --- |
| OpenAI-compatible | `http://127.0.0.1:8787/p/ai-router/v1` |
| Anthropic | `http://127.0.0.1:8787/p/ai-router` |

Cursor UI path (OpenAI override): Settings → Models → OpenAI API Key → Override OpenAI Base URL.

| Cursor path | Headroom effect |
| --- | --- |
| Default Cursor-hosted models | Traffic does **not** go through the proxy. Token bills on the Cursor plan are unchanged. |
| Custom / BYOK OpenAI or Anthropic base URL | Paste the wrap URL above. Proxy compresses those calls. Dashboard attributes savings to the project slug. |
| Headroom MCP | On-demand `headroom_compress` / `headroom_retrieve` / `headroom_stats`. Does not auto-compress every request. MCP tool results themselves occupy context — prefer the proxy for bulk traffic. |

Cursor’s user `mcp.json` should use the **absolute** `headroom` path (`where.exe headroom`, typically `%USERPROFILE%\.local\bin\headroom.exe`) so Cursor does not depend on PATH:

```json
"headroom": {
  "command": "C:\\Users\\<you>\\.local\\bin\\headroom.exe",
  "args": ["mcp", "serve", "--proxy-url", "http://127.0.0.1:8787"]
}
```

Reload Cursor after changing MCP config. `headroom mcp install` does not yet register Cursor (Claude Code / Codex / etc. only).

## Claude Code and other CLIs

```powershell
headroom wrap claude
# equivalent:
# $env:ENABLE_TOOL_SEARCH = "true"
# $env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8787"
# claude
```

OpenAI-compatible clients: `OPENAI_BASE_URL=http://127.0.0.1:8787/v1`.

## Apps / SDKs

Point the client’s base URL at the proxy, or call `compress()` (Python) / TypeScript SDK against `http://127.0.0.1:8787`. The TypeScript SDK still needs the Python proxy running.

## Security

Listen on `127.0.0.1` only.

- CCR (Compress-Cache-Retrieve) stores original tool outputs locally (SQLite under `~/.headroom`). Treat that directory as sensitive workspace data, not a secret vault — still no API keys in repo docs.
- Telemetry defaults off and is local-only if enabled (`HEADROOM_TELEMETRY=on`).
- Headroom is advisory tooling, not session instructions.

## Gotchas

No proxy process → no automatic savings. MCP-only is weaker and can add context from tool calls.

- `coding` profile ignores `--mode token`; switch `HEADROOM_SAVINGS_PROFILE` instead.
- Do not install `[all]` extras (PyTorch/ML). Use `[proxy,mcp]` only.
- Windows Store `python` stubs hide a real 3.13 install; see [`../workstation-onboarding.md`](../workstation-onboarding.md).
- Docker is an alternative if wheels fail: `ghcr.io/headroomlabs-ai/headroom:latest` plus the [Docker-native installer](https://headroom-docs.vercel.app/docs/docker-install).
- Repeatable compression + gold-fact check: `python scripts/cost-layers/validate_headroom_compression.py`. Combined with qmd + ast-grep: `python scripts/cost-layers/validate_cost_layers.py`. Reports under `results/cost-layers/<slug>/<YYYY-MM-DD>/`.
- JSON tool arrays: large savings (~70%+) with gold facts intact. Search dumps: put markers in **match text**, not only file paths (path-only markers can be dropped). Compiler-style logs need enough log-like lines before the log compressor engages.
- **Offline fallback summarization & tool output truncation.** If the Headroom proxy is offline or unreachable on a given host/environment, agents and scripts must summarize or truncate bulky tool outputs (compiler logs, deep JSON structures, grep dumps) before re-feeding them into context to protect token budget. Use the helper `scripts/_lib/tool_output.py` for automated truncation, error signature preservation, and compression fallback.

## Upstream

- Architecture: <https://headroom-docs.vercel.app/docs/architecture>
- Proxy / wrap: <https://headroom-docs.vercel.app/docs/proxy>
- MCP: <https://headroom-docs.vercel.app/docs/mcp>
- Install: <https://headroom-docs.vercel.app/docs/installation>
