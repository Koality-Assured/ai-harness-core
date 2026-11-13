# PowerShell AGENTS

Durable shell execution recipes, quoting and escape caveats, Windows security controls, and safe process execution patterns.

Ingest simply; do not duplicate skills or paste root Critical — link [`../../AGENTS.md`](../../AGENTS.md). Human overview: [`README.md`](./README.md).

## Purpose

Maintain operational execution standards, cross-platform pathing rules, and quoting workarounds for running Python, Node/npx, and CLI automation under Windows PowerShell while enforcing script safety.

## Local Constraints

1. **Strict Output Fire-Wall:** `supporting/` is strictly an input resource and accelerator store. Agents and scripts MUST NEVER deposit shell run logs, diagnostic dumps, or terminal output captures into `supporting/powershell/`. All run artifacts MUST route to `results/` per [`../../results/results-conventions.md`](../../results/results-conventions.md).
2. **One-Way Dependency Invariant:** Supporting files MUST NOT link back to transient `projects/`, `research/`, or `actionable/` queues.
3. **Scripting Policy (Python Default):** Python is the primary automation language across the repository. Agents MUST NOT create new PowerShell scripts (`.ps1`) unless directed to an existing `.ps1` file or explicitly required by the user for OS-shell-only operations (`git`, `gh`, `qmd`, vendor installers). Prefer tagged Python under `scripts/<purpose>/`.
4. **No Inline `python -c` Escape Traps:** Avoid complex inline `python -c "..."` commands in PowerShell to prevent corrupting paths (`\a`, `\r`, `\t` escaping to control characters) and backtick interpolation. For tasks exceeding 2 lines, write a dedicated script in `scratch/` and execute via `python scratch/<script>.py`.
5. **Forward Slashes & Explicit UTF-8 Encoding:** Always use forward slashes (`/`) for paths across Python, git, npm, and CLI tools. Scripts reading or writing files must use explicit `encoding="utf-8"`.
6. **Read-Only Windows Security Control Preflights:** When inspecting Smart App Control (SAC) or Code Integrity failures, agents MUST use read-only queries (Event IDs 3076/3077, registry reads). Agents MUST NOT attempt to disable SAC or weaken Code Integrity policies.
7. **Execution Policy & Shim Resolution:** In default Windows environments where `ExecutionPolicy` restricts `.ps1` execution, prefer `qmd.cmd` or repo Python wrappers implementing `resolve_qmd()`, or configure `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force` once without admin elevation.

## Next Hops

- Shell quoting caveats & execution patterns: [`powershell-python-patterns.md`](./powershell-python-patterns.md)
- Smart App Control preflight checks: [`windows-execution-control.md`](./windows-execution-control.md)
- Machine setup & environment onboarding: [`../workstation-onboarding.md`](../workstation-onboarding.md)
- Default specialist: [`../../ai-tooling/agents/harness-operator/AGENT.md`](../../ai-tooling/agents/harness-operator/AGENT.md)
