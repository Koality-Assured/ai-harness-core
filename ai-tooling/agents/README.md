# Standalone agents

Human overview: specialist definitions live in `<id>/AGENT.md`. Optional host stubs under `.cursor/agents/` only point here.

**Agents do not use this README as a catalog.** Catalogs are `AGENT.md` (Schema V2) + [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) / [`../../routing/area-map.md`](../../routing/area-map.md). Tiers: [`model-tiers.md`](./model-tiers.md).

Human index (not agent SoT):

| Agent | Role | Tier |
| --- | --- | --- |
| [`router/`](./router/) | Parent: classify, isolate, spawn | standard |
| [`documentation-ops/`](./documentation-ops/) | docs + harness structure | standard |
| [`github-ops/`](./github-ops/) | gh / PRs / branch discipline | standard |
| [`router-maintenance/`](./router-maintenance/) | worktrees, routing maps, scratch, Headroom, ast-grep | standard |
| [`qmd-ops/`](./qmd-ops/) | qmd search + efficiency dry runs | standard |
| [`ai-tooling-ops/`](./ai-tooling-ops/) | skills, user/agent memory, agent defs | standard |
| [`memory-operator/`](./memory-operator/) | evidence-backed model-family capability memory | standard |
| [`script-ops/`](./script-ops/) | tagged Python under scripts/ | standard |
| [`detailed-activity/`](./detailed-activity/) | antagonistic review + deep research | high |
| [`artifact-agent/`](./artifact-agent/) | diagrams + modular documents; default `results/` | standard |
| [`as-code-agent/`](./as-code-agent/) | Terraform/Pulumi/Ansible/Kyverno/Rego drafts | high |
| [`git-fast-operator/`](./git-fast-operator/) | simple git fetch/status/log/diff/sync | fast |
| [`reference-ops/`](./reference-ops/) | `references/` captures and normalization | standard |
| [`repo-sync-ops/`](./repo-sync-ops/) | downstream repo sync + public export redaction | standard |
| [`benchmark-agent/`](./benchmark-agent/) | Empirical benchmarking: cost estimation, fleet dry runs, retrieval, tool efficiency, task eval | standard |

A2A specifications & schemas: canonical in `AGENT.md` (Schema V2); see also [`../a2a/agent-cards/README.md`](../a2a/agent-cards/README.md).
