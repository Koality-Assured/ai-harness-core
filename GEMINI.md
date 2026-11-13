# Google Antigravity & Gemini Agent Guidelines

## Context Loading and Subagent Protocol

1. **Root Directives**: Adhere to the normative hierarchy defined in [`AGENTS.md`](./AGENTS.md) and [`routing/AGENTS.md`](./routing/AGENTS.md).
2. **Subagent Spawning (`invoke_subagent`)**:
   - Subagents execute in isolated context windows with clean state.
   - Supply only the explicit `Prompt`, `Role`, `TypeName`, `Model` tier, and `Workspace` mode.
   - Do NOT pass parent conversation transcripts or prior turn logs into child prompts.
3. **Progressive Disclosure**: Only skill names and descriptions are visible initially. Full skill bodies (`SKILL.md`) and target folder rules are loaded strictly Just-In-Time (JIT) when needed.
4. **Cost Layers**: Leverage QMD retrieval primitives (`qmd search` for lexical, `qmd vsearch` for dense semantic vectors, structured `qmd query`, and `qmd multi-get` for batch retrieval) for Markdown discovery from `scratch/qmd-main`, `ast-grep` for AST symbol exploration, and Headroom for bulky outputs. Never fall back to recursive shell greps unless QMD returns zero candidates.
5. **Durable Write-Back**: Record lessons and recovery strategies in `ai-tooling/memory/` and update owning source areas upon completion.
6. **Worktree file-tool access**: Mutating specialists work in `scratch/worktrees/<slug>/`. Do not deny Read/Write on that path. Indexing ignores (`.gitignore`, `.cursorindexingignore`) are not the same as agent-access denies.

## Antigravity Ultra: Model Tiering & Secondary Deferral Rules

1. **Native Model Tiering (Gemini 4 Hydrogen & 3.8 Series)**:
   - Antigravity native defaults are **Gemini 4 Hydrogen (Low)** (`fast`), **Gemini 4 Hydrogen (Medium)** (`standard`), and **Gemini 4 Hydrogen (High)** (`high`; Hydrogen's default thinking level).
   - Max reasoning tier is **Gemini 3.8 Pro** (`max`, alongside **Gemini 4 Hydrogen (xhigh)**). Older 3.8 Flash, 3.7, 3.6, and 3.1 models are retired/superseded.
   - Gemini Ultra subscription provides virtually unconstrained capacity for first-party Gemini models; Gemini remains the daily driver for exploration, repo ingestion, tool chaining, test execution, and bulk coding.

2. **Dedicated Secondary (Claude) Allocation & Utilization Policy**:
   - **Independent Silo**: In Antigravity Ultra, the third-party allocation (Claude / GPT) operates on a dedicated quota meter distinct from the first-party Gemini pool. Using Claude does not reduce Gemini capacity, and Gemini calls do not preserve Claude quota.
   - **Use-It-or-Lose-It Window**: Secondary allocations refresh on a rolling reset window (typically 5 hours). Unused quota does not bank or roll over. To maximize subscription value, agents MUST actively route eligible high-leverage tasks to Claude while the window is available.
   - **Eligible Deferral Triggers**:
     - *State & Concurrency*: Intricate distributed state machines, lock hierarchies, and race conditions.
     - *Rigid Invariant Refactoring*: Multi-module structural refactoring with strict type/semantic invariants.
     - *Adversarial & Security Audits*: Subtle authorization bypasses, reentrancy, timing attacks, and edge-case security verification.
     - *AST & Regex Parsers*: Non-trivial grammar definitions, tree-sitter parsers, and nested regex compilations.
     - *Dense Technical Specifications*: Architectural RFCs, formal API schemas, and specification drafts requiring high logical density and zero corporate filler.

3. **Anti-Waste Guardrails & Subagent Down-Tiering**:
   - Leaf exploration, documentation lookups, AST symbol searches, grep, and routine tool chaining MUST remain on fast native Gemini (`fast` / `Gemini 4 Hydrogen (Low)`, invoked via the host `invoke_subagent` `Model` enum tokens `"flash"` or `"flash_lite"`).
   - When the parent or session is running under a secondary model (Claude), child subagents (`TypeName: "research"`) **MUST NOT** inherit the secondary model. Subagents MUST explicitly specify `Model: "flash"` or `Model: "flash_lite"` (host tool-schema enum tokens).
   - Max active concurrency for secondary subagents is bounded at $N \le 2$.

4. **Allocation Check & Graceful Circuit Breaker**:
   - **Exhaustion Detection**: When a secondary model returns `RESOURCE_EXHAUSTED` (HTTP 429) or is within an active lockout countdown window (`reset_at`), the secondary circuit is considered open.
   - **Zero-Stall Fallback**: Rather than blocking progress or locking the session for 5 hours, the agent MUST immediately fall back to **Gemini 4 Hydrogen (High)** or **Gemini 3.8 Pro**.
   - **Transparent Human Notice**: The agent MUST NOT silently downgrade. The agent must notify the human: `⚠️ Secondary Claude allocation exhausted (resets in Xm). Executing via Gemini 4 Hydrogen (High) with enhanced reasoning prompts instead.`
   - **Window Re-Entry**: Once the reset timer expires, deferral to Claude re-opens automatically for the fresh rolling window.

## Cloudflare Interaction Protocol

1. **CLI Selection**: When interacting with Cloudflare, use the `cf` CLI unless the project has a Wrangler configuration file.
2. **Antigravity Customization Pathway**:
   - Cloudflare skills are discovered globally via `~/.agents/skills/`.
   - Global MCP endpoint configured in `~/.gemini/config/mcp_config.json` (`https://mcp.cloudflare.com/mcp`).
   - For administrative DNS or zone mutations outside of Workers/Pages projects, leverage the `cf` CLI (`cf auth login`) or scoped API tokens.

