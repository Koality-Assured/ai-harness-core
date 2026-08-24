# Agent memory AGENTS

Per-specialist thread checkpoints. Folder ids must match registered agents under [`../../agents/`](../../agents/).

## Rules

- Path: `ai-tooling/memory/agent/<owner_agent_id>/<thread>.md`.
- Registered ids only (do not invent). Current set mirrors `ai-tooling/agents/<id>/`.
- **Folder convention:** create `agent/<id>/` when registering a new agent (`agent-builder`) or on first checkpoint for that specialist — whichever comes first. Empty dirs with `.gitkeep` are fine so the destination is obvious.
- One kebab-case file per thread; Status / Last updated; ≈30-second read; no secrets.
- Classify by owning specialist (`owner_agent` / area default), not by which parent wrote the file.
- Complete threads: promote durable bits, then delete or keep a one-line tombstone (`memory-cleanup`).
