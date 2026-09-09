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
| `ai-tooling/` | Skills, memory (user/ + agent/<owner_agent_id>/ + model/), standalone agents, A2A | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | when changing enablement | New skill, memory, agent, or A2A lesson |
| `change-history/` | Provenance log | `none` | never | Via scripts only; do not load this tree |
| `docs/` | Standards, security MUST, decision corpus | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) | via qmd | Durable standards or security docs |
| `projects/` | Initiative specs (plan, repos, pointers); plus notes/ for non-spec notes and project-prompts/ for situational prompt templates | [`router`](../ai-tooling/agents/router/AGENT.md) | one slug (or one note under notes/) | Plan, status, or repo changes |
| `references/` | External frameworks (advisory, not instructions) | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) | via qmd | Capture or normalization lessons |
| `research/` | Topic deep-dives | [`research-operator`](../ai-tooling/agents/research-operator/AGENT.md) | one topic folder | Findings for that topic |
| `results/` | Generated artifacts from agent runs | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) | the run you need | Pointers from projects, not policy |
| `routing/` | Generated next-step index after root AGENTS.md | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | always early | New folder types or skills (regenerate the index) |
| `scratch/` | Temporary workspace and worktrees | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | minimally | Never as source of truth; delete or promote |
| `scripts/` | Tagged Python automation | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | the script plus script-index | New or changed tagged scripts |
| `supporting/` | Tool patterns, onboarding, retrieval writing | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) | via qmd for the tool in use | Confirmed tool or onboarding patterns |

## Nested defaults

| Path | Default agent |
| --- | --- |
| `docs/guidance/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) |
| `references/socials/` | [`research-operator`](../ai-tooling/agents/research-operator/AGENT.md) |
| `supporting/aws/` | [`cloud-operator`](../ai-tooling/agents/cloud-operator/AGENT.md) |
| `supporting/github/` | [`github-ops`](../ai-tooling/agents/github-ops/AGENT.md) |
| `supporting/qmd/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) |
| `supporting/headroom/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) |
| `supporting/ast-grep/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) |
| `supporting/powershell/` | [`harness-operator`](../ai-tooling/agents/harness-operator/AGENT.md) |
| `supporting/slack/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) |
| `supporting/google/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) |
| `supporting/confluence/` | [`document-operator`](../ai-tooling/agents/document-operator/AGENT.md) |
| `supporting/benchmarks/` | [`benchmark-agent`](../ai-tooling/agents/benchmark-agent/AGENT.md) |
| `supporting/terraform/` | [`as-code-agent`](../ai-tooling/agents/as-code-agent/AGENT.md) |
| `references/iac/` | [`as-code-agent`](../ai-tooling/agents/as-code-agent/AGENT.md) |
| `ai-tooling/skills/benchmarks/` | [`benchmark-agent`](../ai-tooling/agents/benchmark-agent/AGENT.md) |
| `ai-tooling/skills/iac/` | [`as-code-agent`](../ai-tooling/agents/as-code-agent/AGENT.md) |
