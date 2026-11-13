# Headroom AGENTS

Durable tool recipes, context-compression proxy patterns, Model Context Protocol (MCP) integrations, and token optimization protocols.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational configurations, proxy lifecycle workflows, and compression baselines for [Headroom](https://headroom-docs.vercel.app/), intercepting and compressing redundant tool outputs, search dumps, and logs to conserve LLM context windows.

## Local Constraints

1. **Strict Output Fire-Wall:** `supporting/` is strictly an input resource and accelerator store. Agents and scripts MUST NEVER deposit generated compression benchmarks, savings ledgers, or evaluation reports into `supporting/headroom/`. All run artifacts MUST land under `results/cost-layers/headroom/<topic>/<YYYY-MM-DD>/` per [`../../results/results-conventions.md`](../../results/results-conventions.md).
2. **One-Way Dependency Invariant:** Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
3. **Local Loopback & Port 8787 Invariant:** The Headroom proxy MUST bind strictly to `127.0.0.1:8787`. Never expose the proxy across public interfaces or pass `--host 0.0.0.0`.
4. **Zero Secrets in Repository & Cache Safety:** Provider API keys stay in the local host environment; never commit API tokens to repository files or configurations. Treat the local SQLite cache (`~/.headroom`) as sensitive workspace data.
5. **Anti-Bypass Hard Gate:** Agents MUST NEVER bypass context compression when bulky outputs (such as large JSON tool responses, compiler logs, or extensive search dumps) exceed context thresholds.
6. **Offline Fallback Protocol:** If the Headroom proxy daemon is offline or unreachable, agents MUST NOT dump uncompressed bulky payloads into context; agents MUST summarize or truncate large outputs via `scripts/_lib/tool_output.py` to preserve token budget while retaining error signatures.
7. **Lightweight Wheel Dependency:** Install via `uv tool install --python 3.13 "headroom-ai[proxy,mcp]"`. Do not install `headroom-ai[all]` (avoids heavy PyTorch/ML dependencies). Default savings profile is `coding`.

## Next Hops

- Proxy configuration, MCP, and CLI wrapping: [`proxy-mcp.md`](./proxy-mcp.md)
- Machine setup & environment onboarding: [`../workstation-onboarding.md`](../workstation-onboarding.md)
- Default specialist: [`../../ai-tooling/agents/harness-operator/AGENT.md`](../../ai-tooling/agents/harness-operator/AGENT.md)
