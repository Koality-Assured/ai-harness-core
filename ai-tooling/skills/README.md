# Skills

Human overview: router skills live organized into domain families under `<family>/<name>/SKILL.md`.

**Agents do not use this README as a catalog.** They load [`../../routing/skill-dispatch.md`](../../routing/skill-dispatch.md) (regenerate with `python scripts/routing/generate_skill_dispatch.py`) and spawn `owner_agent`. Template: [`../../ai-tooling/skills/skill-conventions.md`](skill-conventions.md). Validate: `python scripts/ai-tooling/validate_skill.py --all`.

Human index (not agent SoT):

| Skill | Owner | Isolation |
| --- | --- | --- |
| [`google-drive-manage/`](./google/google-drive-manage/) | google-suite-operator | mutate |
| [`google-gmail-manage/`](./google/google-gmail-manage/) | google-suite-operator | mutate |
| [`google-workspace-metadata/`](./google/google-workspace-metadata/) | google-suite-operator | read-only |
| [`google-workspace-admin/`](./google/google-workspace-admin/) | google-suite-admin | mutate |
| [`agent-builder/`](./meta/agent-builder/) | ai-tooling-ops | mutate |
| [`ai-vendor-updates/`](./meta/ai-vendor-updates/) | detailed-activity | mutate |
| [`antagonistic-review/`](./meta/antagonistic-review/) | detailed-activity | read-only |
| [`anti-slop/`](./reporting/anti-slop/) | artifact-agent | mutate |
| [`architecture-diagram/`](./reporting/architecture-diagram/) | artifact-agent | mutate |
| [`as-code-builder/`](./reporting/as-code-builder/) | as-code-agent | mutate |
| [`ast-grep/`](./cost-layers/ast-grep/) | router-maintenance | read-only |
| [`aws-logs/`](./aws/aws-logs/) | cloud-operator | mutate |
| [`aws-read/`](./aws/aws-read/) | cloud-operator | mutate |
| [`aws-write/`](./aws/aws-write/) | cloud-operator | mutate |
| [`azure-logs/`](./azure/azure-logs/) | cloud-operator | mutate |
| [`azure-read/`](./azure/azure-read/) | cloud-operator | mutate |
| [`azure-write/`](./azure/azure-write/) | cloud-operator | mutate |
| [`cloud-admin-provision/`](./admin/cloud-admin-provision/) | cloud-admin-agent | mutate |
| [`code-review-report/`](./reporting/code-review-report/) | artifact-agent | mutate |
| [`corpus-draft/`](./reporting/corpus-draft/) | artifact-agent | mutate |
| [`cost-layer-dry-run/`](./cost-layers/cost-layer-dry-run/) | router-maintenance | mutate |
| [`deep-research/`](./meta/deep-research/) | detailed-activity | mutate |
| [`doc-builder/`](./meta/doc-builder/) | documentation-ops | mutate |
| [`downstream-repo-update/`](./meta/downstream-repo-update/) | repo-sync-ops | mutate |
| [`executive-report/`](./reporting/executive-report/) | artifact-agent | mutate |
| [`foundation-site/`](./reporting/foundation-site/) | artifact-agent | mutate |
| [`framework-mapper/`](./reporting/framework-mapper/) | artifact-agent | mutate |
| [`gcp-logs/`](./gcp/gcp-logs/) | cloud-operator | mutate |
| [`gcp-read/`](./gcp/gcp-read/) | cloud-operator | mutate |
| [`gcp-write/`](./gcp/gcp-write/) | cloud-operator | mutate |
| [`git-basics/`](./git/git-basics/) | git-fast-operator | mutate |
| [`github-paths/`](./git/github-paths/) | github-ops | read-only |
| [`github-workflow/`](./git/github-workflow/) | github-ops | mutate |
| [`guidance-draft/`](./reporting/guidance-draft/) | artifact-agent | mutate |
| [`headroom/`](./cost-layers/headroom/) | router-maintenance | read-only |
| [`harness-review/`](./harness-review/) | ai-tooling-ops | mutate |
| [`humanizer/`](./reporting/humanizer/) | artifact-agent | mutate |
| [`isolate-work/`](./meta/isolate-work/) | router | mutate |
| [`markdownlint/`](./meta/markdownlint/) | documentation-ops | mutate |
| [`memory-adjust/`](./memory/memory-adjust/) | ai-tooling-ops | mutate |
| [`memory-cleanup/`](./memory/memory-cleanup/) | ai-tooling-ops | mutate |
| [`memory-create/`](./memory/memory-create/) | ai-tooling-ops | mutate |
| [`mermaid-diagram/`](./reporting/mermaid-diagram/) | artifact-agent | mutate |
| [`model-memory-operate/`](./model-memory-operate/) | memory-operator | mutate |
| [`noir-scan/`](./reporting/noir-scan/) | artifact-agent | mutate |
| [`proposal-report/`](./reporting/proposal-report/) | artifact-agent | mutate |
| [`public-llm-admin/`](./admin/public-llm-admin/) | public-llm-admin | mutate |
| [`qmd-efficiency/`](./meta/qmd-efficiency/) | qmd-ops | mutate |
| [`qmd-usage/`](./meta/qmd-usage/) | qmd-ops | read-only |
| [`reference-maintain/`](./meta/reference-maintain/) | reference-ops | mutate |
| [`scratch-cleanup/`](./meta/scratch-cleanup/) | router-maintenance | mutate |
| [`script-builder/`](./meta/script-builder/) | script-ops | mutate |
| [`skill-builder/`](./meta/skill-builder/) | ai-tooling-ops | mutate |
| [`skill-dry-run/`](./meta/skill-dry-run/) | ai-tooling-ops | read-only |
| [`source-validation/`](./meta/source-validation/) | reference-ops | mutate |
| [`benchlm-lookup/`](./meta/benchlm-lookup/) | detailed-activity | read-only |
| [`social-sentiment-analysis/`](./community/social-sentiment-analysis/) | community-analyst | mutate |
| [`community-troubleshooting/`](./community/community-troubleshooting/) | community-analyst | mutate |
| [`niche-discovery/`](./community/niche-discovery/) | community-analyst | mutate |
| [`social-osint/`](./community/social-osint/) | community-analyst | mutate |
| [`product-opportunity-scout/`](./community/product-opportunity-scout/) | community-analyst | mutate |
| [`community-pattern-analysis/`](./community/community-pattern-analysis/) | community-analyst | mutate |
| [`breaking-tech-news/`](./community/breaking-tech-news/) | community-analyst | mutate |
| [`community-registry-maintain/`](./community/community-registry-maintain/) | community-analyst | mutate |
| [`sync-downstream-repos/`](./meta/sync-downstream-repos/) | repo-sync-ops | mutate |
| [`tabler-dashboard/`](./reporting/tabler-dashboard/) | artifact-agent | mutate |
| [`threat-model/`](./reporting/threat-model/) | assessment-agent | mutate |
| [`wiki-structure/`](./meta/wiki-structure/) | documentation-ops | read-only |
