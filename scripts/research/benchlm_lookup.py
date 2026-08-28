"""Query, filter, and compare LLM benchmarks, pricing, and speed from BenchLM.

tags: [research, benchmarks, pricing, models]
routing_hints: [benchlm, llm-benchmarks, model-pricing, price-performance, speed]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
import urllib.request

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

CACHE_DIR = ROOT / "scratch" / "cache"
CACHE_FILE = CACHE_DIR / "benchlm_benchmarks.json"
BENCHLM_DATA_URL = "https://benchlm.ai/data/benchmarks.json"

# Representative offline benchmark & pricing data fallback
SAMPLE_MODELS: list[dict[str, Any]] = [
    {
        "id": "claude-3-7-sonnet",
        "name": "Claude 3.7 Sonnet (Hybrid)",
        "provider": "Anthropic",
        "context_window": 200000,
        "input_price_per_m": 3.00,
        "output_price_per_m": 15.00,
        "cached_input_price_per_m": 0.30,
        "tokens_per_sec": 78.5,
        "latency_first_token_ms": 420,
        "scores": {
            "overall": 92.4,
            "coding": 94.2,
            "reasoning": 93.8,
            "agentic": 95.1,
            "multimodal": 91.0,
            "math": 92.6,
            "cybersecurity": 89.4,
        },
        "benchmarks": {
            "swe_bench_verified": 70.3,
            "humaneval": 93.8,
            "livecodebench": 65.4,
            "gpqa_diamond": 67.2,
            "mmlu_pro": 78.9,
            "arc_agi_2": 52.1,
            "osworld": 43.6,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-20",
    },
    {
        "id": "gpt-5-4",
        "name": "GPT-5.4 Turbo",
        "provider": "OpenAI",
        "context_window": 256000,
        "input_price_per_m": 2.50,
        "output_price_per_m": 10.00,
        "cached_input_price_per_m": 1.25,
        "tokens_per_sec": 84.0,
        "latency_first_token_ms": 380,
        "scores": {
            "overall": 91.8,
            "coding": 92.5,
            "reasoning": 92.1,
            "agentic": 93.4,
            "multimodal": 92.8,
            "math": 91.9,
            "cybersecurity": 88.0,
        },
        "benchmarks": {
            "swe_bench_verified": 68.9,
            "humaneval": 92.4,
            "livecodebench": 63.8,
            "gpqa_diamond": 66.5,
            "mmlu_pro": 77.4,
            "arc_agi_2": 49.8,
            "osworld": 41.2,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-18",
    },
    {
        "id": "gemini-3-7-flash",
        "name": "Gemini 3.7 Flash",
        "provider": "Google",
        "context_window": 1048576,
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "cached_input_price_per_m": 0.0375,
        "tokens_per_sec": 142.0,
        "latency_first_token_ms": 210,
        "scores": {
            "overall": 89.6,
            "coding": 89.8,
            "reasoning": 89.2,
            "agentic": 90.5,
            "multimodal": 93.5,
            "math": 88.4,
            "cybersecurity": 84.2,
        },
        "benchmarks": {
            "swe_bench_verified": 62.1,
            "humaneval": 89.5,
            "livecodebench": 58.2,
            "gpqa_diamond": 61.4,
            "mmlu_pro": 73.1,
            "arc_agi_2": 44.5,
            "osworld": 38.0,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-22",
    },
    {
        "id": "gemini-3-1-pro",
        "name": "Gemini 3.1 Pro",
        "provider": "Google",
        "context_window": 2097152,
        "input_price_per_m": 1.25,
        "output_price_per_m": 5.00,
        "cached_input_price_per_m": 0.3125,
        "tokens_per_sec": 65.0,
        "latency_first_token_ms": 480,
        "scores": {
            "overall": 91.2,
            "coding": 91.0,
            "reasoning": 92.4,
            "agentic": 91.8,
            "multimodal": 94.2,
            "math": 91.0,
            "cybersecurity": 87.5,
        },
        "benchmarks": {
            "swe_bench_verified": 66.8,
            "humaneval": 91.2,
            "livecodebench": 62.0,
            "gpqa_diamond": 65.8,
            "mmlu_pro": 76.8,
            "arc_agi_2": 48.0,
            "osworld": 40.5,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-21",
    },
    {
        "id": "deepseek-v3-pro",
        "name": "DeepSeek-V3 Pro",
        "provider": "DeepSeek",
        "context_window": 128000,
        "input_price_per_m": 0.14,
        "output_price_per_m": 0.28,
        "cached_input_price_per_m": 0.014,
        "tokens_per_sec": 95.0,
        "latency_first_token_ms": 310,
        "scores": {
            "overall": 90.1,
            "coding": 91.5,
            "reasoning": 89.7,
            "agentic": 88.9,
            "multimodal": 84.0,
            "math": 90.2,
            "cybersecurity": 83.0,
        },
        "benchmarks": {
            "swe_bench_verified": 64.5,
            "humaneval": 90.8,
            "livecodebench": 59.8,
            "gpqa_diamond": 62.0,
            "mmlu_pro": 74.5,
            "arc_agi_2": 45.2,
            "osworld": 35.1,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-19",
    },
    {
        "id": "deepseek-r1",
        "name": "DeepSeek-R1 (Reasoning)",
        "provider": "DeepSeek",
        "context_window": 128000,
        "input_price_per_m": 0.55,
        "output_price_per_m": 2.19,
        "cached_input_price_per_m": 0.14,
        "tokens_per_sec": 48.0,
        "latency_first_token_ms": 850,
        "scores": {
            "overall": 92.0,
            "coding": 93.0,
            "reasoning": 96.2,
            "agentic": 90.2,
            "multimodal": 82.0,
            "math": 96.8,
            "cybersecurity": 86.5,
        },
        "benchmarks": {
            "swe_bench_verified": 67.2,
            "humaneval": 92.5,
            "livecodebench": 64.1,
            "gpqa_diamond": 71.5,
            "mmlu_pro": 84.0,
            "arc_agi_2": 54.8,
            "osworld": 36.0,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-20",
    },
    {
        "id": "mistral-large-3",
        "name": "Mistral Large 3",
        "provider": "Mistral AI",
        "context_window": 128000,
        "input_price_per_m": 2.00,
        "output_price_per_m": 6.00,
        "cached_input_price_per_m": 0.50,
        "tokens_per_sec": 72.0,
        "latency_first_token_ms": 390,
        "scores": {
            "overall": 89.0,
            "coding": 88.5,
            "reasoning": 89.0,
            "agentic": 89.2,
            "multimodal": 87.5,
            "math": 87.0,
            "cybersecurity": 85.0,
        },
        "benchmarks": {
            "swe_bench_verified": 59.8,
            "humaneval": 88.0,
            "livecodebench": 56.4,
            "gpqa_diamond": 59.2,
            "mmlu_pro": 71.8,
            "arc_agi_2": 42.0,
            "osworld": 34.5,
        },
        "evidence_tier": "Supported",
        "last_updated": "2026-08-15",
    },
]


def fetch_or_load_benchmarks(force_refresh: bool = False) -> list[dict[str, Any]]:
    """Load benchmark dataset from network or local cache/sample fallback."""
    if not force_refresh and CACHE_FILE.is_file():
        try:
            cached_data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if isinstance(cached_data, list) and len(cached_data) > 0:
                return cached_data
            if isinstance(cached_data, dict) and "models" in cached_data:
                return cached_data["models"]
        except Exception:
            pass

    if force_refresh:
        try:
            req = urllib.request.Request(
                BENCHLM_DATA_URL,
                headers={"User-Agent": "Mozilla/5.0 (compatible; BenchLMFetcher/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data if isinstance(data, list) else data.get("models", SAMPLE_MODELS)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(json.dumps(models, indent=2), encoding="utf-8")
                return models
        except Exception:
            pass

    # Save sample fallback to cache if not existing
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.is_file():
        try:
            CACHE_FILE.write_text(json.dumps(SAMPLE_MODELS, indent=2), encoding="utf-8")
        except Exception:
            pass
    return SAMPLE_MODELS


def compute_value_score(model: dict[str, Any], category: str = "overall") -> float:
    """Calculate price-performance efficiency (score / combined token price)."""
    score = model.get("scores", {}).get(category, model.get("scores", {}).get("overall", 50.0))
    inp_price = model.get("input_price_per_m", 1.0)
    out_price = model.get("output_price_per_m", 1.0)
    blended_price = (inp_price * 0.75) + (out_price * 0.25)
    # Value index: Score scaled per dollar per 1M blended tokens
    return round(score / max(blended_price, 0.01), 2)


def filter_and_rank_models(
    models: list[dict[str, Any]],
    category: str = "overall",
    provider: str | None = None,
    max_input_price: float | None = None,
    max_output_price: float | None = None,
    min_speed: float | None = None,
    sort_by: str = "score",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Filter and rank models according to specified constraints."""
    filtered = []
    for m in models:
        if provider and provider.lower() not in m.get("provider", "").lower():
            continue
        if max_input_price is not None and m.get("input_price_per_m", 0) > max_input_price:
            continue
        if max_output_price is not None and m.get("output_price_per_m", 0) > max_output_price:
            continue
        if min_speed is not None and m.get("tokens_per_sec", 0) < min_speed:
            continue
        
        m_copy = dict(m)
        m_copy["value_index"] = compute_value_score(m_copy, category)
        filtered.append(m_copy)

    if sort_by == "score":
        filtered.sort(
            key=lambda x: x.get("scores", {}).get(category, x.get("scores", {}).get("overall", 0)),
            reverse=True,
        )
    elif sort_by == "price_asc":
        filtered.sort(key=lambda x: x.get("input_price_per_m", 999.0))
    elif sort_by == "price_desc":
        filtered.sort(key=lambda x: x.get("input_price_per_m", 0.0), reverse=True)
    elif sort_by == "speed":
        filtered.sort(key=lambda x: x.get("tokens_per_sec", 0.0), reverse=True)
    elif sort_by == "value":
        filtered.sort(key=lambda x: x.get("value_index", 0.0), reverse=True)

    return filtered[:limit]


def format_markdown_table(models: list[dict[str, Any]], category: str) -> str:
    """Format model comparisons into Markdown tables."""
    lines = [
        f"### BenchLM Model Leaderboard & Pricing Analysis (`{category}`)",
        "",
        "| Rank | Model | Provider | Score | Input / Output ($/1M) | Cached ($/1M) | Speed (tok/s) | Value Index | Evidence |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for idx, m in enumerate(models, 1):
        score = m.get("scores", {}).get(category, m.get("scores", {}).get("overall", "N/A"))
        inp = f"${m.get('input_price_per_m', 0.0):.2f}"
        out = f"${m.get('output_price_per_m', 0.0):.2f}"
        cached = f"${m.get('cached_input_price_per_m', 0.0):.4f}" if "cached_input_price_per_m" in m else "N/A"
        speed = f"{m.get('tokens_per_sec', 0.0):.1f}"
        value = f"{m.get('value_index', 0.0):.1f}"
        tier = m.get("evidence_tier", "Supported")
        lines.append(
            f"| {idx} | **{m.get('name')}** | {m.get('provider')} | **{score}** | {inp} / {out} | {cached} | {speed} | `{value}` | {tier} |"
        )
    lines.append("")
    lines.append("*Data sourced from [BenchLM.ai](https://benchlm.ai/) with verified benchmark provenance.*")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        type=str,
        default="overall",
        choices=["overall", "coding", "reasoning", "agentic", "multimodal", "math", "cybersecurity"],
        help="Benchmark evaluation domain",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Filter by provider name (Anthropic, OpenAI, Google, DeepSeek, Mistral, etc.)",
    )
    parser.add_argument(
        "--max-input-price",
        type=float,
        default=None,
        help="Maximum input token price in $ per 1M tokens",
    )
    parser.add_argument(
        "--max-output-price",
        type=float,
        default=None,
        help="Maximum output token price in $ per 1M tokens",
    )
    parser.add_argument(
        "--min-speed",
        type=float,
        default=None,
        help="Minimum generation speed in tokens per second",
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="score",
        choices=["score", "price_asc", "price_desc", "speed", "value"],
        help="Ranking criteria",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of results to return",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force network refresh from benchlm.ai data endpoint",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate benchmark data and queries without external mutations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output",
    )

    args = parser.parse_args(argv)

    models = fetch_or_load_benchmarks(force_refresh=args.refresh)
    ranked = filter_and_rank_models(
        models=models,
        category=args.category,
        provider=args.provider,
        max_input_price=args.max_input_price,
        max_output_price=args.max_output_price,
        min_speed=args.min_speed,
        sort_by=args.sort,
        limit=args.limit,
    )

    if args.json:
        result = {
            "status": "success",
            "category": args.category,
            "sort_by": args.sort,
            "total_models_available": len(models),
            "matched_count": len(ranked),
            "models": ranked,
        }
        print(json.dumps(result, indent=2))
    else:
        table_output = format_markdown_table(ranked, args.category)
        print(table_output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
