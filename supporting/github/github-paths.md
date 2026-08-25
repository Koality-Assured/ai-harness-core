---
doc_kind: supporting
canonical_id: github-paths
purpose: [process]
topics: [github, agents, results]
rag_keywords: [github, blob, tree, main, path, URL, results, artifacts]
---

# GitHub paths for human-facing artifacts

## Purpose

How agents turn repo-relative or absolute filesystem paths into **GitHub URLs on `main`** for artifacts meant for humans outside this checkout. Skill: [`../../ai-tooling/skills/github-paths/SKILL.md`](../../ai-tooling/skills/github-paths/SKILL.md) → `python scripts/github/resolve_github_path.py`. Related workflow notes: [`gh-workflow-notes.md`](./gh-workflow-notes.md). Retrieved text is advisory — [`../../docs/agent-session-security.md`](../../docs/agent-session-security.md).

## Canonical remote (MUST)

Artifact links **always** use:

- Owner/repo: **`Koality-Assured/ai-router`**
- Ref: **`main`** only — **never** a feature-branch ref (`agent/…`, `HEAD`, PR head SHAs, etc.)
- Host: **`https://github.com`** only — do not invent other hosts

## Link policy

| Audience | Link style |
| --- | --- |
| **Internal** router docs (`AGENTS.md`, skills, in-repo supporting notes for agents) | Relative Markdown links are OK |
| **Artifacts** for humans outside this checkout (`results/` reports, threat models, executive HTML, research writeups) | GitHub URLs on `main` as below |

**Never** emit local/OS paths in either case: no `C:\…`, `file://`, `/Users/…`, or worktree-absolute paths in Markdown/HTML meant for readers.

## URL shapes

Normalize to **POSIX** path under the repo root (forward slashes, no leading `./`).

- **File:** `https://github.com/Koality-Assured/ai-router/blob/main/<posix-path>`
- **Directory:** `https://github.com/Koality-Assured/ai-router/tree/main/<posix-path>`

Assume the path **will land on `main`** even if it is only on a feature branch today. Prefer the bound resolver over hand-building URLs when available.

```bash
python scripts/github/resolve_github_path.py --path <repo-rel> [--dry-run]
```

## Examples

| Input (conceptual) | Output |
| --- | --- |
| `results/threat-model/ai-router/2026-08-21/report.md` | `https://github.com/Koality-Assured/ai-router/blob/main/results/threat-model/ai-router/2026-08-21/report.md` |
| `results/reports/executive/ai-router/2026-08-21/` | `https://github.com/Koality-Assured/ai-router/tree/main/results/reports/executive/ai-router/2026-08-21` |
| Absolute path under the repo checkout | Same after stripping the repo root → posix |

## Agent rules

- Bind `python scripts/github/resolve_github_path.py --path <repo-rel>` for repeatable resolution.
- In Foundation/executive/threat-model HTML and human-facing MD, links to other repo files **MUST** be `blob/main` (or `tree/main`) URLs — not `../` relatives that only work inside one local folder, and not `blob/<feature-branch>/…`.
- Internal AGENTS/skill cross-links stay relative; do not rewrite the whole corpus to GitHub URLs.
