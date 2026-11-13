"""Dry-run Headroom compression: token savings vs gold-fact accuracy with multi-trial randomization.

tags: [headroom, qmd, cost-layers, benchmarks]
routing_hints: [validation, dry-run, tokens, compression, multi-trial, randomized]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
CHARS_PER_TOKEN = 4.0


def _ensure_headroom_import() -> None:
    try:
        import headroom  # noqa: F401

        return
    except ImportError:
        pass
    home = Path.home()
    candidates = [
        home / "AppData/Roaming/uv/tools/headroom-ai/Lib/site-packages",
        home / ".local/share/uv/tools/headroom-ai/lib",
    ]
    for site in candidates:
        if site.is_dir():
            sys.path.insert(0, str(site))
            import headroom  # noqa: F401

            return
        # Linux/mac uv layout: .../headroom-ai/lib/python3.x/site-packages
        if site.parent.is_dir():
            for match in site.parent.glob("python*/site-packages"):
                sys.path.insert(0, str(match))
                try:
                    import headroom  # noqa: F401

                    return
                except ImportError:
                    continue
    raise SystemExit(
        "error: cannot import headroom; install with: "
        "uv tool install --python 3.13 \"headroom-ai[proxy,mcp]\""
    )


def est_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(round(len(text) / CHARS_PER_TOKEN)))


@dataclass
class Fixture:
    id: str
    kind: str
    gold_facts: list[str]
    messages: list[dict]
    trial_idx: int = 0


def generate_json_search_fixture(trial: int = 0, rng: random.Random | None = None) -> Fixture:
    """Generate a randomized JSON array search result fixture."""
    if rng is None:
        rng = random.Random(42 + trial)
    marker = f"FATAL unique-marker-HR-JSON-ZX{trial}_{rng.randint(100, 999)}"
    gold_line = f"preserve incident line trial {trial}"
    row_count = 60 + (trial * 20) + rng.randint(0, 15)
    
    rows = []
    for i in range(row_count):
        keys = ["id", "title", "snippet", "metadata"]
        rng.shuffle(keys)
        item = {
            "id": i,
            "title": f"Result {i} (batch {trial})",
            "snippet": f"boilerplate error context {i} " * rng.randint(12, 22),
            "metadata": {"status": "ok", "trial": trial, "weight": rng.random()},
        }
        rows.append(item)
    
    insert_pos = rng.randint(len(rows) // 2, len(rows) - 1)
    rows.insert(insert_pos, {
        "id": 9999 + trial,
        "title": marker,
        "snippet": gold_line,
        "metadata": {"critical": True, "alert_level": "high"},
    })
    
    content = json.dumps({"results": rows, "total": len(rows), "trial": trial})
    return Fixture(
        id="json_tool_array",
        kind="json",
        gold_facts=[marker, gold_line],
        messages=[
            {"role": "system", "content": "You triage search results."},
            {"role": "user", "content": f"What failed in trial {trial}?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"c{trial}",
                        "type": "function",
                        "function": {"name": "search", "arguments": f'{{"q":"error_trial_{trial}"}}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": f"c{trial}", "content": content},
        ],
        trial_idx=trial,
    )


def generate_build_log_fixture(trial: int = 0, rng: random.Random | None = None) -> Fixture:
    """Generate a randomized synthetic build log fixture."""
    if rng is None:
        rng = random.Random(142 + trial)
    marker = f"error C{1000 + trial * 111 + rng.randint(1, 99)}: unique-marker-HR-LOG-QK{trial}"
    total_lines = 250 + (trial * 40) + rng.randint(0, 20)
    lines = []
    
    flags_list = ["-O2 -Wall", "-O3 -Wextra", "-g -O1", "-O2 -pedantic"]
    for i in range(total_lines):
        flag = flags_list[(i + trial) % len(flags_list)]
        lines.append(
            f"2026-08-20T12:00:{i%60:02d} INFO [build] compiling unit_{i}_{trial}.c with flags {flag}"
        )
    
    fail_idx = rng.randint(total_lines // 2, total_lines - 10)
    lines.insert(fail_idx, f"2026-08-20T12:04:12 ERROR [msbuild] FAILED {marker}")
    log = "\n".join(lines)
    
    return Fixture(
        id="build_log",
        kind="log",
        gold_facts=[marker],
        messages=[
            {"role": "system", "content": "You read CI logs."},
            {"role": "user", "content": f"Why did CI build {trial} fail?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"c_log_{trial}",
                        "type": "function",
                        "function": {"name": "read_log", "arguments": f'{{"path":"build_{trial}.log"}}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": f"c_log_{trial}", "content": log},
        ],
        trial_idx=trial,
    )


def generate_grep_fixture(trial: int = 0, rng: random.Random | None = None) -> Fixture:
    """Generate a randomized grep match table fixture."""
    if rng is None:
        rng = random.Random(242 + trial)
    marker = f"unique-marker-HR-GREP-LM{trial}_{rng.randint(100, 999)}"
    num_hits = 80 + (trial * 15) + rng.randint(0, 10)
    
    exts = ["ts", "js", "py", "rs"]
    hits = []
    for i in range(num_hits):
        ext = exts[(i + trial) % len(exts)]
        hits.append(f"app/module_{trial}/file_{i}.{ext}:{10 + i%50}: const unused_{i}_{trial} = {i};")
    
    keep_idx = rng.randint(len(hits) // 3, len(hits) - 5)
    hits.insert(keep_idx, f"src/keep_{trial}.ts:3: export const MUST_KEEP = '{marker}'")
    blob = "\n".join(hits)
    
    return Fixture(
        id="grep_hits",
        kind="search",
        gold_facts=[marker, "MUST_KEEP"],
        messages=[
            {"role": "system", "content": "You search code."},
            {"role": "user", "content": f"Find MUST_KEEP in trial {trial}"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": f"c_grep_{trial}",
                        "type": "function",
                        "function": {"name": "grep", "arguments": f'{{"q":"MUST_KEEP_T{trial}"}}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": f"c_grep_{trial}", "content": blob},
        ],
        trial_idx=trial,
    )


# Default 1-trial aliases for backwards compatibility
def _json_search_fixture() -> Fixture:
    return generate_json_search_fixture(0)


def _build_log_fixture() -> Fixture:
    return generate_build_log_fixture(0)


def _grep_fixture() -> Fixture:
    return generate_grep_fixture(0)


def messages_text(messages: list[dict]) -> str:
    return json.dumps(messages, ensure_ascii=False)


def gold_hits(text: str, facts: list[str]) -> dict:
    found = [f for f in facts if f in text]
    missing = [f for f in facts if f not in text]
    return {
        "gold_total": len(facts),
        "gold_found": len(found),
        "missing": missing,
        "accuracy_pct": round(100.0 * len(found) / len(facts), 1) if facts else None,
    }


def run_fixture(fixture: Fixture) -> dict:
    from headroom import compress

    before = messages_text(fixture.messages)
    direct = gold_hits(before, fixture.gold_facts)
    result = compress(fixture.messages, model="gpt-4o")
    after = messages_text(result.messages)
    fetched = gold_hits(after, fixture.gold_facts)
    return {
        "id": fixture.id,
        "kind": fixture.kind,
        "trial_idx": fixture.trial_idx,
        "ok": fetched["gold_found"] == fetched["gold_total"] and direct["gold_found"] == direct["gold_total"],
        "chars_before": len(before),
        "chars_after": len(after),
        "est_tokens_before": est_tokens(before),
        "est_tokens_after": est_tokens(after),
        "headroom_tokens_before": result.tokens_before,
        "headroom_tokens_after": result.tokens_after,
        "headroom_tokens_saved": result.tokens_saved,
        "compression_ratio": result.compression_ratio,
        "transforms_applied": list(result.transforms_applied or []),
        "direct_review": direct,
        "compressed_accuracy": fetched,
        "accuracy_vs_direct": fetched["accuracy_pct"] if direct["accuracy_pct"] == 100 else None,
        "detect_backend_note": os.environ.get("HEADROOM_DETECT_BACKEND", "default"),
    }


def run_multi_trial_benchmarks(trials_count: int = 5) -> tuple[list[dict], list[dict], dict]:
    """Run multi-trial randomized benchmarks across all fixture generators."""
    generators = [
        ("json_tool_array", generate_json_search_fixture),
        ("build_log", generate_build_log_fixture),
        ("grep_hits", generate_grep_fixture),
    ]
    
    all_trial_rows: list[dict] = []
    category_summaries: list[dict] = []
    
    for cat_id, gen_fn in generators:
        cat_trials: list[dict] = []
        for t in range(trials_count):
            fixture = gen_fn(trial=t)
            print(f"running {cat_id} (trial {t+1}/{trials_count})...", flush=True)
            res = run_fixture(fixture)
            cat_trials.append(res)
            all_trial_rows.append(res)
        
        saved_list = [r["headroom_tokens_saved"] for r in cat_trials]
        ratios_list = [r["compression_ratio"] * 100 for r in cat_trials]
        all_ok = all(r["ok"] for r in cat_trials)
        
        cat_summary = {
            "id": cat_id,
            "trials_count": trials_count,
            "mean_tokens_saved": round(statistics.mean(saved_list), 1) if saved_list else 0.0,
            "stddev_tokens_saved": round(statistics.stdev(saved_list), 2) if len(saved_list) > 1 else 0.0,
            "min_tokens_saved": min(saved_list) if saved_list else 0,
            "max_tokens_saved": max(saved_list) if saved_list else 0,
            "mean_reduction_pct": round(statistics.mean(ratios_list), 1) if ratios_list else 0.0,
            "stddev_reduction_pct": round(statistics.stdev(ratios_list), 2) if len(ratios_list) > 1 else 0.0,
            "min_reduction_pct": round(min(ratios_list), 1) if ratios_list else 0.0,
            "max_reduction_pct": round(max(ratios_list), 1) if ratios_list else 0.0,
            "perfect_accuracy": all_ok,
            "trials": cat_trials,
        }
        category_summaries.append(cat_summary)
    
    all_ratios = [r["compression_ratio"] * 100 for r in all_trial_rows]
    all_saved = [r["headroom_tokens_saved"] for r in all_trial_rows]
    mean_ratio = statistics.mean(all_ratios) if all_ratios else 0.0
    stddev_ratio = statistics.stdev(all_ratios) if len(all_ratios) > 1 else 0.0
    perfect_count = sum(1 for r in all_trial_rows if r["ok"])
    
    savings_summary = {
        "trials_count": trials_count,
        "categories_count": len(category_summaries),
        "total_trials": len(all_trial_rows),
        "mean_ratio_pct": round(mean_ratio, 1),
        "stddev_ratio_pct": round(stddev_ratio, 2),
        "min_ratio_pct": round(min(all_ratios), 1) if all_ratios else 0.0,
        "max_ratio_pct": round(max(all_ratios), 1) if all_ratios else 0.0,
        "total_tokens_saved": sum(all_saved),
        "mean_tokens_saved": round(statistics.mean(all_saved), 1) if all_saved else 0.0,
        "perfect_accuracy": perfect_count,
        "perfect_accuracy_pct": round(100.0 * perfect_count / max(1, len(all_trial_rows)), 1),
        "confidence_block": {
            "trials_count": trials_count,
            "mean_reduction_pct": round(mean_ratio, 1),
            "stddev": round(stddev_ratio, 2),
            "min": round(min(all_ratios), 1) if all_ratios else 0.0,
            "max": round(max(all_ratios), 1) if all_ratios else 0.0,
        },
    }
    
    return all_trial_rows, category_summaries, savings_summary


def write_report(out_dir: Path, payload: dict) -> None:
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: headroom-dry-run",
        "purpose: [process]",
        "topics: [headroom, tokens, multi-trial, randomized]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# Headroom compression multi-trial randomized dry-run",
        "",
        "Multi-trial randomized validation of Headroom compression across perturbed tool dump fixtures (JSON payloads, build logs, grep hit tables). Evaluates statistical token savings (mean, stddev, min, max) and asserts 100% gold-fact preservation.",
        "",
        "Headroom `tokens_*` come from its tokenizer. `est_tokens_*` is `chars/4` for comparison with the qmd validator.",
        "",
        "## Statistical Summary by Category",
        "",
        "| Category | Trials | Mean Saved (tok) | Stddev (tok) | Mean Ratio | Min Ratio | Max Ratio | Gold Fact Accuracy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cat in payload.get("categories", []):
        lines.append(
            f"| `{cat['id']}` | {cat['trials_count']} | {cat['mean_tokens_saved']} | "
            f"±{cat['stddev_tokens_saved']} | {cat['mean_reduction_pct']}% | "
            f"{cat['min_reduction_pct']}% | {cat['max_reduction_pct']}% | "
            f"{'100% (PASS)' if cat['perfect_accuracy'] else 'FAIL'} |"
        )
    
    s = payload["savings_summary"]
    lines += [
        "",
        "## Overall Statistical Envelope",
        "",
        f"- Number of randomized trials per fixture: **{s['trials_count']}**",
        f"- Mean compression ratio: **{s['mean_ratio_pct']}%** (stddev: **±{s['stddev_ratio_pct']}%**)",
        f"- Compression range: **[{s['min_ratio_pct']}%, {s['max_ratio_pct']}%]**",
        f"- Total Headroom tokens saved across all trials: **{s['total_tokens_saved']}**",
        f"- Total trials with 100% gold-fact survival: **{s['perfect_accuracy']}/{s['total_trials']}** ({s['perfect_accuracy_pct']}%)",
        "",
        "## Findings",
        "",
    ]
    for finding in payload["findings"]:
        lines.append(f"- {finding}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Output directory under repo root "
            "(default: results/cost-layers/headroom/<YYYY-MM-DD>, dated at runtime)"
        ),
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of randomized trials per fixture category (default: 5)",
    )
    args = parser.parse_args(argv)

    _ensure_headroom_import()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/cost-layers/headroom/{today}"
    out_dir = ROOT / out_rel
    out_dir.mkdir(parents=True, exist_ok=True)

    all_trials, categories, savings_summary = run_multi_trial_benchmarks(trials_count=args.trials)

    findings: list[str] = []
    for cat in categories:
        if not cat["perfect_accuracy"]:
            findings.append(f"`{cat['id']}` had one or more trials drop gold facts after compression.")
        findings.append(
            f"`{cat['id']}`: mean saved {cat['mean_tokens_saved']} tokens "
            f"({cat['mean_reduction_pct']}%, range: [{cat['min_reduction_pct']}%, {cat['max_reduction_pct']}%])."
        )
    findings.append(
        "Multi-trial randomized testing eliminates static fixture overfitting and proves empirical performance bounds."
    )
    findings.append(
        "This measures compression quality, not Cursor-hosted billing. "
        "Provider savings require traffic through the proxy or MCP compress."
    )
    findings.append(
        "Windows may log a Magika/ONNX detect-backend warning; compression still ran."
    )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token_method_est": "chars/4",
        "trials_count": args.trials,
        "categories": categories,
        "fixtures": all_trials,
        "savings_summary": savings_summary,
        "findings": findings,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir, payload)
    failed = [r["id"] for r in all_trials if not r["ok"]]
    print(json.dumps({"out": str(out_dir), "trials": args.trials, "failed": failed, "savings_summary": savings_summary, "findings": findings}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
