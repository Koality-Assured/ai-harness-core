# Change-history AGENTS

Provenance log only. **Never load this tree into agent context by default.**

Ingest simply; do not duplicate skills or paste root Critical — link [`../AGENTS.md`](../AGENTS.md). Agents append via scripts only.

## Rules

- Layout: `change-history/<YYYY>/Q<n>/entries.md`.
- Append: `python scripts/change-history/append_change_history.py`
- Rotate/create quarters: `python scripts/change-history/ensure_change_history_quarter.py`
- Entry budget ≤ ~150 tokens; no secrets; newest first in the active quarter file.
- Low-ceremony scratch under `scratch/` does not require an entry.
