---
schema_version: "2.0.0"
name: as-code-builder
description: >-
  Draft Terraform, Pulumi, Ansible, Kyverno, Rego, or similar as-code under
  results/as-code/<type>/<topic>/<date>/. Use when producing IaC or policy-as-code
  artifacts. Do not apply or deploy to real clouds.
owner_agent: as-code-agent
rank: high
isolation: mutate
contracts:
  inputs:
    - As-code type (terraform, pulumi, ansible, kyverno, rego, ...) and topic slug
  outputs:
    - Draft IaC or policy-as-code under results/as-code/<type>/<topic>/<date>/ (not applied)
---

# As-code builder

## When to use

Produce parameterized as-code (Terraform, Pulumi, Ansible, Kyverno, Rego, similar) under `results/as-code/`.

## When not to use

Applying or deploying to real clouds: follow destination-local cloud policy and official provider tools, or report a capability gap if none is available. Optional ai-router provenance: `cloud-operator` owns its cloud-write skills. Generic diagrams (`architecture-diagram`).

## Criticality

High: never apply/deploy via this skill or A2A. Parameterize type explicitly.

## Source of truth

- `results/AGENTS.md` (`../../../../results/AGENTS.md`; ai-router-only, optional provenance)
- Related patterns via `qmd search`
- `python scripts/results/new_run_dir.py --family as-code --topic <slug> --type <type>`

## Isolation

Standalone dispatch: Follow the destination's isolation and dispatch rules. Use a registered local operator or continue in-session when those rules permit; report a capability gap if no local path supports the work.

`mutate`. In ai-router, the parent spawns `as-code-agent` with area `results`.

## How to use

1. Confirm `type` (terraform|pulumi|ansible|kyverno|rego|…) and topic from the parent prompt.
2. `qmd search` for in-repo patterns — no tree walks, no README for ops.
3. `python scripts/results/new_run_dir.py --family as-code --topic <slug> --type <type>` → `results/as-code/<type>/<topic>/<YYYY-MM-DD>/`.
4. Author modules/policies; use ast-grep for structured YAML/JSON/HCL facts when helpful.
5. Do **not** apply, plan against live clouds, or store credentials.

## Dry run

```bash
python scripts/results/new_run_dir.py --family as-code --topic <slug> --type <type> --dry-run
```

Scaffold dir + file list in a worktree only; no cloud apply.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

A2A MUST NOT apply/deploy. No credentials in repo or prompts.

## Completion gates

Path under `results/as-code/<type>/<topic>/<date>/`. Confirm nothing was applied.
