# Claude Workspace Guidelines

## Invariant Rules and Protocols

All Claude Code sessions, coordinator prompts, and subagents operating in this repository MUST adhere to:

1. **Hierarchy and Navigation**: Start at [`AGENTS.md`](./AGENTS.md) -> [`routing/AGENTS.md`](./routing/AGENTS.md) -> target area `AGENTS.md` (loaded strictly Just-In-Time).
2. **Clean-Slate Subagent Spawning**: Subagents execute in isolated context windows. The coordinator passes only the specific task prompt, relevant file/agent paths, and worktree location. Do NOT pass parent conversation history or transcripts.
3. **Prompt Caching Compliance**: Respect the 5-Tier Ordered Context Hierarchy and 2-breakpoint caching structure (Tier 1/2 Base Prefix + Tier 3 Turn N-1). Do not place breakpoints on ephemeral turn deltas or churn cache blocks.
4. **Cost Layers**: Use `qmd` for Markdown discovery (`qmd search` / `qmd get`), `ast-grep` for structured code inspection, and Headroom for bulky tool outputs. Avoid dumping full repository trees.
5. **Durable Learning Loop**: Always write durable findings, fixes, and quirks to the owning source area before session completion.
