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
gh pr merge <number> --merge --admin
gh pr checks
gh pr status
gh api user
```

### CLI quirks & GraphQL deprecations

- **`gh pr view` GraphQL deprecation**: In repositories configured with legacy project cards, running `gh pr view <id>` may fail or output GraphQL deprecation errors regarding `repository.pullRequest.projectCards`. Use `gh pr status` or `git log origin/main..main` or `gh api repos/:owner/:repo/pulls/<id>` to inspect PR status reliably.


## IaC / Actions

Prefer OIDC to cloud providers over static keys in Actions.

- Keep workflow changes reviewable; treat `pull_request_target` + checkout of untrusted code as high risk.

## Cross-repository changes

This repository does not provide a shared publisher or sanitizer for other repositories. Make cross-repository changes in the destination checkout, follow its local contribution and security instructions, and use its feature-branch and pull-request workflow. Do not treat this page as an export or redaction procedure.

## Per-repo facts

Store clone paths, remotes, and deploy wiring in the relevant `projects/<slug>/` spec — this page stays pattern-level.
