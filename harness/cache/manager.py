"""Multi-vendor prompt caching manager.

Supports:
- Anthropic: 4-breakpoint limit, ephemeral cache_control tags, 5-minute (300s) TTL, >=1024 tokens.
- OpenAI: Automatic caching prefix ordering (>=1024 tokens prefix, 128-token alignment).
- Gemini: Context Cache API planning (>=32,768 tokens threshold, explicit TTLs).
"""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from ..config import CacheConfig, HarnessConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import CacheConfig, HarnessConfig

CHARS_PER_TOKEN = 4.0


@dataclass
class CacheBreakpoint:
    """Represents a placed cache breakpoint."""

    target_type: str  # 'system' | 'tool' | 'message'
    index: int
    vendor: str
    ttl_seconds: int
    estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        """Convert breakpoint to dictionary."""
        return asdict(self)


@dataclass
class CacheOptimizationResult:
    """Outcome of optimizing a request for vendor-specific prompt caching."""

    vendor: str
    system_prompt: Any
    tools: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    breakpoints_added: int
    eligible_for_cache: bool
    estimated_tokens: int
    cache_hit_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


class PromptCacheManager:
    """Manager for optimizing prompt caching across Anthropic, OpenAI, and Gemini."""

    def __init__(self, config: CacheConfig | HarnessConfig | None = None) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.cache
        elif isinstance(config, CacheConfig):
            self.config = config
        else:
            self.config = CacheConfig()

    @staticmethod
    def estimate_tokens(text_or_obj: Any) -> int:
        """Estimate token count using chars/4 heuristic."""
        if not text_or_obj:
            return 0
        if isinstance(text_or_obj, str):
            text = text_or_obj
        else:
            try:
                text = json.dumps(text_or_obj)
            except (TypeError, ValueError):
                text = str(text_or_obj)
        return max(1, int(round(len(text) / CHARS_PER_TOKEN)))

    def optimize_anthropic(
        self,
        system_prompt: str | list[dict[str, Any]] | None,
        tools: list[dict[str, Any]] | None,
        messages: list[dict[str, Any]] | None,
    ) -> CacheOptimizationResult:
        """Apply Anthropic ephemeral cache_control breakpoints (max 4).

        Places breakpoints at:
        1. System prompt (if substantial)
        2. Last tool definition (so tool catalogue is cached together)
        3. Turn-history checkpoints / large context blocks up to the 4-breakpoint limit.
        """
        max_bps = self.config.anthropic.max_breakpoints
        min_tokens = self.config.anthropic.min_tokens_threshold
        ttl = self.config.anthropic.ttl_seconds

        tools_copy = copy.deepcopy(tools or [])
        messages_copy = copy.deepcopy(messages or [])

        bps_placed = 0
        total_tokens = 0

        # Process system prompt
        opt_system: Any = None
        if system_prompt:
            if isinstance(system_prompt, str):
                sys_tokens = self.estimate_tokens(system_prompt)
                total_tokens += sys_tokens
                if bps_placed < max_bps:
                    opt_system = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                    bps_placed += 1
                else:
                    opt_system = system_prompt
            elif isinstance(system_prompt, list):
                opt_system = []
                for idx, block in enumerate(system_prompt):
                    b_copy = dict(block)
                    sys_tokens = self.estimate_tokens(b_copy.get("text", ""))
                    total_tokens += sys_tokens
                    if bps_placed < max_bps and idx == len(system_prompt) - 1:
                        b_copy["cache_control"] = {"type": "ephemeral"}
                        bps_placed += 1
                    opt_system.append(b_copy)
        else:
            opt_system = system_prompt

        # Process tools: mark the last tool with ephemeral cache control if available
        if tools_copy:
            tools_tokens = self.estimate_tokens(tools_copy)
            total_tokens += tools_tokens
            if bps_placed < max_bps:
                tools_copy[-1]["cache_control"] = {"type": "ephemeral"}
                bps_placed += 1

        # Process messages: place breakpoints at turn checkpoints
        for idx, msg in enumerate(messages_copy):
            msg_tokens = self.estimate_tokens(msg)
            total_tokens += msg_tokens
            if bps_placed < max_bps and idx in {len(messages_copy) - 2, len(messages_copy) - 1}:
                content = msg.get("content")
                if isinstance(content, list):
                    if content and isinstance(content[-1], dict):
                        content[-1]["cache_control"] = {"type": "ephemeral"}
                        bps_placed += 1
                elif isinstance(content, str) and content:
                    msg["content"] = [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                    bps_placed += 1

        eligible = total_tokens >= min_tokens

        return CacheOptimizationResult(
            vendor="anthropic",
            system_prompt=opt_system,
            tools=tools_copy,
            messages=messages_copy,
            breakpoints_added=bps_placed,
            eligible_for_cache=eligible,
            estimated_tokens=total_tokens,
            cache_hit_metadata={
                "max_breakpoints": max_bps,
                "ttl_seconds": ttl,
                "min_tokens_threshold": min_tokens,
            },
        )

    def optimize_openai(
        self,
        system_prompt: str | None,
        tools: list[dict[str, Any]] | None,
        messages: list[dict[str, Any]] | None,
    ) -> CacheOptimizationResult:
        """Structure request for OpenAI automatic prompt caching (>=1024 token prefix).

        Ensures static system prompt and tools form a deterministic, aligned prefix.
        """
        min_prefix = self.config.openai.min_tokens_prefix
        alignment = self.config.openai.prefix_alignment_tokens

        tools_copy = [dict(t) for t in (tools or [])]
        messages_copy = [dict(m) for m in (messages or [])]

        # Ensure system prompt is first message if provided as string
        ordered_messages: list[dict[str, Any]] = []
        if system_prompt:
            if not any(m.get("role") == "system" for m in messages_copy):
                ordered_messages.append({"role": "system", "content": system_prompt})

        ordered_messages.extend(messages_copy)

        prefix_tokens = self.estimate_tokens(tools_copy) + (
            self.estimate_tokens(system_prompt) if system_prompt else 0
        )
        total_tokens = prefix_tokens + sum(self.estimate_tokens(m) for m in messages_copy)

        eligible = prefix_tokens >= min_prefix
        aligned_prefix_tokens = (prefix_tokens // alignment) * alignment

        return CacheOptimizationResult(
            vendor="openai",
            system_prompt=system_prompt,
            tools=tools_copy,
            messages=ordered_messages,
            breakpoints_added=0,  # OpenAI caching is automatic on prefix match
            eligible_for_cache=eligible,
            estimated_tokens=total_tokens,
            cache_hit_metadata={
                "min_tokens_prefix": min_prefix,
                "alignment_tokens": alignment,
                "prefix_tokens": prefix_tokens,
                "aligned_prefix_tokens": aligned_prefix_tokens,
            },
        )

    def optimize_gemini(
        self,
        system_instruction: str | None,
        contents: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Prepare descriptor for Gemini Context Cache API (>=32,768 tokens)."""
        threshold = self.config.gemini.min_tokens_threshold
        ttl = ttl_seconds if ttl_seconds is not None else self.config.gemini.default_ttl_seconds

        total_tokens = (
            self.estimate_tokens(system_instruction)
            + sum(self.estimate_tokens(c) for c in contents)
            + (self.estimate_tokens(tools) if tools else 0)
        )

        eligible = total_tokens >= threshold

        descriptor: dict[str, Any] = {
            "vendor": "gemini",
            "eligible_for_context_cache": eligible,
            "estimated_tokens": total_tokens,
            "min_tokens_threshold": threshold,
            "ttl_seconds": ttl,
            "ttl_string": f"{ttl}s",
            "cached_content_spec": {
                "system_instruction": {"parts": [{"text": system_instruction}]} if system_instruction else None,
                "contents": contents,
                "tools": tools or [],
                "ttl": f"{ttl}s",
            },
        }
        return descriptor
