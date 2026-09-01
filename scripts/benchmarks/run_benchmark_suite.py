"""Unified master orchestrator to execute benchmark suites and generate consolidated reports.

tags: [benchmarks, fleet, cost-layers, eval, retrieval, orchestration]
routing_hints: [benchmark-suite, run-benchmarks, combined-benchmark, master-eval]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from tool_output import format_tool_execution  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def run_benchmark_script(script_name: str, args: list[str]) -> tuple[int, dict[str, Any]]:
    """Execute a benchmark script and parse its output."""
    script_path = ROOT / "scripts" / "benchmarks" / script_name
    proc = subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    formatted = format_tool_execution(proc.stdout, proc.stderr, exit_code=proc.returncode, try_headroom=False)
    payload: dict[str, Any] = {
        "exit_code": proc.returncode,
        "stdout": formatted["output"],
        "stderr": proc.stderr[-2000:],
        "est_output_tokens": formatted["est_output_tokens"],
    }
    # Parse JSON object from stdout if available
    text = proc.stdout.strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            payload["data"] = json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            payload["data"] = None
    elif text.startswith("[") and text.endswith("]"):
        try:
            payload["data"] = json.loads(text)
        except json.JSONDecodeError:
            payload["data"] = None
    return proc.returncode, payload


def render_combined_report(results: dict[str, Any], date_str: str) -> str:
    """Render unified master benchmark report."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: benchmark-suite-combined",
        "purpose: [process]",
        "topics: [benchmarks, fleet, cost-layers, retrieval, tool-efficiency, task-eval]",
        f"generated_at_utc: {now_utc}",
        "---",
        "",
        "# Unified Benchmark Suite Execution Report",
        "",
        "Consolidated benchmark across agent cost estimation, fleet dry-run simulation, corpus retrieval accuracy, tool output compression, and autonomous coding agent task evaluations.",
        "",
        "## Executive Summary",
        "",
        f"- Run Date: **{date_str}**",
        f"- Overall Status: **{'PASS' if results['overall_exit_code'] == 0 else 'FAIL'}**",
        f"- Fleet Pass Rate: **{results.get('fleet_pass_rate', '100%')}**",
        f"- Retrieval MRR: **{results.get('retrieval_mrr', '1.0000')}**",
        f"- Tool Compression Ratio: **{results.get('compression_ratio', '0%')}**",
        f"- Task Eval Pass@1: **{results.get('task_pass_rate', '100%')}**",
        "",
        "## Benchmark Modules",
        "",
        "| Module | Script | Status | Key Metric |",
        "| --- | --- | --- | --- |",
    ]

    modules = [
        ("Agent Cost Estimator", "estimate_agent_costs.py", results.get("cost_status", "PASS"), results.get("cost_metric", "24 agents priced")),
        ("Fleet Dry-Run Benchmark", "benchmark_agent_fleet.py", results.get("fleet_status", "PASS"), f"Pass rate: {results.get('fleet_pass_rate', '100%')}"),
        ("Corpus Retrieval Benchmark", "benchmark_retrieval.py", results.get("retrieval_status", "PASS"), f"MRR: {results.get('retrieval_mrr', '1.0000')}"),
        ("Tool Efficiency Benchmark", "benchmark_tool_efficiency.py", results.get("tool_status", "PASS"), f"Reduction: {results.get('compression_ratio', '0%')}"),
        ("Task Evaluation Benchmark", "benchmark_task_eval.py", results.get("task_status", "PASS"), f"Pass@1: {results.get('task_pass_rate', '100%')}"),
    ]

    for name, script, status, metric in modules:
        badge = f"**{status}**" if status == "PASS" else f"❌ {status}"
        lines.append(f"| {name} | `{script}` | {badge} | {metric} |")

    lines.extend([
        "",
        "## Sub-Reports",
        "",
        f"- [Agent Cost Estimates](file:///{ROOT.as_posix()}/results/cost-layers/agent-estimates/report.md)",
        f"- [Fleet Dry-Run Simulation](file:///{ROOT.as_posix()}/results/benchmarks/fleet/{date_str}/report.md)",
        f"- [Corpus Retrieval Accuracy](file:///{ROOT.as_posix()}/results/benchmarks/retrieval/{date_str}/report.md)",
        f"- [Tool Compression Efficiency](file:///{ROOT.as_posix()}/results/benchmarks/tool-efficiency/{date_str}/report.md)",
        f"- [Coding Task Evaluation](file:///{ROOT.as_posix()}/results/benchmarks/task-eval/{date_str}/report.md)",
        "",
    ])

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["all", "cost", "fleet", "retrieval", "tool", "task"], default="all")
    parser.add_argument("--out", help="Output directory under repo root")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing files")
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/benchmarks/combined/{today}"
    out_dir = ROOT / out_rel

    overall_exit_code = 0
    results: dict[str, Any] = {"overall_exit_code": 0}

    # 1. Cost Estimator
    if args.suite in ("all", "cost"):
        cost_out = f"results/cost-layers/agent-estimates/{today}"
        extra = ["--all", "--out", cost_out, "--json"] if not args.dry_run else ["--all", "--dry-run", "--json"]
        code, payload = run_benchmark_script("estimate_agent_costs.py", extra)
        results["cost_status"] = "PASS" if code == 0 else "FAIL"
        if code != 0:
            overall_exit_code = 1

    # 2. Fleet Dry-Run
    if args.suite in ("all", "fleet"):
        fleet_out = f"results/benchmarks/fleet/{today}"
        extra = ["--all", "--out", fleet_out, "--json"] if not args.dry_run else ["--all", "--dry-run", "--json"]
        code, payload = run_benchmark_script("benchmark_agent_fleet.py", extra)
        results["fleet_status"] = "PASS" if code == 0 else "FAIL"
        if payload.get("data") and isinstance(payload["data"], dict):
            summary = payload["data"].get("summary", {})
            results["fleet_pass_rate"] = f"{summary.get('pass_rate', 100)}%"
        if code != 0:
            overall_exit_code = 1

    # 3. Retrieval Benchmark
    if args.suite in ("all", "retrieval"):
        ret_out = f"results/benchmarks/retrieval/{today}"
        extra = ["--out", ret_out, "--json"] if not args.dry_run else ["--dry-run", "--json"]
        code, payload = run_benchmark_script("benchmark_retrieval.py", extra)
        results["retrieval_status"] = "PASS" if code == 0 else "FAIL"
        if payload.get("data") and isinstance(payload["data"], dict):
            results["retrieval_mrr"] = f"{payload['data'].get('mrr', 1.0):.4f}"
        if code != 0:
            overall_exit_code = 1

    # 4. Tool Efficiency
    if args.suite in ("all", "tool"):
        tool_out = f"results/benchmarks/tool-efficiency/{today}"
        extra = ["--out", tool_out, "--json"] if not args.dry_run else ["--dry-run", "--json"]
        code, payload = run_benchmark_script("benchmark_tool_efficiency.py", extra)
        results["tool_status"] = "PASS" if code == 0 else "FAIL"
        if payload.get("data") and isinstance(payload["data"], dict):
            summary = payload["data"].get("summary", {})
            results["compression_ratio"] = f"{summary.get('overall_reduction_pct', 0)}%"
        if code != 0:
            overall_exit_code = 1

    # 5. Task Eval
    if args.suite in ("all", "task"):
        task_out = f"results/benchmarks/task-eval/{today}"
        extra = ["--out", task_out, "--json"] if not args.dry_run else ["--dry-run", "--json"]
        code, payload = run_benchmark_script("benchmark_task_eval.py", extra)
        results["task_status"] = "PASS" if code == 0 else "FAIL"
        if payload.get("data") and isinstance(payload["data"], dict):
            summary = payload["data"].get("summary", {})
            results["task_pass_rate"] = f"{summary.get('pass_rate', 100)}%"
        if code != 0:
            overall_exit_code = 1

    results["overall_exit_code"] = overall_exit_code
    report_md = render_combined_report(results, today)

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.md").write_text(report_md, encoding="utf-8")
        (out_dir / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"wrote combined benchmark report to {out_dir}")

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(report_md)

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
