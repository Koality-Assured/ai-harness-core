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
| [`security-tooling-operator/`](./security-tooling-operator/) | Defensive assessments, threat modeling, AD/Windows audit, attack-surface discovery | standard |

### Coordinator & true specialists

| Specialist | Role | Tier |
| --- | --- | --- |
| [`router/`](./router/) | Parent coordinator: classify, isolate, spawn | standard |
| [`artifact-agent/`](./artifact-agent/) | Diagrams, media captures, code review reports, framework mapping | standard |
| [`as-code-agent/`](./as-code-agent/) | Dedicated Terraform/OpenTofu/IaC authoring & plan validation | high |
| [`benchmark-agent/`](./benchmark-agent/) | Empirical benchmarking: cost estimation, fleet dry runs, retrieval, tool efficiency | standard |
| [`bifrost-operator/`](./bifrost-operator/) | Maxim Bifrost AI gateway lifecycle, routing, virtual keys, and inference layer orchestration | standard |
| [`detailed-activity/`](./detailed-activity/) | Dedicated adversarial / antagonistic review and challenge audits | high |
| [`git-fast-operator/`](./git-fast-operator/) | Simple git fetch/status/log/diff/sync | fast |
| [`github-ops/`](./github-ops/) | GitHub PR workflow, branch discipline, issue management | standard |
| [`public-publication/`](./public-publication/) | Evidence-backed white-paper and blog candidate discovery and publication | standard |

### Retired micro-agents (Consolidated into Operators)

The following 16 micro-agents were consolidated into the 5 primary operators:
- `documentation-ops`, `docs-collab-agent`, `google-suite-admin`, `google-suite-operator`, `chat-collab-agent`, `reference-ops` -> consolidated into [`document-operator/`](./document-operator/)
- `router-maintenance`, `qmd-ops`, `ai-tooling-ops`, `memory-operator`, `script-ops`, `repo-sync-ops` -> consolidated into [`harness-operator/`](./harness-operator/)
- `community-analyst` -> consolidated into [`research-operator/`](./research-operator/)
- `cloud-admin-agent`, `public-llm-admin` -> consolidated into [`cloud-operator/`](./cloud-operator/)
- `assessment-agent` -> consolidated into [`security-tooling-operator/`](./security-tooling-operator/)

A2A specifications & schemas: canonical in `AGENT.md` (Schema V2); see also [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md).
