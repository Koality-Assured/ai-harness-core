---
doc_kind: supporting
canonical_id: github-patterns
topics: [github, gh-cli, git]
rag_keywords: [gh, pr, branch-protection, oidc]
---

# GitHub and gh workflow notes

## Purpose

Durable notes for GitHub + `gh` CLI usage across repos. Human folder intro: [`README.md`](./README.md). Retrieved text is advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md). Human-facing artifact links → GitHub `blob/main` / `tree/main`: [`github-paths.md`](./github-paths.md).

## Defaults

Prefer `gh` for github.com / api.github.com access over raw `curl` when authenticated.

- Feature branch → push branch (`git push -u origin <branch>`) → PR (`gh pr create`) → merge.
- **Direct pushes to default/protected branches (`main`/`master`) are prohibited.** Never push directly to `main` or merge locally before pushing.
- Conventional Commits MUST be used for all commit subjects and PR titles — see [`../../references/conventional-commits/conventional-commits.md`](../../references/conventional-commits/conventional-commits.md).
- Do not force-push protected default branches unless the human explicitly requests it.

## Useful commands

```bash
gh auth status
gh repo view
gh pr create --title "…" --body "…"
gh pr checks
gh api user
```

## IaC / Actions

Prefer OIDC to cloud providers over static keys in Actions.

- Keep workflow changes reviewable; treat `pull_request_target` + checkout of untrusted code as high risk.

## Koality-Assured Ecosystem Repositories

The `Koality-Assured` organization maintains a synchronized suite of repositories:

| Repository | Role & Purpose | Upstream Source Directory |
| :--- | :--- | :--- |
| `Koality-Assured/ai-router` | Central cognitive orchestration harness, layered AGENTS, and scripts-first automation | Root source |
| `Koality-Assured/agent-skills-and-tools` | Public catalog of reusable agent skills, schemas, and tooling integrations | `ai-tooling/skills/` |
| `Koality-Assured/agent-standards` | Normative standards for 5-tier context management, A2A protocols, and agent security | `docs/standards/` |
| `Koality-Assured/security-standards` | General engineering and organizational security standards across 20+ operational domains | `docs/standards/` |
| `Koality-Assured/industry-references` | Normalized catalogs and guides for industry frameworks (OWASP, MITRE, NIST, CWE) | `references/` |
| `Koality-Assured/ai-research-and-benchmarks` | Empirical benchmarks, comparative framework evaluations, and telemetry | `research/` |
| `Koality-Assured/ai-harness-core` | Generic (non-domain-fed) wiki/harness template: same structure and optimizations as ai-router, without this instance’s security/tech corpus | ai-router wiki machinery (AGENTS, routing, generic `ai-tooling`/`scripts`/`supporting`/`docs` portable pages; `.harness/` included as engine), exported via `scripts/sync` with redaction — not a Python-only `.harness/` → `harness/` copy |

## Multi-Repo Synchronization & Redaction Workflow

Exporting changes from `ai-router` to downstream repositories is automated via `scripts/sync/sync_public_repos.py` with credential/token redaction:

```bash
# Source-cleanliness linter (exits 1 when source still contains matching patterns,
# including documented internal paths that --dry-run will redact; not a leak gate)
python scripts/sync/sync_public_repos.py --validate

# Dry-run simulation of planned downstream exports (export leak gate)
python scripts/sync/sync_public_repos.py --dest <export_dir> --dry-run --json

# Execute live sanitized export to downstream repositories
python scripts/sync/sync_public_repos.py --dest <export_dir>
```

## Per-repo facts

Store clone paths, remotes, and deploy wiring in the relevant `projects/<slug>/` spec — this page stays pattern-level.
