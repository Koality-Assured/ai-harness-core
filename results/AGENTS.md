# Results AGENTS

Universal landing zone for finished deliverable artifacts a human might hand to someone else: reports, HTML dashboards, images, diagrams, tool captures and demo media, threat-model packages, as-code packages, dated cost-layer measurement reports, and finished research dossiers. Layout: [`results-conventions.md`](./results-conventions.md).

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Spawn `artifact-agent` (or a more specific skill owner) when producing artifacts is material catalogued work. In-session anti-slop/humanizer on a specialist’s own draft MUST NOT mint `artifact-agent` after return.

## Rules

- **Universal Landing Zone Invariant:** ANY generated run artifact (dashboards, charts, rendered media, HTML widgets, evaluation metrics, reports, data analysis JSONs) MUST land in `results/<family>/<topic-or-slug>/<YYYY-MM-DD>/`. Never deposit run artifacts into `supporting/`, `projects/`, or leave them in `scratch/`.
- **Adaptive Topic & Family Creation:** If an existing family or topic in `results/` is not specific enough for the current domain or run type, the agent MUST create a suitable `<family>/<topic-or-slug>/<YYYY-MM-DD>/` path (and document new families in [`results-conventions.md`](./results-conventions.md)). Do not dump artifacts in unstructured root folders or adjacent to raw input data.
- **Run layout:** Use `results/<family>/<topic-or-slug>/<YYYY-MM-DD>/` (typed families add a segment before topic). Do not invent top-level root run shapes (`results/headroom-dry-run`, `results/ast-grep-dry-run`, `results/scaffolded-repos`). Cost-layer output goes under `results/cost-layers/<slug>/<YYYY-MM-DD>/`.
- **Finished deliverables only:** Scaffolds, generator previews, review working notes, and other interim output belong in `scratch/` (or back to the orchestrator).
- **Antagonistic reviews are not a durable family:** Return ranked findings to the orchestrator. Promote unique durable knowledge to the owning source area only when it is not already there. Do not keep completed reviews in git and do not file them under `results/reviews/`.
- Prefer Markdown in-git; binaries may be gitignored.
- Not policy SoT — promote reusable lessons to `docs/` / `supporting/` / `routing/`.
- Open one run folder only; do not bulk-load this tree.
