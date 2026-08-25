# Standalone agents

Human overview: specialist definitions live in `<id>/AGENT.md`. Optional host stubs under `.cursor/agents/` only point here.

**Agents do not use this README as a catalog.** Catalogs are `AGENT.md` (Schema V2) + [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) / [`../../routing/area-map.md`](../../routing/area-map.md). Tiers: [`model-tiers.md`](./model-tiers.md).

Human index (not agent SoT):

| Agent | Role | Tier |
| --- | --- | --- |
| [`router/`](./router/) | Parent: classify, isolate, spawn | standard |
| [`documentation-ops/`](./documentation-ops/) | docs + wiki structure | standard |
| [`github-ops/`](./github-ops/) | gh / PRs / branch discipline | standard |
| [`router-maintenance/`](./router-maintenance/) | worktrees, routing maps, scratch, Headroom, ast-grep | standard |
| [`qmd-ops/`](./qmd-ops/) | qmd search + efficiency dry runs | standard |
| [`ai-tooling-ops/`](./ai-tooling-ops/) | skills, user/agent memory, agent defs | standard |
| [`memory-operator/`](./memory-operator/) | evidence-backed model-family capability memory | standard |
| [`script-ops/`](./script-ops/) | tagged Python under scripts/ | standard |
| [`detailed-activity/`](./detailed-activity/) | antagonistic review + deep research | high |
| [`artifact-agent/`](./artifact-agent/) | diagrams + modular documents; default `results/` | standard |
| [`assessment-agent/`](./assessment-agent/) | STRIDE threat models | standard |
| [`as-code-agent/`](./as-code-agent/) | Terraform/Pulumi/Ansible/Kyverno/Rego drafts | high |
| [`cloud-operator/`](./cloud-operator/) | AWS/GCP/Azure read, authorized write, logs | standard |
| [`cloud-admin-agent/`](./cloud-admin-agent/) | Multi-cloud organization admin & landing zone provisioning | standard |
| [`public-llm-admin/`](./public-llm-admin/) | Public LLM workspace admin, ZDR audit & API key governance | standard |
| [`google-suite-operator/`](./google-suite-operator/) | Google Workspace resources: Drive, Gmail, Docs, Metadata | standard |
| [`google-suite-admin/`](./google-suite-admin/) | Google Workspace domain admin, OU hierarchy, DLP, ZDR audit | standard |
| [`git-fast-operator/`](./git-fast-operator/) | simple git fetch/status/log/diff/sync | fast |
| [`reference-ops/`](./reference-ops/) | `references/` captures and normalization | standard |
| [`repo-sync-ops/`](./repo-sync-ops/) | downstream repo sync + public export redaction | standard |
| [`community-analyst/`](./community-analyst/) | public communities, subreddits, developer forums & OSINT | standard |

A2A specifications & schemas: canonical in `AGENT.md` (Schema V2); see also [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md).
