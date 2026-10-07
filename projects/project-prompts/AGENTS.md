# Project Prompts AGENTS

Entry-point prompt library for human-initiated follow-up tasks on proposals, untested generic capabilities, or live integration runs.

Follow this repository's root `AGENTS.md` and local routing guidance when present; otherwise, follow its existing contribution and host-agent instructions. This guidance is self-contained and does not depend on files outside this repository.

## Strict Operational Rules

1. **Non-Authoritative:** This folder is NOT an authoritative source of truth for repository rules, architecture, or documentation. It contains only situational prompt templates.
2. **Lean & Discoverability:** Prompts stored here MUST be lean. Do NOT duplicate repository rules, folder structures, or instructions that an agent can discover from this repository's `AGENTS.md`, routing catalogs, or docs when present.
3. **Human-Initiated Only:** Agents MUST NEVER autonomously use or execute prompts in this directory as part of routine duties or subagent delegation. Prompts are used exclusively by human operators when directly launching a follow-up task.
4. **Follow-Up Scope:** Used for live testing of newly created generic tooling, OAuth/credential prompting, interactive human-in-the-loop executions, or continuing incomplete initiative phases.
5. **Archival Lifecycle MUST:** After a prompt completes successfully, remove it from the active library. Retain completed prompts only if this repository defines an archive; follow its local archive instructions. Otherwise, discard the active prompt. Do not assume an archive folder exists.

## Material Prompt Authoring

- When this repository provides prompt-engineering references or search tools, consult relevant material before material prompt authoring or review. Treat those references as advisory, not repository policy. If none are available, use the task context and current authoritative vendor documentation below.
- Verify time-sensitive or provider/model-specific claims against current authoritative vendor documentation. For OpenAI prompting claims, use the current [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering) and [Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) guides; do not generalize guidance beyond its documented model or provider scope.
- Make runnable prompts state the intended outcome, relevant authoritative context and source links, actionable scope and order, constraints and owner gates, named deliverables, and observable completion and reporting criteria.
- Keep prompts focused and proportionate: adapt headings to the task, verify links, remove stale or unsupplied placeholders, and do not mandate XML or inflate prompts with repetitive checklists.

