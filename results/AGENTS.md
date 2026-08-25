# Results AGENTS

Home for finished deliverable artifacts a human might hand to someone else: reports, HTML, images, diagrams, threat-model packages, as-code packages, dated cost-layer measurement reports, and finished research dossiers. Layout: [`results-conventions.md`](./results-conventions.md).

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Spawn `artifact-agent` (or a more specific skill owner) when producing artifacts is material catalogued work. In-session anti-slop/humanizer on a specialist’s own draft MUST NOT mint `artifact-agent` after return.

## Rules

- Use `results/<family>/<topic-or-slug>/<YYYY-MM-DD>/` (typed families add a segment before topic). Do not invent new top-level run shapes (`results/headroom-dry-run`, `results/ast-grep-dry-run`, `results/scaffolded-repos`). Cost-layer output goes under `results/cost-layers/<slug>/<YYYY-MM-DD>/`.
- Finished deliverables only. Scaffolds, generator previews, review working notes, and other interim output belong in `scratch/` (or back to the orchestrator).
- Antagonistic reviews are not a durable family. Return ranked findings to the orchestrator. Promote unique durable knowledge to the owning source area only when it is not already there. Do not keep completed reviews in git and do not file them under `results/reviews/`.
- Prefer Markdown in-git; binaries may be gitignored.
- Not policy SoT — promote reusable lessons to `docs/` / `supporting/` / `routing/`.
- Open one run folder only; do not bulk-load this tree.
