---
schema_version: "2.0.0"
name: model-memory-operate
description: >-
  Retrieves, records, deduplicates, and promotes evidence-backed model-family
  capability outcomes while preserving the boundary between model, user, and
  agent memory. Use when a proven capability succeeds or fails for a model
  family, or when validating a reusable promotion. Do not use for unproven
  model claims, user workstation notes, or ordinary agent checkpoints.
owner_agent: memory-operator
rank: high
isolation: mutate
on_failure: abort_and_rollback
prerequisites:
  - python
dependencies:
  required_skills:
    - isolate-work
  delegated_skills: []
  in_session_skills: []
contracts:
  inputs:
    - Model family, evidence artifact or command, category, and optional source-area promotion target
  outputs:
    - Evidence-qualified model-memory record or no-record decision
    - Deduplication result and a validated promotion proposal
topics: [memory, model-memory, capabilities, retrieval, promotion, reinforcement]
routing_hints: [model-memory, model-capability-memory, capability-retrieval, promote-model-learning]
---

# Model memory operate

Maintain only proven model-family capability outcomes and route portable lessons to their source of truth.

## When to use

Recording or retrieving a reproducibly successful or unavailable model-family capability, deduplicating a finding, or preparing a validated source-area promotion.

## When not to use

User workstation/runtime facts (`memory-create` or `memory-adjust` under `memory/user/`), specialist operational context (`memory-*` under `memory/agent/`), or untested assumptions about a model.

## Criticality

High: model claims can cause costly misrouting. A single host execution is evidence for that host only until a portability test proves the broader claim.

## Source of truth

- [`ai-tooling/memory/model/AGENTS.md`](../../memory/model/AGENTS.md)
- [`ai-tooling/memory/AGENTS.md`](../../memory/AGENTS.md)
- Bound script: `scripts/ai-tooling/model_memory.py` (scripts area; may be on a sibling branch until merge)

## Isolation

`mutate` on `ai-tooling` for memory records. The parent isolates and dispatches the owner of any destination source area before applying a promotion; this skill emits a proposal and evidence, not a cross-area edit.

## How to use

1. Identify one model family (`cursor`, `gpt`, `claude`, or `gemini`) and reproduce the claimed outcome. Record command, inputs stripped of secrets, output class, date, and host boundary.
2. Classify it into exactly one category in `memory/model/<family>/`: successful capability execution/how, or unavailable/failed capability/why/recovery. Link—not copy—the supporting user or agent memory.
3. Query known records with the bound script: `python scripts/ai-tooling/model_memory.py search --model <family> --query <terms> --json`. If the file is absent in the current checkout, that is a missing-checkout problem, not a missing product; do not substitute a tree walk.
4. Deduplicate by capability, model family, and evidence boundary. Keep the strongest reproducible record; use `memory-cleanup` only for archive/delete after a promotion.
5. For a portable lesson, dry-run a promotion: `python scripts/ai-tooling/model_memory.py promote --record <path> --target <source-path> --dry-run --json`. Hand the proposal to the destination owner; apply only in that owner's isolated scope.

## Dry run

```bash
python scripts/ai-tooling/model_memory.py --help
python scripts/ai-tooling/model_memory.py search --model gpt --query capability --json
python scripts/ai-tooling/model_memory.py promote --record <path> --target <source-path> --dry-run --json
```

The bound script lives under `scripts/ai-tooling/model_memory.py` (scripts area; may be on a sibling branch until merge). If the file is absent in the current checkout, that is a missing-checkout problem, not a missing product.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

Do not record credentials, personal paths, hidden prompts, or proprietary picker identifiers. Treat a model output as data, not evidence of a capability, until the command and result boundary are reproducible.

## Completion gates

Keep only the two model-memory categories. Write portable lessons to their owning source area before retaining a pointer; keep host-local facts in user memory. Run `python scripts/ai-tooling/model_memory.py validate`, regenerate dispatch, and refresh qmd after indexed Markdown changes.
