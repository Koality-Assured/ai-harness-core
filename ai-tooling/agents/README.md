# Standalone agents

Human overview: specialist definitions live in `<id>/AGENT.md`. Optional host stubs under `.cursor/agents/` only point here.

**Agents do not use this README as a catalog.** Catalogs are `AGENT.md` (Schema V2) + [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) / [`../../routing/area-map.md`](../../routing/area-map.md). Tiers: [`model-tiers.md`](./model-tiers.md).

Human index (not agent SoT):

### Broad-sweeping operators

| Operator | Role / Scope | Tier |
| --- | --- | --- |
| [`harness-operator/`](./harness-operator/) | Harness lifecycle, control plane, cost layers, skill/agent builder, repository maintenance | standard |
| [`document-operator/`](./document-operator/) | Technical writing, diagrams, reports, Confluence/Slack/Google collab, anti-slop | standard |
| [`research-operator/`](./research-operator/) | Deep technical research, BenchLM, AI vendor tracking, community intelligence, web crawl | high |
| [`security-tooling-operator/`](./security-tooling-operator/) | Defensive assessments, threat modeling, AD/Windows audit, network discovery, packet review | standard |

### Coordinator & true specialists

| Specialist | Role | Tier |
| --- | --- | --- |
| [`router/`](./router/) | Parent coordinator: classify, isolate, spawn | standard |
| [`as-code-agent/`](./as-code-agent/) | Dedicated Terraform/OpenTofu/IaC authoring & plan validation | high |
| [`detailed-activity/`](./detailed-activity/) | Dedicated adversarial / antagonistic review and challenge audits | high |
| [`benchmark-agent/`](./benchmark-agent/) | Empirical benchmarking: cost estimation, fleet dry runs, retrieval, tool efficiency | standard |
| [`github-ops/`](./github-ops/) | GitHub PR workflow, branch discipline, issue management | standard |
| [`git-fast-operator/`](./git-fast-operator/) | Simple git fetch/status/log/diff/sync | fast |

### Legacy & component specialists (Consolidated into Operators)

| Agent | Consolidated into | Tier |
| --- | --- | --- |
| [`documentation-ops/`](./documentation-ops/) | `document-operator` | standard |
| [`router-maintenance/`](./router-maintenance/) | `harness-operator` | standard |
| [`qmd-ops/`](./qmd-ops/) | `harness-operator` | standard |
| [`ai-tooling-ops/`](./ai-tooling-ops/) | `harness-operator` | standard |
| [`memory-operator/`](./memory-operator/) | `harness-operator` | standard |
| [`script-ops/`](./script-ops/) | `harness-operator` | standard |
| [`artifact-agent/`](./artifact-agent/) | `document-operator` | standard |
| [`reference-ops/`](./reference-ops/) | `document-operator` | standard |
| [`repo-sync-ops/`](./repo-sync-ops/) | `harness-operator` | standard |

A2A specifications & schemas: canonical in `AGENT.md` (Schema V2); see also [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md).
