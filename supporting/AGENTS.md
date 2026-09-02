# Supporting AGENTS

Durable tool patterns, locations, and machine setup notes — not full vendor manuals.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). README is human-only (root [`../AGENTS.md`](../AGENTS.md) High README rule).

## Rules

- One tool family per folder (`aws/`, `cloudflare/`, `github/`, `qmd/`, `headroom/`, `ast-grep/`, `terraform/`, …).
- **One-way dependency invariant:** `supporting/` holds durable platform and tool facts. Its relationship is strictly one-way (`project -> supporting`). Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
- Record confirmed commands, project names, gotchas, and where things live.
- **Reproducible Success Storage:** Store verified methodologies, successful tool recipes, and confirmed operational patterns under the relevant tool family folder so high-value methodologies are reliably reproducible across sessions.
- Prefer linking upstream docs over large excerpts.
- Promote from `scratch/` / chat only after verified.
- Nested AGENTS only when a tool subtree becomes complex.
- Workstation setup: [`workstation-onboarding.md`](./workstation-onboarding.md). Retrieval writing: [`qmd/retrieval-conventions.md`](./qmd/retrieval-conventions.md).
- Agent recipes (not README): `aws/account-details.md`, `qmd/query-pattern.md`, `ast-grep/precision-retrieval.md`, `headroom/proxy-mcp.md`, `terraform/cli-workflow.md`, tool-specific tagged pages.
- Default specialists: `cloud-operator` (aws), `qmd-ops`, `github-ops`, `router-maintenance` (headroom/ast-grep), `as-code-agent` (terraform) — spawn matching skill owners when that work is material. Parent runs isolate CLI.
