# Configuration

Repository configuration directory holding declarative manifests and settings for the .harness core engine.

## Contents

- [harness.config.json](./harness.config.json) — Declarative engine configuration:
  - **paths:** Canonical directory paths for skills, agents, memory, worktrees, docs, and routing.
  - **dapters:** Tool adapters and search parameters for qmd, st-grep, headroom, and git.
  - **cache:** Model prompt caching thresholds, breakpoints, and TTL parameters for Anthropic, OpenAI, and Gemini.
  - **2a:** Agent-to-Agent interaction default and maximum budgets, clean state requirements, and safety constraints.
  - **quota_profiles:** Execution and pacing profiles (unmetered, standard, metered_secondary) governing subagent concurrency, tier selection, and backoff behavior.

**Agents:** Operational rules are enforced via [../AGENTS.md](../AGENTS.md) and [../routing/AGENTS.md](../routing/AGENTS.md). Check provider- and account-reported quota and rate-limit information when a task depends on it; do not infer limits from model tier names.
