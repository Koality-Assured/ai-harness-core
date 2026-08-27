---
schema_version: "2.0.0"
name: sync-downstream-repos
description: >-
  Synchronize sanitized downstream repositories and export directories with
  automatic credential redaction and audit logging. Use when exporting skills,
  standards, research, or the generic wiki/harness template (ai-harness-core)
  to public downstream repos or validating export safety.
  Do not use for internal branch merges.
owner_agent: repo-sync-ops
rank: high
isolation: mutate
dependencies:
  required_skills:
    - isolate-work
  delegated_skills: []
  in_session_skills: []
on_failure: abort_and_rollback
contracts:
  inputs:
    - Source directory, destination directory, target repo, dry-run and validate flags
  outputs:
    - Sync report, redaction audit log, and synced-file count
---

# Sync downstream repos

## When to use

Exporting or synchronizing changes from the internal `ai-router` repository to public downstream repositories (`agent-skills-and-tools`, `agent-standards`, `security-standards`, `industry-references`, `ai-research-and-benchmarks`, `ai-harness-core`). Use when publishing new skills, updated security standards, industry references, benchmark research, or the generic (non-domain-fed) wiki/harness template, or when running redaction safety audits.

## When not to use

Internal git branch merging, worktree isolation management (use `isolate-work`), or direct GitHub PR operations on this internal repository (use `github-workflow`).

## Criticality

High: Public repositories must never receive private credentials, internal file paths, internal employee identities, or unredacted API tokens. Every export must execute sanitization and emit an audit log. On unexpected failure, follow `on_failure: abort_and_rollback`.

## Source of truth

- [`scripts/sync/sync_public_repos.py`](../../../../scripts/sync/sync_public_repos.py)
- [`docs/agent-session-security.md`](../../../../docs/agent-session-security.md)
- [`ai-tooling/skills/skill-conventions.md`](../../skill-conventions.md)
- [`ai-tooling/skills/isolate-work/SKILL.md`](../isolate-work/SKILL.md)

## Isolation

`mutate`. Parent router isolates the session with `isolate-work` before spawning `repo-sync-ops`. Downstream synchronizations write to the designated destination directory; use `--dry-run` to simulate changes before writing live files.

## How to use

1. Discover required targets and verify paths via `qmd search` or CLI arguments:
   - `ai-tooling/skills/` -> `agent-skills-and-tools/skills/`
   - `docs/standards/` -> `agent-standards/standards/`
   - `docs/standards/` -> `security-standards/standards/`
   - `references/` -> `industry-references/references/`
   - `research/` -> `ai-research-and-benchmarks/research/`
   - **`ai-harness-core` is a generic (non-domain-fed) wiki/harness template**, not a `.harness/` → `harness/` engine extract. Script-ops encodes the mapping in `scripts/sync/sync_public_repos.py`. Contract:
     - Destination is a full generic wiki tree (same top-level areas as this router). Public export MUST still run redaction/audit. Never copy secrets, home paths, or tokens.
     - KEEP machinery: `AGENTS.md`; `routing/`; generic `ai-tooling/` (filtered); generic `scripts/` (`routing`, `qmd`, `cost-layers`, `change-history`, `_lib`, plus `sync`/`repos` as needed); generic `supporting/` (`qmd`, `ast-grep`, `headroom`, `github`, `powershell` if generic); portable `docs/` (`agent-session-security.md`, `anti-slop.md`, `docs/AGENTS.md`, harness-architecture standards only); `.harness/` kept as `.harness/` (engine is part of the template, not the whole product); generic `config/`; lint/ast-grep config; empty scaffolds for `actionable/`, `scratch/`, `results/`, `projects/`, `research/`, `change-history`.
     - DROP domain feed: `references/` families nist-ai-rmf, nist-csf, owasp, cwe, mitre-attack, mitre-atlas, stride (keep conventional-commits and markdown tooling); most `docs/standards` security-ops pages; cloud/security skills (`aws-*`, `azure-*`, `gcp-*`, framework-mapper, threat-model, noir if present); instance `projects/`/`research/` content; user memory checkpoints; scratch worktrees; results dumps; `.git`.
     - Stub dropped areas with area `AGENTS.md` (or empty tree + AGENTS) stating this is a generic template: feed domain content later; do not ship this instance’s security corpus.
2. Run `--validate` as a **source-cleanliness linter**. It flags patterns still present in source (including documented internal paths) and **exits 1** when any hit exists. That nonzero status is expected on this repo when skills document `scratch/worktrees/`; it is **not** a public leak. Do not abort the export solely because `--validate` is dirty:
   `python scripts/sync/sync_public_repos.py --validate --json`
3. Execute dry-run simulation to review planned file changes and redactions (this is the **export leak gate**; a redaction here is the control):
   `python scripts/sync/sync_public_repos.py --dest <export_dir> --dry-run --json`
4. Inspect the generated redaction audit log in the output. If unexpected patterns or errors arise, halt and remediate.
5. Perform live export synchronization:
   `python scripts/sync/sync_public_repos.py --dest <export_dir>`
   Or sync a specific repository:
   `python scripts/sync/sync_public_repos.py --dest <export_dir> --repo agent-skills-and-tools`
6. Verify destination repository integrity and return structured summary to parent.

## Dry run

```bash
python scripts/sync/sync_public_repos.py --dry-run
python scripts/sync/sync_public_repos.py --validate
python scripts/sync/sync_public_repos.py --repo agent-skills-and-tools --dry-run --json
```

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Follow [`docs/agent-session-security.md`](../../../../docs/agent-session-security.md). All public exports MUST be processed through the sanitization engine in `sync_public_repos.py`. Never bypass redaction filters, never commit live credentials or tokens into downstream export destinations, and ensure all redaction events are audited.

## Completion gates

Verify sync summary (files scanned, synced, modified, unchanged) and confirm `total_errors == 0`. Emit redaction audit log for review. Log change-history entry if public exports were updated.
