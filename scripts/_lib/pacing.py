"""Quota management, subagent down-tiering, and pacing helpers. Not indexed (_lib).

Provides profile resolution, 429 reset duration parsing, and batch chunking
for multi-agent workflows running on metered secondary models, platform-native
models, or enterprise unmetered clusters.
"""

from __future__ import annotations

import json
import os
import re
import time
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
        "description": "Platform-native models with standard quotas (Gemini 3.8 Flash).",
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


def get_quota_state_path(repo_root: Path | None = None) -> Path:
    """Path to the local scratch quota state tracker."""
    root = repo_root or REPO_ROOT
    return root / "scratch" / "quota_state.json"


def record_secondary_exhaustion(
    reset_seconds: int,
    provider: str = "claude",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Record a 429 lockout window in the local quota state tracker."""
    now = time.time()
    reset_at = now + max(reset_seconds, 0)
    state = {
        "exhausted": True,
        "provider": provider,
        "exhausted_at": now,
        "reset_at": reset_at,
        "reset_seconds": reset_seconds,
    }
    path = get_quota_state_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError:
        pass
    return state


def check_secondary_availability(repo_root: Path | None = None) -> tuple[bool, int]:
    """Check if the secondary model allocation is available.

    Returns:
        (is_available, seconds_remaining_in_lockout)
        If available, returns (True, 0).
        If exhausted/in-cooldown, returns (False, remaining_seconds).
    """
    path = get_quota_state_path(repo_root)
    if not path.is_file():
        return True, 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data.get("exhausted"):
            return True, 0
        reset_at = float(data.get("reset_at", 0))
        now = time.time()
        remaining = int(reset_at - now)
        if remaining <= 0:
            clear_secondary_exhaustion(repo_root)
            return True, 0
        return False, remaining
    except (OSError, json.JSONDecodeError, ValueError):
        return True, 0


def clear_secondary_exhaustion(repo_root: Path | None = None) -> None:
    """Clear secondary exhaustion state after reset window expires."""
    path = get_quota_state_path(repo_root)
    if path.is_file():
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"exhausted": False}, f, indent=2)
        except OSError:
            pass


# Canonical triggers for Antigravity Ultra secondary model (Claude) deferral
DEFERRAL_TRIGGERS: dict[str, list[str]] = {
    "state_and_concurrency": [
        r"\brace condition\b",
        r"\bdistributed lock(?:ing)?\b",
        r"\bmutex hierarch(?:y|ies)\b",
        r"\bdeadlock\b",
        r"\bchannel synchroniz\w+\b",
        r"\batomic state machine\b",
        r"\bthread safety\b",
        r"\bmemory ordering\b",
        r"\bconcurrent state machine\b",
        r"\bgoroutine leak\b",
        r"\block inversion\b",
    ],
    "rigid_invariant_refactoring": [
        r"\binvariant refactor(?:ing)?\b",
        r"\bpreserv(?:e|ing) invariants\b",
        r"\bstructural refactor(?:ing)?\b",
        r"\brigid (?:type|semantic) invariants\b",
        r"\bsemantic invariants\b",
        r"\bcross-module coupling\b",
        r"\binterface invariants\b",
        r"\barchitectural refactor(?:ing)?\b",
    ],
    "adversarial_security_audit": [
        r"\badversarial (?:code )?audit\b",
        r"\bsecurity audit\b",
        r"\btiming attack\b",
        r"\btiming leak\b",
        r"\bauth(?:orization)? bypass\b",
        r"\bcryptographic flaw\b",
        r"\breentrancy\b",
        r"\bside-channel\b",
        r"\bconstant[- ]time\b",
        r"\bprivilege escalation\b",
        r"\btoken refresh\b",
        r"\bsession verification\b",
        r"\bsession fixation\b",
        r"\bcsrf (?:protection|attack|token|defense|mismatch)\b",
        r"\boauth (?:security|audit|vulnerability|flaw)\b",
        r"\btoken lifecycle\b",
    ],
    "ast_and_regex_parser": [
        r"\btree-sitter grammar\b",
        r"\bast (?:compiler|parser)\b",
        r"\bcompiler grammar\b",
        r"\bregex engine\b",
        r"\bnested regex\b",
        r"\btoken-level grammar\b",
        r"\bparser grammar\b",
        r"\blexer tokens\b",
    ],
    "dense_technical_rfc": [
        r"\barchitectural? rfc\b",
        r"\bformal api schema\b",
        r"\btechnical specification\b",
        r"\brfc draft\b",
        r"\barchitectural? proposal\b",
        r"\bformal schema definition\b",
        r"\barchitectural decision record\b",
    ],
}

# Negative anti-triggers (operational plumbing best served by Gemini Ultra)
DISQUALIFYING_OPERATIONAL_PATTERNS: list[str] = [
    r"^(?:run|execute)\s+(?:pytest|unittest|tests?|suite)\b",
    r"^(?:git\s+)?(?:status|add|commit|push|pull|merge|checkout|fetch)\b",
    r"^(?:grep|rg|search)\s+(?:codebase|repo|files?|directory|docs?)\b",
    r"^(?:fix|clean)\s+(?:lint|linter|flake8|markdownlint|formatting|style)\b",
    r"^(?:generate|write)\s+(?:docstrings?|boilerplate|getters|setters)\b",
]


def classify_deferral_eligibility(
    prompt: str,
    host: str = "antigravity",
    is_subagent: bool = False,
    subagent_type: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Classify whether a task is eligible for secondary (Claude) deferral in Antigravity Ultra.

    Enforces:
      1. Anti-waste guardrails: Subagent leaf workers and operational tasks stay on Gemini.
      2. Material pillar matching: Concurrency, invariant refactoring, security audits,
         grammars/parsers, and dense RFCs qualify.
      3. Zero-stall circuit-breaker: Automatically pivots to Gemini 3.8 Flash (High) on 429 lockout.
    """
    prompt_clean = (prompt or "").strip()
    host_norm = (host or "").strip().lower()

    # Rule 1: Non-Antigravity hosts follow their own platform-native rules
    if host_norm != "antigravity":
        return {
            "should_defer": False,
            "recommended_model": "platform-native",
            "trigger": None,
            "reason": f"Host '{host}' follows platform-native model tiering.",
            "quota_profile": "unmetered" if host_norm in ("cursor", "enterprise") else "standard",
            "fallback_active": False,
            "remaining_cooldown_sec": 0,
        }

    # Rule 2: Subagents must strictly down-tier to flash (never inherit secondary Claude)
    if is_subagent:
        tier = "flash_lite" if subagent_type == "research" else "flash"
        return {
            "should_defer": False,
            "recommended_model": tier,
            "trigger": None,
            "reason": "Subagent leaf workers must down-tier to flash to preserve secondary quota.",
            "quota_profile": "metered_secondary",
            "fallback_active": False,
            "remaining_cooldown_sec": 0,
        }

    # Rule 3: Check for purely operational commands (hard disqualifiers)
    for pattern in DISQUALIFYING_OPERATIONAL_PATTERNS:
        if re.search(pattern, prompt_clean, re.IGNORECASE):
            return {
                "should_defer": False,
                "recommended_model": "Gemini 3.8 Flash",
                "trigger": None,
                "reason": "Operational plumbing task reserved for Gemini Ultra high-throughput capacity.",
                "quota_profile": "standard",
                "fallback_active": False,
                "remaining_cooldown_sec": 0,
            }

    # Rule 4: Match positive deferral triggers
    matched_trigger: str | None = None
    for category, regex_list in DEFERRAL_TRIGGERS.items():
        for regex in regex_list:
            if re.search(regex, prompt_clean, re.IGNORECASE):
                matched_trigger = category
                break
        if matched_trigger:
            break

    if not matched_trigger:
        return {
            "should_defer": False,
            "recommended_model": "Gemini 3.8 Flash",
            "trigger": None,
            "reason": "Task does not meet material secondary deferral criteria; default to Gemini Ultra.",
            "quota_profile": "standard",
            "fallback_active": False,
            "remaining_cooldown_sec": 0,
        }

    # Rule 5: Check secondary quota availability (Circuit-Breaker check)
    is_available, rem = check_secondary_availability(repo_root)
    if not is_available:
        return {
            "should_defer": False,
            "recommended_model": "Gemini 3.8 Flash (High)",
            "trigger": matched_trigger,
            "reason": f"Matches trigger '{matched_trigger}', but secondary quota is exhausted ({rem}s remaining). Zero-stall circuit-breaker fallback to Gemini 3.8 Flash (High).",
            "quota_profile": "metered_secondary",
            "fallback_active": True,
            "remaining_cooldown_sec": rem,
        }

    # Rule 6: Fully eligible and window is active
    return {
        "should_defer": True,
        "recommended_model": "Claude 5.5 Sonnet",
        "trigger": matched_trigger,
        "reason": f"Matches material deferral trigger '{matched_trigger}'. Active in rolling use-it-or-lose-it window.",
        "quota_profile": "metered_secondary",
        "fallback_active": False,
        "remaining_cooldown_sec": 0,
    }


def format_deferral_notice(deferral_info: dict[str, Any]) -> str | None:
    """Format human-facing notice required by GEMINI.md when secondary deferral is recommended or fallback occurs."""
    if deferral_info.get("fallback_active"):
        rem_sec = deferral_info.get("remaining_cooldown_sec", 0)
        rem_min = max(1, round(rem_sec / 60))
        return (
            f"⚠️ Secondary Claude allocation exhausted (resets in {rem_min}m). "
            "Executing via Gemini 3.8 Flash (High) with enhanced reasoning prompts instead."
        )
    if deferral_info.get("should_defer"):
        trigger = deferral_info.get("trigger", "high-leverage reasoning")
        model = deferral_info.get("recommended_model", "Claude 5.5 Sonnet")
        return (
            f"ℹ️ Task qualifies for Antigravity Ultra secondary model deferral ({trigger}). "
            f"Active in rolling 5-hour window -> Recommended model: {model}."
        )
    return None


