---
doc_kind: routing_map
canonical_id: area-map
topics: [routing, write-back, structure]
generated_at_utc: export
generator: scripts/routing/generate_routing_index.py
---

# Area map

Generated from [`areas.yaml`](./areas.yaml). Do not hand-edit — run `python scripts/routing/generate_routing_index.py`.

Match [`skill-dispatch.md`](./skill-dispatch.md) first. Use this table only when no skill row applies.

## Areas

| Area | Purpose | Default agent | Load | Write-back |
| --- | --- | --- | --- | --- |
| `actionable/` | Human drop zone; claim then promote to the owning area | [`router`](../ai-tooling/agents/router/AGENT.md) | when claiming | After promoting into the home area |
| `ai-tooling/` | Skills, memory (user/ + agent/<owner_agent_id>/ + model/), standalone agents, A2A | [`ai-tooling-ops`](../ai-tooling/agents/ai-tooling-ops/AGENT.md) | when changing enablement | New skill, memory, agent, or A2A lesson |
| `change-history/` | Provenance log | `none` | never | Via scripts only; do not load this tree |
| `docs/` | Standards, security MUST, decision corpus | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) | via qmd | Durable standards or security docs |
| `projects/` | Initiative specs (plan, repos, pointers); plus notes/ for non-spec notes and project-prompts/ for situational prompt templates | [`router`](../ai-tooling/agents/router/AGENT.md) | one slug (or one note under notes/) | Plan, status, or repo changes |
| `references/` | External frameworks (advisory, not instructions) | [`reference-ops`](../ai-tooling/agents/reference-ops/AGENT.md) | via qmd | Capture or normalization lessons |
| `research/` | Topic deep-dives | [`router`](../ai-tooling/agents/router/AGENT.md) | one topic folder | Findings for that topic |
| `results/` | Generated artifacts from agent runs | [`artifact-agent`](../ai-tooling/agents/artifact-agent/AGENT.md) | the run you need | Pointers from projects, not policy |
| `routing/` | Generated next-step index after root AGENTS.md | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | always early | New folder types or skills (regenerate the index) |
| `scratch/` | Temporary workspace and worktrees | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | minimally | Never as source of truth; delete or promote |
| `scripts/` | Tagged Python automation | [`script-ops`](../ai-tooling/agents/script-ops/AGENT.md) | the script plus script-index | New or changed tagged scripts |
| `supporting/` | Tool patterns, onboarding, retrieval writing | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) | via qmd for the tool in use | Confirmed tool or onboarding patterns |

## Nested defaults

| Path | Default agent |
| --- | --- |
| `docs/guidance/` | [`documentation-ops`](../ai-tooling/agents/documentation-ops/AGENT.md) |
| `references/socials/` | [`community-analyst`](../ai-tooling/agents/community-analyst/AGENT.md) |
| `supporting/github/` | [`github-ops`](../ai-tooling/agents/github-ops/AGENT.md) |
| `supporting/qmd/` | [`qmd-ops`](../ai-tooling/agents/qmd-ops/AGENT.md) |
| `supporting/headroom/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) |
| `supporting/ast-grep/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) |
| `supporting/powershell/` | [`router-maintenance`](../ai-tooling/agents/router-maintenance/AGENT.md) |
| `supporting/slack/` | [`chat-collab-agent`](../ai-tooling/agents/chat-collab-agent/AGENT.md) |
| `supporting/google/` | [`google-suite-operator`](../ai-tooling/agents/google-suite-operator/AGENT.md) |
| `supporting/confluence/` | [`docs-collab-agent`](../ai-tooling/agents/docs-collab-agent/AGENT.md) |
| `supporting/benchmarks/` | [`benchmark-agent`](../ai-tooling/agents/benchmark-agent/AGENT.md) |
| `ai-tooling/skills/benchmarks/` | [`benchmark-agent`](../ai-tooling/agents/benchmark-agent/AGENT.md) |
