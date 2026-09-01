# GitHub Copilot & GPT Agent Instructions

## Repository Standards and Context Boundaries

1. **Canonical Authority**: Always consult [`AGENTS.md`](../AGENTS.md) and [`routing/AGENTS.md`](../routing/AGENTS.md) for normative operational directives.
2. **Subagent Context Isolation**: Subagents and auxiliary agent invocations MUST operate with clean-slate context. They know only the explicit task prompt and parameters provided by the parent coordinator, plus knowledge they autonomously discover JIT from the repository.
3. **No Transcript Bleed**: Never chain historical chat transcripts into subtask or child agent prompts.
4. **Just-In-Time Context Ingestion**: Load area-level `AGENTS.md` and domain skill instructions strictly JIT when entering target folders. Extract only relevant headings or line ranges rather than full file dumps.
5. **Cost-Effective Tooling**: Use `qmd search` / `qmd get` for documentation search, `ast-grep` for code outline inspection, and Headroom for bulky command outputs.
