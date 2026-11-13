"""Dynamic schema inspection and adapter for multi-harness repositories.

Reads and adapts routing/areas.yaml, ai-tooling/skills, and ai-tooling/agents
from any active or targeted domain harness checkout.

tags: [harness, cli, schema, adapter, multi-harness]
routing_hints: [harness, schema, adapter, areas, skills, agents]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure _lib and scripts are in sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "_lib"
for _p in (str(_LIB_DIR), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from areas import AreasYamlError, load_area_records
except ImportError:
    AreasYamlError = ValueError  # type: ignore[assignment, misc]
    load_area_records = None  # type: ignore[assignment]

from cli.registry import get_registry


def resolve_harness_root(harness_arg: str | None = None, fallback_cwd: Path | None = None) -> Path:
    """Resolve the target repository root path for harness commands.
    
    If harness_arg is provided, resolves from the registry by ID or path.
    Otherwise checks if an active harness is recorded in the registry.
    If no active harness is recorded, defaults to fallback_cwd or Path.cwd().
    """
    reg = get_registry()

    if harness_arg:
        record = reg.get_harness(harness_arg)
        if record:
            return Path(record["path"]).resolve()
        # Check if direct directory path
        p = Path(harness_arg).resolve()
        if p.is_dir():
            return p
        raise ValueError(f"Target harness '{harness_arg}' is not registered and does not exist as a directory.")

    active = reg.get_active_harness()
    if active:
        p = Path(active["path"]).resolve()
        if p.is_dir():
            return p

    return (fallback_cwd or Path.cwd()).resolve()


def load_dynamic_areas(repo_root: Path) -> list[dict[str, str]]:
    """Load area records from the specified repository's routing/areas.yaml."""
    areas_file = repo_root / "routing" / "areas.yaml"
    if not areas_file.is_file():
        return []

    if load_area_records:
        try:
            return load_area_records(repo_root)
        except Exception:
            pass

    # Simple fallback parser if _lib.areas cannot resolve
    results = []
    try:
        raw = areas_file.read_text(encoding="utf-8")
        current: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                if current and "id" in current:
                    results.append(current)
                current = {"id": stripped.split(":", 1)[1].strip()}
            elif current and ":" in stripped and not stripped.startswith("#"):
                k, _, v = stripped.partition(":")
                current[k.strip()] = v.strip()
        if current and "id" in current:
            results.append(current)
    except Exception:
        pass

    return results


def load_dynamic_agents(repo_root: Path) -> list[dict[str, Any]]:
    """Discover agents defined within the specified repository's ai-tooling/agents/."""
    agents_dir = repo_root / "ai-tooling" / "agents"
    if not agents_dir.is_dir():
        return []

    records = []
    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue
        spec_file = agent_dir / "AGENT.md"
        if spec_file.is_file():
            summary: dict[str, Any] = {
                "id": agent_dir.name,
                "path": str(spec_file),
                "title": agent_dir.name,
                "tier": "standard",
            }
            try:
                content = spec_file.read_text(encoding="utf-8")
                for line in content.splitlines()[:20]:
                    if line.startswith("# "):
                        summary["title"] = line[2:].strip()
                    elif "model_tier:" in line.lower() or "tier:" in line.lower():
                        summary["tier"] = line.split(":", 1)[1].strip()
            except Exception:
                pass
            records.append(summary)

    return records
