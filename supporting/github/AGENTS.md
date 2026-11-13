# GitHub AGENTS

Durable operational notes, GitHub CLI (`gh`) execution patterns, pull request workflows, branch protection discipline, and canonical artifact URL resolution.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational recipes, GitHub CLI (`gh`) interaction patterns, branch discipline conventions, and canonical GitHub `blob/main` and `tree/main` path resolution for human-facing artifacts across the repository ecosystem.

## Local Constraints

1. **Token & Secret Hygiene:** Personal Access Tokens (PATs), GitHub Apps private keys, OAuth tokens, and webhook secrets MUST NEVER be hardcoded or committed to git. Authenticate locally via `gh auth login` or read from standard environment variables (`GITHUB_TOKEN`, `GH_TOKEN`).
2. **Strict Output Fire-Wall:** `supporting/` is strictly an input resource and accelerator store. Agents and scripts MUST NEVER deposit PR review dumps, raw API JSON responses, issue export lists, or workflow run logs into `supporting/github/`. All generated reports and reviews route to `results/github/<topic>/<YYYY-MM-DD>/` per [`../../results/results-conventions.md`](../../results/results-conventions.md).
3. **One-Way Dependency Invariant:** Supporting files hold durable platform facts and MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
4. **Branch Protection & Commit Discipline:** Never push directly to protected default branches (`main` or `master`). Work must proceed via feature branches and pull requests (`gh pr create`). All commit messages and PR titles MUST follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`) per [`../../references/conventional-commits/conventional-commits.md`](../../references/conventional-commits/conventional-commits.md). Force-pushing to default branches is strictly prohibited.
5. **Canonical Main URL Link Invariant:** External and human-facing artifact links (e.g. in `results/` reports, executive dashboards, threat models) MUST use canonical POSIX GitHub URLs on `main` (`https://github.com/Koality-Assured/ai-router/blob/main/<path>`). Never link to feature-branch refs, worktree-absolute paths, or OS-local paths (`C:\...`). Internal docs retain relative Markdown links.
6. **CLI Preference & Quirk Safety:** Prefer `gh` CLI over raw `curl` or GraphQL API calls when authenticated. Work around known CLI quirks (such as `gh pr view` GraphQL deprecation errors on legacy project cards) by falling back to `gh pr status` or `gh api repos/:owner/:repo/pulls/<id>`.

## Next Hops

- Workflow notes & CLI commands: [`gh-workflow-notes.md`](./gh-workflow-notes.md)
- Canonical GitHub path resolution for artifacts: [`github-paths.md`](./github-paths.md)
- Default specialist (git and GitHub ops): [`../../ai-tooling/agents/github-ops/AGENT.md`](../../ai-tooling/agents/github-ops/AGENT.md)
- Fast git operations: [`../../ai-tooling/agents/git-fast-operator/AGENT.md`](../../ai-tooling/agents/git-fast-operator/AGENT.md)
- Multi-repo downstream synchronization: [`../../ai-tooling/agents/harness-operator/AGENT.md`](../../ai-tooling/agents/harness-operator/AGENT.md)
- IaC & Actions security standard: [`../../docs/standards/github-iac-security.md`](../../docs/standards/github-iac-security.md)
