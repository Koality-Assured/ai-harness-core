# Google Antigravity & Gemini Agent Guidelines

## Context Loading and Subagent Protocol

1. **Root Directives**: Adhere to the normative hierarchy defined in [`AGENTS.md`](./AGENTS.md) and [`routing/AGENTS.md`](./routing/AGENTS.md).
2. **Subagent Spawning (`invoke_subagent`)**:
   - Subagents execute in isolated context windows with clean state.
   - Supply only the explicit `Prompt`, `Role`, `TypeName`, `Model` tier, and `Workspace` mode.
   - Do NOT pass parent conversation transcripts or prior turn logs into child prompts.
3. **Progressive Disclosure**: Only skill names and descriptions are visible initially. Full skill bodies (`SKILL.md`) and target folder rules are loaded strictly Just-In-Time (JIT) when needed.
4. **Cost Layers**: Leverage `qmd search`/`qmd get` for Markdown discovery, `ast-grep` for AST symbol exploration, and Headroom for bulky outputs.
5. **Durable Write-Back**: Record lessons and recovery strategies in `ai-tooling/memory/` and update owning source areas upon completion.
