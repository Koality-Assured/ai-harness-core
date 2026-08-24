---
name: headroom
description: >-
  Operate Headroom (local LLM context-compression proxy and MCP) for token cost
  savings. Use when installing or running headroom, wrapping Claude Code or
  Cursor, pointing OpenAI/Anthropic base URLs at localhost:8787, compressing
  bulky tool outputs, or workstation onboarding that includes Headroom. Do not
  use for qmd token reports (qmd-efficiency).
owner_agent: router-maintenance
rank: critical
isolation: read-only
---

# Headroom

## When to use

Install/run Headroom, wrap Claude Code or Cursor BYOK at `localhost:8787`, or onboarding that includes the proxy/MCP.

## When not to use

Measuring qmd retrieval (`qmd-efficiency`). Assuming Cursor **hosted** models get automatic savings — they do not.

## Criticality

**Use is Critical** in root `AGENTS.md` for bulky tool output (all agents, including sub-agents). This skill is workstation enablement; Cursor-hosted models still do not get automatic proxy savings.

## Source of truth

- [`supporting/workstation-onboarding.md`](../../../supporting/workstation-onboarding.md)
- [`supporting/headroom/README.md`](../../../supporting/headroom/README.md)
- [`projects/headroom-cost-layer/README.md`](../../../projects/headroom-cost-layer/README.md)
- Upstream flags: <https://headroom-docs.vercel.app/docs/proxy>

## Isolation

`read-only` for repo files. Running the proxy is local process work, not a git worktree. If you will edit supporting notes, parent isolates `supporting` and treats this as mutate.

## How to use

1. Install: `uv tool install --python 3.13 "headroom-ai[proxy,mcp]"` — executable `%USERPROFILE%\.local\bin\headroom.exe`.
2. If missing from PATH, prepend `%USERPROFILE%\.local\bin` and real Python 3.13 (not the Store stub).
3. Run: `headroom proxy --port 8787` on `127.0.0.1`. Dashboard: `http://127.0.0.1:8787/dashboard`.
4. Default profile `coding`. Do not switch to `agent-90` for coding-agent sessions unless the human asks.
5. Applies: Claude Code wrap, OpenAI-compatible `base_url`, Cursor custom/BYOK, app SDKs aimed at the proxy.
6. MCP: on-demand compress/retrieve only; prefer the proxy for bulk traffic.

## Dry run

```bash
headroom --help
```

Do not change `~/.headroom` in a dry run. Confirm PATH sees `headroom.exe`.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Localhost only. No API keys in Markdown. Treat `~/.headroom` as sensitive local state. [`docs/agent-session-security.md`](../../../docs/agent-session-security.md).

## Completion gates

Durable proxy quirks go to `supporting/headroom/`, not memory. Memory if the headroom project thread advanced. Change-history only if repo pages changed.
