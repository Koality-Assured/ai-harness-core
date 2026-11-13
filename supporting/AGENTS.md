# Supporting AGENTS

The accelerator and foundation store: durable tool patterns, evaluation rubrics, category mappings, structural examples, reference datasets, and machine setup notes that empower and simplify future work.

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). README is human-only (root [`../AGENTS.md`](../AGENTS.md) High README rule).

## Purpose & Scope

`supporting/` houses reusable foundations that accelerate future execution:
1. **Tool Patterns & Recipes:** Operational execution recipes, flags, syntax patterns, and gotchas (`ast-grep/`, `qmd/`, `headroom/`, `aws/`, `cloudflare/`, `powershell/`, `terraform/`, …).
2. **Rubrics & Evaluation Frameworks:** Scoring rubrics, assessment criteria, classification taxonomies, and interaction heuristics that ground agent evaluations.
3. **Mappings & Taxonomies:** Domain dictionaries, affective valence overlays, entity maps, and schema normalization tables.
4. **Structural Examples & Templates:** Golden reference files, scenario fixtures, boilerplate layouts, and structural blueprints.
5. **Reference Datasets & Corpora:** Static domain databases, baseline archives, raw transcripts, and benchmark ground-truth fixtures.

## Rules

- **Strict Output Fire-Wall (Input-Resource Invariant):** `supporting/` is strictly an *input resource and accelerator store*. Agents and automation scripts MUST NEVER write execution outputs, generated charts, word clouds, HTML dashboards, analysis reports, or run deliverables into `supporting/`. All generated artifacts MUST route to `results/<family>/<slug>/<date>/` per [`../results/results-conventions.md`](../results/results-conventions.md).
- **One-way dependency invariant:** `supporting/` holds durable platform and tool facts. Its relationship is strictly one-way (`project -> supporting`). Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
- **One family per folder:** Organize logically by tool, domain, or resource family (`ast-grep/`, `auth0/`, `aws/`, `cloudflare/`, `github/`, `local-llms/`, `qmd/`, `headroom/`, `terraform/`, `sentiment-analysis/`, …).
- Record confirmed commands, project names, gotchas, and where things live.
- **Reproducible Success Storage:** Store verified methodologies, successful tool recipes, and confirmed operational patterns under the relevant family folder so high-value methodologies are reliably reproducible across sessions.
- Prefer linking upstream docs or summarizing over dumping large excerpts.
- Promote from `scratch/` / chat only after verified empirically.
- Nested AGENTS only when a resource subtree becomes complex or enforces folder-local constraints.
- Workstation setup: [`workstation-onboarding.md`](./workstation-onboarding.md). Retrieval writing: [`qmd/retrieval-conventions.md`](./qmd/retrieval-conventions.md).
- Agent recipes (not README): `auth0/tenant-details.md`, `aws/account-details.md`, `local-llms/direct-interaction.md`, `qmd/query-pattern.md`, `ast-grep/precision-retrieval.md`, `headroom/proxy-mcp.md`, `terraform/cli-workflow.md`, tool-specific tagged pages.
- Default specialists: `cloud-operator` (aws), `harness-operator` (local-llms), `qmd-ops`, `github-ops`, `router-maintenance` (headroom/ast-grep), `as-code-agent` (terraform) — spawn matching skill owners when that work is material. Parent runs isolate CLI.
