"""Quota management, subagent down-tiering, and pacing helpers. Not indexed (_lib).

Provides profile resolution, 429 reset duration parsing, and batch chunking
for multi-agent workflows running on metered secondary models, platform-native
models, or enterprise unmetered clusters.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from paths import REPO_ROOT


DEFAULT_QUOTA_PROFILES: dict[str, dict[str, Any]] = {
    "unmetered": {
        "max_concurrent_subagents": 8,
        "research_subagent_tier": "inherit",
        "pacing_delay_sec": 0,
        "auto_schedule_on_429": false if "false" == "true" else False,
        "description": "Enterprise provisioned throughput or uncapped subscriptions.",
    },
    "standard": {
        "max_concurrent_subagents": 4,
        "research_subagent_tier": "flash",
        "pacing_delay_sec": 1,
        "auto_schedule_on_429": True,
        "description": "Platform-native models with standard quotas.",
    },
    "metered_secondary": {
        "max_concurrent_subagents": 2,
        "research_subagent_tier": "flash_lite",
        "pacing_delay_sec": 3,
        "auto_schedule_on_429": True,
        "description": "Secondary or quota-capped models with rolling reset windows.",
    },
}


def load_quota_profiles(repo_root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load quota_profiles from harness.config.json, falling back to defaults."""
    root = repo_root or REPO_ROOT
    config_path = root / "config" / "harness.config.json"
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                profiles = data.get("quota_profiles")
                if isinstance(profiles, dict) and profiles:
                    return profiles
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_QUOTA_PROFILES


def parse_reset_duration(error_text: str) -> int | None:
    """Extract reset delay in seconds from a 429 / RESOURCE_EXHAUSTED error message.

    Handles formats like:
      - 'Resets in 4h57m0s'
      - 'Resets in 2h30m'
      - 'Resets in 45m10s'
      - 'Resets in 30s'
      - 'retry after 120s' / 'retry-after: 120'
    """
    if not error_text:
        return None

    # Pattern: Resets in Xh Ym Zs (with any combination of h, m, s)
    hms_match = re.search(
        r"[Rr]esets in\s*(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*(?:(\d+)\s*s(?:ec(?:onds?)?)?)?",
        error_text,
    )
    if hms_match and any(hms_match.groups()):
        hours = int(hms_match.group(1) or 0)
        minutes = int(hms_match.group(2) or 0)
        seconds = int(hms_match.group(3) or 0)
        total = hours * 3600 + minutes * 60 + seconds
        if total > 0:
            return total

    # Pattern: retry[- ]after:? (\d+)s?
    retry_match = re.search(r"retry[- ]after:?\s*(\d+)\s*s?", error_text, re.IGNORECASE)
    if retry_match:
        return int(retry_match.group(1))

    return None


def resolve_quota_profile(
    host: str = "antigravity",
    model_name: str | None = None,
    env_override: str | None = None,
    profiles: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Resolve active quota profile based on environment, host, and model.

    Precedence:
      1. Explicit env_override / ROUTER_QUOTA_PROFILE env var
      2. Host check (Cursor / Enterprise -> 'unmetered')
      3. Secondary model check on Antigravity (Claude / GPT -> 'metered_secondary')
      4. Default platform-native -> 'standard'
    """
    known_profiles = profiles or load_quota_profiles()

    # 1. Environment override
    env_val = env_override or os.environ.get("ROUTER_QUOTA_PROFILE")
    if env_val and env_val in known_profiles:
        return env_val

    host_norm = (host or "").strip().lower()

    # 2. Host check
    if host_norm in ("cursor", "enterprise", "unmetered"):
        return "unmetered"

    # 3. Model check on Antigravity
    if model_name:
        model_lower = model_name.strip().lower()
        if any(sec in model_lower for sec in ("claude", "opus", "sonnet", "haiku", "gpt", "openai", "o1", "o3")):
            return "metered_secondary"

    return "standard"


def chunk_tasks(tasks: list[Any], max_concurrency: int) -> list[list[Any]]:
    """Divide a task list into sequential batches bounded by max_concurrency."""
    if max_concurrency <= 0:
        max_concurrency = 1
    return [tasks[i : i + max_concurrency] for i in range(0, len(tasks), max_concurrency)]


def format_schedule_wakeup(reset_seconds: int, prompt_action: str) -> dict[str, Any]:
    """Format payload for Antigravity schedule tool call."""
    return {
        "DurationSeconds": max(reset_seconds, 10),
        "Prompt": prompt_action,
        "TimerCondition": "never",
    }
