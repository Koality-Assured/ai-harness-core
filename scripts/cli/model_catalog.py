"""Model metadata catalog for context window limits and token pricing.

tags: [harness, cli, models, catalog, context, pricing, cost]
routing_hints: [model_catalog, context_window, token_cost, pricing]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata for a model family or specific model id."""

    context_window: int
    input_cost_per_m: float  # USD per 1M input tokens
    output_cost_per_m: float  # USD per 1M output tokens
    cache_read_cost_per_m: float = 0.0  # USD per 1M cached input tokens


DEFAULT_CONTEXT_WINDOW = 128_000

# Canonical model pricing per 1M tokens (USD)
# Provider/family baseline definitions
MODEL_PRICING_CATALOG: dict[str, ModelMetadata] = {
    # Anthropic Claude models
    "claude-5.5-sonnet": ModelMetadata(200_000, 1.50, 6.00, 0.15),
    "claude-5-5-sonnet": ModelMetadata(200_000, 1.50, 6.00, 0.15),
    "claude-5.5-opus": ModelMetadata(200_000, 5.00, 25.00, 1.25),
    "claude-5-5-opus": ModelMetadata(200_000, 5.00, 25.00, 1.25),
    "claude-5.5-haiku": ModelMetadata(200_000, 0.25, 1.25, 0.025),
    "claude-5-5-haiku": ModelMetadata(200_000, 0.25, 1.25, 0.025),
    "claude-sonnet-4-5": ModelMetadata(200_000, 3.00, 15.00, 0.30),
    "claude-3-7-sonnet": ModelMetadata(200_000, 3.00, 15.00, 0.30),
    "claude-3-5-sonnet": ModelMetadata(200_000, 3.00, 15.00, 0.30),
    "claude-3-5-haiku": ModelMetadata(200_000, 0.80, 4.00, 0.08),
    "claude-3-opus": ModelMetadata(200_000, 15.00, 75.00, 1.50),
    "claude-default": ModelMetadata(200_000, 1.50, 6.00, 0.15),
    # OpenAI models
    "gpt-6.0-luna": ModelMetadata(128_000, 1.25, 5.00, 0.30),
    "gpt-6-0-luna": ModelMetadata(128_000, 1.25, 5.00, 0.30),
    "gpt-terra": ModelMetadata(128_000, 2.50, 10.00, 0.60),
    "gpt-sol": ModelMetadata(128_000, 5.00, 20.00, 1.25),
    "gpt-4o": ModelMetadata(128_000, 2.50, 10.00, 1.25),
    "gpt-4o-mini": ModelMetadata(128_000, 0.15, 0.60, 0.075),
    "o1": ModelMetadata(128_000, 15.00, 60.00, 7.50),
    "o1-mini": ModelMetadata(128_000, 1.10, 4.40, 0.55),
    "o1-preview": ModelMetadata(128_000, 15.00, 60.00, 7.50),
    "o3": ModelMetadata(128_000, 15.00, 60.00, 7.50),
    "o3-mini": ModelMetadata(128_000, 1.10, 4.40, 0.55),
    "gpt-4-turbo": ModelMetadata(128_000, 10.00, 30.00),
    "gpt-4": ModelMetadata(8_192, 30.00, 60.00),
    "gpt-3.5-turbo": ModelMetadata(16_385, 0.50, 1.50),
    "openai-default": ModelMetadata(128_000, 1.25, 5.00, 0.30),
    # Google Gemini models
    "gemini-4-hydrogen": ModelMetadata(1_000_000, 1.50, 7.50, 0.075),
    "gemini-3.8-flash": ModelMetadata(1_000_000, 0.15, 0.60, 0.0375),
    "gemini-3-8-flash": ModelMetadata(1_000_000, 0.15, 0.60, 0.0375),
    "gemini-3.8-flash-lite": ModelMetadata(1_000_000, 0.075, 0.30, 0.01875),
    "gemini-3-8-flash-lite": ModelMetadata(1_000_000, 0.075, 0.30, 0.01875),
    "gemini-3.8-pro": ModelMetadata(1_000_000, 1.25, 5.00, 0.3125),
    "gemini-3-8-pro": ModelMetadata(1_000_000, 1.25, 5.00, 0.3125),
    "gemini-2.5-flash": ModelMetadata(1_000_000, 0.10, 0.40),
    "gemini-2.5-pro": ModelMetadata(1_000_000, 1.25, 5.00),
    "gemini-2.0-flash": ModelMetadata(1_000_000, 0.10, 0.40),
    "gemini-1.5-flash": ModelMetadata(1_000_000, 0.075, 0.30),
    "gemini-1.5-pro": ModelMetadata(1_000_000, 1.25, 5.00),
    "gemini-default": ModelMetadata(1_000_000, 1.50, 7.50, 0.075),
    # Cursor & Grok models
    "composer-2-5": ModelMetadata(200_000, 0.15, 0.60, 0.0375),
    "cursor-grok-4-7-standard": ModelMetadata(256_000, 1.00, 4.00, 0.20),
    "cursor-grok-4-7-high": ModelMetadata(500_000, 2.50, 10.00, 0.50),
    "cursor-grok-4-7-max": ModelMetadata(500_000, 5.00, 20.00, 1.00),
    # Local / Ollama models (always $0.00)
    "qwen2.5-coder:14b": ModelMetadata(32_768, 0.0, 0.0),
    "local-default": ModelMetadata(32_768, 0.0, 0.0),
}


def _normalize_provider(provider: str) -> str:
    prov = (provider or "").lower().strip()
    if prov in ("claude", "anthropic"):
        return "anthropic"
    if prov in ("gpt", "openai"):
        return "openai"
    if prov in ("google", "gemini"):
        return "gemini"
    if prov in ("local", "ollama", "llamacpp", "llama-server"):
        return "local"
    return prov


def _normalize_model_name(model: str | None) -> str:
    """Strip optional provider routing prefix (e.g. 'gemini/gemini-4-hydrogen')."""
    mod = (model or "").lower().strip()
    if "/" in mod:
        prefix, rest = mod.split("/", 1)
        if prefix in ("gemini", "google", "anthropic", "claude", "openai", "gpt", "bifrost"):
            return rest.strip()
    return mod


def get_context_window(model: str | None, provider: str = "") -> int:
    """Resolve context window limit for a model and provider.

    Defaults to 128,000 tokens when the specific ceiling is unknown.
    """
    prov = _normalize_provider(provider)
    mod = _normalize_model_name(model)

    if prov == "local":
        return 32_768

    if "qwen" in mod:
        return 32_768

    if mod in MODEL_PRICING_CATALOG:
        return MODEL_PRICING_CATALOG[mod].context_window

    if mod.startswith("claude") or prov == "anthropic":
        return 200_000

    if mod.startswith("gemini") or prov == "gemini":
        return 1_000_000

    if mod.startswith(("gpt-4o", "o1", "o3", "gpt-4-turbo")) or prov == "openai":
        if mod == "gpt-4":
            return 8_192
        if mod == "gpt-3.5-turbo":
            return 16_385
        return 128_000

    return DEFAULT_CONTEXT_WINDOW


def _resolve_model_metadata(model: str, provider: str) -> ModelMetadata:
    prov = _normalize_provider(provider)
    mod = _normalize_model_name(model)

    if prov == "local":
        return MODEL_PRICING_CATALOG["local-default"]

    if mod in MODEL_PRICING_CATALOG:
        return MODEL_PRICING_CATALOG[mod]

    # Prefix / family matching
    if mod.startswith("claude") or prov == "anthropic":
        if "haiku" in mod:
            return MODEL_PRICING_CATALOG["claude-3-5-haiku"]
        if "opus" in mod:
            return MODEL_PRICING_CATALOG["claude-3-opus"]
        return MODEL_PRICING_CATALOG["claude-default"]

    if mod.startswith("gemini") or prov == "gemini":
        if "pro" in mod:
            return MODEL_PRICING_CATALOG["gemini-3.8-pro"]
        return MODEL_PRICING_CATALOG["gemini-default"]

    if prov == "openai" or mod.startswith(("gpt", "o1", "o3")):
        if "o1-mini" in mod:
            return MODEL_PRICING_CATALOG["o1-mini"]
        if "o3-mini" in mod:
            return MODEL_PRICING_CATALOG["o3-mini"]
        if "gpt-4o-mini" in mod or ("gpt-4o" in mod and "mini" in mod):
            return MODEL_PRICING_CATALOG["gpt-4o-mini"]
        if mod.startswith(("o1", "o3")):
            return MODEL_PRICING_CATALOG["o1"]
        return MODEL_PRICING_CATALOG["openai-default"]

    return ModelMetadata(DEFAULT_CONTEXT_WINDOW, 0.0, 0.0)


def calculate_token_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate token cost in USD. Local models are always $0.00."""
    prov = _normalize_provider(provider)
    if prov == "local":
        return 0.0

    meta = _resolve_model_metadata(model, prov)
    in_tokens = max(0, int(input_tokens or 0))
    out_tokens = max(0, int(output_tokens or 0))
    cost = (in_tokens * meta.input_cost_per_m / 1_000_000.0) + (out_tokens * meta.output_cost_per_m / 1_000_000.0)
    return round(cost, 6)
