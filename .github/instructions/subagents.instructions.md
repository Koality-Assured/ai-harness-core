---
applyTo: "**/*"
---

# Subagent Context and Execution Boundaries

When delegating tasks to subagents or child tools:
- Initialize the subagent with clean-slate context (task specification + file/worktree pointers only).
- Do not forward parent multi-turn dialogue or conversation history.
- Ensure the subagent discovers repository facts autonomously via targeted search and JIT file reads.
