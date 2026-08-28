# Koality-Assured AI Harness Core

Generic AI harness template. Clone this tree, then feed your own domain
topic (standards, references, skills, projects) without inheriting another
instance's security corpus.

## Mission Statement

Ship a reusable, non-domain-fed harness so future domain routers can
plug in their own topic. The Python engine under `.harness/` stays part of
the template; it is not the whole product.

## Architecture Overview

The public export is a full harness tree (same top-level areas as the private
harness), not a flattened Python package:

```
AGENTS.md                 # root agent contract
routing/                  # area map + skill dispatch
ai-tooling/               # filtered skills, agents, A2A, memory scaffolds
scripts/                  # routing, qmd, cost-layers, change-history, sync
supporting/               # qmd, ast-grep, headroom, github, powershell
docs/                     # session security, anti-slop, portable harness standards
.harness/                 # embeddable engine (kept as .harness/, not harness/)
references/               # tooling families only (conventional-commits, markdown, valid-sources)
actionable/ projects/ research/ results/ scratch/ change-history/
```

Domain-fed content (OWASP/NIST/CWE dumps, cloud-provider skills, instance
projects) is omitted. Empty areas keep an AGENTS.md so you can feed them later.

## Quick Start: Feed a Domain

1. Clone this template.
2. Add domain standards under `docs/standards/` and references under `references/`.
3. Add domain skills under `ai-tooling/skills/` and regenerate routing indexes.
4. Keep `.harness/` as the engine; do not flatten it into a Python-package-only product.

```bash
python scripts/routing/generate_routing_index.py
python scripts/qmd/refresh_qmd_index.py
```

## Verification & Testing

```bash
python -m compileall -q scripts .harness
python -m unittest discover -s scripts/tests -v
```

## Security Notice

Public export still runs redaction/audit. Never commit secrets, home paths, or
tokens. Session security MUST lives in `docs/agent-session-security.md`.

## License

MIT License Copyright (c) 2026 Koality-Assured.
