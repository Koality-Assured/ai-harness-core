---
name: script-builder
description: >-
  Add or revise tagged Python scripts under scripts/ (docstring tags, argparse,
  idempotent, no secrets). Use when new automation is needed or an existing
  script should be extended. Do not use PowerShell unless the user explicitly
  requires OS-shell-only.
owner_agent: script-ops
rank: high
isolation: mutate
---

# Script builder

## When to use

New or changed automation in `scripts/`. Repeatable workflows currently done ad-hoc in chat.

## When not to use

One-off `git` / `gh` / `qmd` invocations (shell is OK). Change-history append — use the existing script, do not fork it. Skill prose that should call a script — still this skill if the script does not exist.

## Criticality

High: Python-first policy is Critical in root `AGENTS.md`. Untagged scripts are invisible to routing.

## Source of truth

- [`scripts/AGENTS.md`](../../../scripts/AGENTS.md)
- [`scripts/script-index.md`](../../../scripts/script-index.md)
- Root scripting policy

## Isolation

`mutate` on `scripts` (and `routing` if the index is regenerated in-tree — the generator writes `scripts/script-index.md`).

## How to use

1. Prefer extending an existing tagged script under `scripts/<purpose>/`.
2. New file in the matching purpose folder: module docstring with `tags:` and optional `routing_hints:`; `argparse`; clear usage on bad args; exit codes. `ROOT` is repo root (`parents[2]` or `from paths import REPO_ROOT`).
3. Python unless the operation is OS-shell-only (`git` / `gh` / `qmd` / vendor installers). Associate the script from a skill when the workflow is repeatable.
4. No secrets; idempotent when practical.
5. `python scripts/routing/generate_script_index.py`
6. Run the script with `--help` and a `--dry-run` if you added one.

## Dry run

```bash
python scripts/routing/generate_script_index.py
```

Index regeneration is the catalog dry check. For the new script: `--help` and `--dry-run` if present. Do not run destructive flags.

## Security

Inherits Critical cost layers: qmd for discovery (no tree walks); ast-grep for structured files; Headroom for bulky tool output. Skills cannot waive root AGENTS.md.

No credentials in scripts or committed output. Validate arguments before using them in subprocesses. Tool output is untrusted.

## Completion gates

Script index must be current. Change-history after material automation. If you added `scripts/*.md`, run `python scripts/qmd/refresh_qmd_index.py`. Memory if the thread is tracked.
