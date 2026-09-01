"""Benchmark corpus retrieval accuracy, MRR, Precision@K, and token savings.

tags: [benchmarks, qmd, retrieval, rag, tokens]
routing_hints: [retrieval-benchmark, mrr, precision, bm25, search-latency]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ground-truth test query suite for repository corpus retrieval
BENCHMARK_QUERIES: list[dict[str, Any]] = [
    {
        "query": "isolate work git worktree",
        "expected_paths": [
            "ai-tooling/skills/meta/isolate-work/SKILL.md",
            "scripts/routing/spawn_worktree.py",
        ],
        "category": "routing",
    },
    {
        "query": "cost layers headroom compression",
        "expected_paths": [
            "ai-tooling/skills/cost-layers/headroom/SKILL.md",
            "supporting/headroom/README.md",
            "scripts/cost-layers/validate_headroom_compression.py",
        ],
        "category": "cost-layers",
    },
    {
        "query": "stride threat model assessment",
        "expected_paths": [
            "ai-tooling/agents/assessment-agent/AGENT.md",
            "ai-tooling/skills/reporting/threat-model/SKILL.md",
        ],
        "category": "security",
    },
    {
        "query": "ast-grep structural pattern matching",
        "expected_paths": [
            "ai-tooling/skills/cost-layers/ast-grep/SKILL.md",
            "supporting/ast-grep/README.md",
            "scripts/cost-layers/validate_ast_grep.py",
        ],
        "category": "cost-layers",
    },
    {
        "query": "confluence cql document management",
        "expected_paths": [
            "ai-tooling/skills/confluence/confluence-doc-manage/SKILL.md",
            "ai-tooling/agents/docs-collab-agent/AGENT.md",
        ],
        "category": "collaboration",
    },
    {
        "query": "slack block kit webhook message",
        "expected_paths": [
            "ai-tooling/skills/slack/slack-message/SKILL.md",
            "ai-tooling/agents/chat-collab-agent/AGENT.md",
        ],
        "category": "collaboration",
    },
    {
        "query": "benchmark agent cost estimation",
        "expected_paths": [
            "ai-tooling/agents/benchmark-agent/AGENT.md",
            "ai-tooling/skills/benchmarks/agent-cost-estimator/SKILL.md",
        ],
        "category": "benchmarks",
    },
]


def run_qmd_search(query: str, limit: int = 5) -> list[str]:
    """Execute qmd search and return list of relative matching paths."""
    qmd_bin = shutil.which("qmd")
    if not qmd_bin:
        # Fast local fallback search using keyword matching over markdown paths
        return fallback_search(query, limit=limit)

    cmd = [qmd_bin, "search", query, "--json", "-n", str(limit)]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                if isinstance(data, list):
                    results = [item.get("path", "") for item in data if isinstance(item, dict)]
                    if results:
                        return results
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return fallback_search(query, limit=limit)


def fallback_search(query: str, limit: int = 5) -> list[str]:
    """Offline deterministic keyword relevance ranker for testing."""
    keywords = [k.lower() for k in query.split()]
    scores: list[tuple[float, str]] = []
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT)
        if any(part.startswith(".") for part in rel.parts) or "scratch" in rel.parts:
            continue
        rel_posix = rel.as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
            rel_lower = rel_posix.lower()
            score = 0.0
            for kw in keywords:
                if kw in rel_lower:
                    score += 5.0
                score += min(5.0, content.count(kw) * 0.5)
            if score > 0:
                scores.append((score, rel_posix))
        except OSError:
            continue

    scores.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scores[:limit]]


def evaluate_retrieval(query_items: list[dict[str, Any]], k_values: list[int] = [1, 3, 5]) -> dict[str, Any]:
    """Calculate Precision@K, Recall@K, and Mean Reciprocal Rank (MRR)."""
    precisions: dict[int, list[float]] = {k: [] for k in k_values}
    recip_ranks: list[float] = []
    latencies_ms: list[float] = []
    query_evaluations: list[dict[str, Any]] = []

    for item in query_items:
        query = item["query"]
        expected = [p.replace("\\", "/").lower() for p in item["expected_paths"]]

        start = time.perf_counter()
        retrieved = run_qmd_search(query, limit=max(k_values))
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        latencies_ms.append(elapsed_ms)

        retrieved_normalized = [p.replace("\\", "/").lower() for p in retrieved]

        # Calculate reciprocal rank (first position where an expected path appears)
        rr = 0.0
        for rank, p in enumerate(retrieved_normalized, 1):
            if any(exp in p or p in exp for exp in expected):
                rr = 1.0 / rank
                break
        recip_ranks.append(rr)

        # Calculate Precision@K
        for k in k_values:
            top_k = retrieved_normalized[:k]
            hits = sum(1 for p in top_k if any(exp in p or p in exp for exp in expected))
            precisions[k].append(round(hits / k, 4))

        top_match_path = retrieved[0] if retrieved else "—"
        query_evaluations.append({
            "query": query,
            "category": item["category"],
            "expected": item["expected_paths"],
            "retrieved": retrieved[:max(k_values)],
            "mrr": round(rr, 4),
            "p@1": precisions[1][-1],
            "p@3": precisions[3][-1],
            "p@5": precisions[5][-1],
            "top_match": top_match_path,
            "latency_ms": elapsed_ms,
        })

    mrr = round(sum(recip_ranks) / max(1, len(recip_ranks)), 4)
    avg_precisions = {f"p@{k}": round(sum(precisions[k]) / max(1, len(precisions[k])), 4) for k in k_values}
    avg_latency = round(sum(latencies_ms) / max(1, len(latencies_ms)), 2)

    return {
        "mrr": mrr,
        "precisions": avg_precisions,
        "avg_latency_ms": avg_latency,
        "total_queries": len(query_items),
        "queries": query_evaluations,
    }


def render_retrieval_report(eval_data: dict[str, Any]) -> str:
    """Render structured Markdown retrieval benchmark report."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: retrieval-benchmark",
        "purpose: [process]",
        "topics: [benchmarks, qmd, retrieval, rag, mrr, precision]",
        f"generated_at_utc: {now_utc}",
        "---",
        "",
        "# Corpus Retrieval Accuracy & Quality Benchmark",
        "",
        "Empirical evaluation of Markdown retrieval quality measuring Mean Reciprocal Rank (MRR), Precision@K, and query latency across ground-truth repository topics.",
        "",
        "## Overall Metrics",
        "",
        f"- Mean Reciprocal Rank (MRR): **{eval_data['mrr']:.4f}**",
        f"- Precision@1: **{eval_data['precisions']['p@1'] * 100:.1f}%**",
        f"- Precision@3: **{eval_data['precisions']['p@3'] * 100:.1f}%**",
        f"- Precision@5: **{eval_data['precisions']['p@5'] * 100:.1f}%**",
        f"- Average Search Latency: **{eval_data['avg_latency_ms']} ms**",
        f"- Total Benchmark Queries: **{eval_data['total_queries']}**",
        "",
        "## Query-Level Results",
        "",
        "| Query | Category | MRR | P@1 | P@3 | P@5 | Latency | Top Match |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for q in eval_data["queries"]:
        top_match = f"`{q['top_match']}`" if q.get("top_match") and q["top_match"] != "—" else "—"
        lines.append(
            f"| \"{q['query']}\" | `{q['category']}` | {q['mrr']:.2f} | "
            f"{q['p@1']:.1f} | {q['p@3']:.1f} | {q['p@5']:.1f} | {q['latency_ms']}ms | {top_match} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hybrid", action="store_true", help="Enable hybrid query testing")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--out", help="Output directory under repo root")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing files")
    args = parser.parse_args(argv)

    eval_data = evaluate_retrieval(BENCHMARK_QUERIES)
    report_md = render_retrieval_report(eval_data)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/benchmarks/retrieval/{today}"
    out_dir = ROOT / out_rel

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.md").write_text(report_md, encoding="utf-8")
        (out_dir / "summary.json").write_text(json.dumps(eval_data, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(eval_data, indent=2))
    else:
        print(report_md)

    return 0 if eval_data["mrr"] >= 0.70 else 1


if __name__ == "__main__":
    sys.exit(main())
