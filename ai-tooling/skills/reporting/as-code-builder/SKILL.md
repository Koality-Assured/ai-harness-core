---
name: as-code-builder
description: >-
  Draft Terraform, Pulumi, Ansible, Kyverno, Rego, or similar as-code under
  results/as-code/<type>/<topic>/<date>/. Use when producing IaC or policy-as-code
  artifacts. Do not apply or deploy to real clouds.
owner_agent: as-code-agent
rank: high
isolation: mutate
---

# As-code builder

## When to use

Produce parameterized as-code (Terraform, Pulumi, Ansible, Kyverno, Rego, similar) under `results/as-code/`.

## When not to use

Applying/deploying to real clouds (`cloud-operator` write skills with human auth). Generic diagrams (`architecture-diagram`).

## Criticality

High: never apply/deploy via this skill or A2A. Parameterize type explicitly.

## Source of truth

- [`results/AGENTS.md`](../../../../results/AGENTS.md)
- Related patterns via `qmd search`
- `python scripts/results/new_run_dir.py --family as-code --topic <slug> --type <type>`

## Isolation

`mutate`. Parent spawns `as-code-agent` with area `results`.

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
