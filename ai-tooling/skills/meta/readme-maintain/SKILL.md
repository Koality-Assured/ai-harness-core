---
schema_version: "2.0.0"
name: readme-maintain
description: >-
  Audit, scaffold, and context-awarely update router README.md files following
  material folder changes. Use when folders, subdirectories, or initiative specs
  are created, moved, or restructured and need human-facing directory navigation.
  Do not use for agent operational rules (AGENTS.md), generalized standards
  (doc-builder), or linter execution (markdownlint).
owner_agent: documentation-ops
rank: high
isolation: mutate
contracts:
  inputs:
    - Target directory path and summary of material folder changes
  outputs:
    - Created or updated human-facing README.md adhering to context-aware navigation standards
---

# README Maintain

Context-aware auditing, creation, and maintenance of human-facing `README.md` directory entrypoints.

## When to use

Use when:
- Material changes occur in a folder (new subfolders, restructured files, added initiative specs, or updated tool pointers) where updated human navigation is valuable.
- Scaffolding a new directory that requires a human overview alongside its `AGENTS.md`.
- Auditing existing `README.md` files to ensure they remain concise, accurate, and free of agent instructions or prompt clutter.

## When not to use

- Authoring agent rules, local constraints, or directive boundaries — use `AGENTS.md` (root or nested).
- Creating or revising generalized engineering/security standards under `docs/standards/` — use [`doc-builder`](../doc-builder/SKILL.md).
- Running Markdown linting passes — use [`markdownlint`](../markdownlint/SKILL.md).
- Updating generated routing catalogs (`routing/skill-dispatch.md`, `routing/area-map.md`) — run `python scripts/routing/generate_routing_index.py`.

## Criticality

High when repository structure or folder capabilities experience material shifts. Stale or misleading READMEs degrade human usability and orientation.

## Source of truth

- [`AGENTS.md`](../../../../AGENTS.md)
- [`docs/AGENTS.md`](../../../../docs/AGENTS.md)
- [`ai-tooling/skills/skill-conventions.md`](../../skill-conventions.md)
- `python scripts/docs/validate_router_structure.py`

## Core Philosophy: Human-Only vs. Agent Information Architecture

`README.md` files in this repository serve **strictly as human directory navigation and orientation entrypoints**:

| Channel | Target Audience | Canonical Purpose | Allowed Contents | Prohibited Contents |
| --- | --- | --- | --- | --- |
| **`README.md`** | Human Engineers & Users | High-level folder orientation and directory navigation. | Folder title, 1–2 sentence purpose, Markdown link table of subfolders/specs, prerequisites. | Agent instructions, prompt directives, tool call schemas, duplicated skill bodies. |
| **`AGENTS.md`** | Autonomous AI Agents | Strict operational MUST rules, local constraints, and dispatch next hops. | Directive hierarchy, folder intent, local constraints, JIT next hops. | Long human prose, tutorials, duplicated catalogs. |

Agents MUST NOT treat `README.md` files as a source of operational instructions or context. Agent context strictly resides in `AGENTS.md`, `routing/`, `ai-tooling/memory/`, `supporting/`, `docs/`, `ai-tooling/skills/`, and `ai-tooling/agents/`.

## Context-Aware Maintenance Methodology

When maintaining a `README.md` file, follow this context-aware lifecycle:

1. **Assess Materiality**: Determine whether the folder's recent changes represent material structural shifts (e.g., newly added child directories, moved specs, renamed tooling guides) that a human engineer needs to navigate. Minor internal file tweaks do not warrant a README update.
2. **Context-Aware Scoping**: Tailor the README structure to the specific role of the directory:
   - **Top-level areas** (e.g., `supporting/`, `docs/`, `projects/`): High-level mission statement, 1–2 sentence purpose, and a Markdown link table mapping child areas to their purpose.
   - **Leaf/tool folders** (e.g., `supporting/qmd/`, `references/cwe/`): Brief explanation of what the tool/framework is, upstream links, and key topic files.
   - **Initiative folders** (`projects/<slug>/`): High-level human project pitch, status frontmatter, and links to specs/deliverables.
3. **Drafting Constraints**:
   - Single `#` H1 title.
   - Brief 1–2 sentence orientation paragraph immediately under the title.
   - Clean, scannable Markdown table linking child paths to human-readable summaries.
   - Never embed agent prompt engineering, JSON-RPC schemas, or instructions directed at AI models.
4. **Quality Gates**:
   - In-session anti-slop and humanizer pass on newly drafted prose.
   - Validate structure via `python scripts/docs/validate_router_structure.py`.

## Isolation

`mutate`. Parent isolates the target areas via `python scripts/routing/spawn_worktree.py check` → `add` before dispatching `documentation-ops`.

## How to use

1. Inspect the target folder and its subfolders with `ast-grep` or file search tools.
2. Identify new, moved, or deleted subpaths requiring human navigation updates.
3. Edit or create the target `README.md` to reflect the updated folder structure.
4. Verify all relative links point to existing files or directories.
5. Run the validator:
   ```bash
   python scripts/docs/validate_router_structure.py
   ```
6. If indexed Markdown changed, refresh the search index:
   ```bash
   python scripts/qmd/refresh_qmd_index.py
   ```

## Dry run

```bash
python scripts/docs/validate_router_structure.py --dry-run
```

## Security

Inherits Critical cost layers: qmd for discovery; ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

[`docs/agent-session-security.md`](../../../../docs/agent-session-security.md). No credentials, secrets, or internal proprietary tokens in README files.

## Completion gates

`README.md` updated and validated. Relative links verified. If indexed paths changed, `python scripts/qmd/refresh_qmd_index.py` executed. Change-history updated via script after material structural updates.
