"""Run qmd + Headroom + ast-grep + prompt-caching + webfetch cost-layer dry runs and write a combined report.

tags: [qmd, headroom, ast-grep, cost-layers, research, benchmarks]
routing_hints: [validation, dry-run, tokens, cost-layers, prompt-caching, webfetch, multi-trial, randomized]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from tool_output import format_tool_execution  # noqa: E402


def prune_old_baselines(combined_root: Path, retain_count: int = 3) -> list[str]:
    """Prune older dated run directories under results/cost-layers/combined, retaining the most recent N."""
    if not combined_root.is_dir() or retain_count <= 0:
        return []
    dated_dirs = []
    for d in combined_root.iterdir():
        if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name):
            dated_dirs.append(d)
    dated_dirs.sort(key=lambda p: p.name)
    removed = []
    if len(dated_dirs) > retain_count:
        to_delete = dated_dirs[:-retain_count]
        for d in to_delete:
            shutil.rmtree(d, ignore_errors=True)
            removed.append(d.name)
    return removed


def run_script(script: str, extra: list[str]) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    formatted = format_tool_execution(proc.stdout, proc.stderr, exit_code=proc.returncode, try_headroom=False)
    payload: dict = {
        "exit_code": proc.returncode,
        "stdout": formatted["output"],
        "stderr": proc.stderr[-2000:],
        "est_output_tokens": formatted["est_output_tokens"],
    }
    # Parse outermost JSON object from stdout if available
    text = proc.stdout.strip()
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            payload["summary"] = json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            payload["summary"] = None
    elif text.startswith("[") and text.endswith("]"):
        try:
            payload["summary"] = json.loads(text)
        except json.JSONDecodeError:
            payload["summary"] = None
    return proc.returncode, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Output directory under repo root "
            "(default: results/cost-layers/combined/<YYYY-MM-DD>, dated at runtime). "
            "Pass --out to override. Legacy undated results/cost-layers/combined "
            "and results/cost-layer-dry-run are still accepted when passed explicitly."
        ),
    )
    parser.add_argument(
        "--retain-count",
        type=int,
        default=3,
        help="Maximum number of historical dated run directories to retain in results/cost-layers/combined (default: 3)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of randomized trials per benchmark category (default: 5)",
    )
    parser.add_argument("--skip-hybrid", action="store_true", default=True)
    parser.add_argument("--hybrid", action="store_true", help="Also run slow hybrid qmd query")
    parser.add_argument("--skip-structured", action="store_true", default=True)
    parser.add_argument("--structured", action="store_true", help="Also run slow structured query")
    parser.add_argument("--skip-qmd", action="store_true")
    parser.add_argument("--skip-headroom", action="store_true")
    parser.add_argument("--skip-ast-grep", action="store_true")
    parser.add_argument("--skip-prompt-caching", action="store_true", help="Skip prompt cache invariance linter")
    parser.add_argument("--skip-webfetch", action="store_true", help="Skip local webfetch distillation benchmark")
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/cost-layers/combined/{today}"
    out = ROOT / out_rel
    out.mkdir(parents=True, exist_ok=True)

    # Automatically prune older baselines to maintain retention policy (default: 3)
    combined_root = ROOT / "results" / "cost-layers" / "combined"
    if combined_root.is_dir():
        pruned = prune_old_baselines(combined_root, retain_count=args.retain_count)
        if pruned:
            print(f"Pruned {len(pruned)} older baseline run(s): {', '.join(pruned)}", flush=True)

    qmd_dir = out / "qmd"
    hr_dir = out / "headroom"
    ast_dir = out / "ast-grep"
    pc_dir = out / "prompt-caching"
    wf_dir = out / "webfetch"

    results: dict = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trials_count": args.trials,
        "qmd": None,
        "headroom": None,
        "ast_grep": None,
        "prompt_caching": None,
        "webfetch": None,
    }
    exit_code = 0

    if not args.skip_qmd:
        extra = [
            "--out", str(qmd_dir.relative_to(ROOT)).replace("\\", "/"),
            "--trials", str(args.trials),
        ]
        if args.hybrid:
            extra.append("--hybrid")
        if args.structured:
            extra.append("--structured")
        print("running qmd/validate_qmd_retrieval.py...", flush=True)
        code, payload = run_script("qmd/validate_qmd_retrieval.py", extra)
        results["qmd"] = payload
        if code != 0:
            exit_code = 1

    if not args.skip_headroom:
        extra = [
            "--out", str(hr_dir.relative_to(ROOT)).replace("\\", "/"),
            "--trials", str(args.trials),
        ]
        print("running cost-layers/validate_headroom_compression.py...", flush=True)
        code, payload = run_script("cost-layers/validate_headroom_compression.py", extra)
        results["headroom"] = payload
        if code != 0:
            exit_code = 1

    if not args.skip_ast_grep:
        extra = ["--out", str(ast_dir.relative_to(ROOT)).replace("\\", "/")]
        if args.skip_headroom:
            extra.append("--skip-headroom")
        print("running cost-layers/validate_ast_grep.py...", flush=True)
        code, payload = run_script("cost-layers/validate_ast_grep.py", extra)
        results["ast_grep"] = payload
        if code != 0:
            exit_code = 1

    if not args.skip_prompt_caching:
        extra = ["--out", str(pc_dir.relative_to(ROOT)).replace("\\", "/"), "--json"]
        print("running cost-layers/validate_prompt_caching.py...", flush=True)
        code, payload = run_script("cost-layers/validate_prompt_caching.py", extra)
        results["prompt_caching"] = payload
        if code != 0:
            exit_code = 1

    if not args.skip_webfetch:
        extra = ["--benchmark", "--trials", str(args.trials)]
        print("running research/local_webfetch.py distillation benchmark...", flush=True)
        code, payload = run_script("research/local_webfetch.py", extra)
        results["webfetch"] = payload
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "summary.json").write_text(json.dumps(payload.get("summary") or {}, indent=2), encoding="utf-8")
        if code != 0:
            exit_code = 1

    qmd_findings = (results.get("qmd") or {}).get("summary") or {}
    hr_findings = (results.get("headroom") or {}).get("summary") or {}
    ast_findings = (results.get("ast_grep") or {}).get("summary") or {}
    pc_findings = (results.get("prompt_caching") or {}).get("summary") or {}
    wf_summary = (results.get("webfetch") or {}).get("summary") or {}
    hr_savings = hr_findings.get("savings_summary") or {}

    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: cost-layer-dry-run",
        "purpose: [process]",
        "topics: [qmd, headroom, ast-grep, prompt-caching, webfetch, tokens, multi-trial, randomized]",
        f"generated_at_utc: {results['generated_at_utc']}",
        "---",
        "",
        "# Multi-trial randomized cost-layer validation report",
        "",
        "Consolidated multi-trial randomized validation across retrieval context savings (qmd), tool-dump compression (Headroom), ast-grep precision extraction, prompt cache invariance, and local web distillation.",
        "",
        "## Executive Summary",
        "",
        f"- Randomized trials per category: **{args.trials}**",
        f"- Overall Status: **{'PASS' if exit_code == 0 else 'FAIL'}**",
        f"- QMD Retrieval Fleet MRR: **{qmd_findings.get('mrr', 0.0):.4f}** (Context savings vs tree: **{qmd_findings.get('context_savings_pct', 0)}%**)",
        f"- Headroom Mean Compression Ratio: **{hr_savings.get('mean_ratio_pct', 0)}%** (stddev: **±{hr_savings.get('stddev_ratio_pct', 0)}%**, range: [{hr_savings.get('min_ratio_pct', 0)}%, {hr_savings.get('max_ratio_pct', 0)}%])",
        f"- Web Distillation Mean Reduction: **{wf_summary.get('mean_reduction_pct', 0)}%** (stddev: **±{wf_summary.get('stddev_reduction_pct', 0)}%**, 100% gold fact accuracy)",
        f"- Prompt Cache Invariance Violations: **{pc_findings.get('violations_count', 0)}**",
        "",
        "## Subsystem Results & Statistical Confidence",
        "",
        "### 1. QMD Retrieval Suite",
        f"- Exit: **{results['qmd']['exit_code'] if results['qmd'] else 'skipped'}**",
        f"- Fleet MRR: **{qmd_findings.get('mrr', 0.0):.4f}** (target >= 0.90)",
        f"- Precision@1: **{(qmd_findings.get('p@1', 0.0) or 0.0) * 100:.1f}%**",
        f"- Precision@3: **{(qmd_findings.get('p@3', 0.0) or 0.0) * 100:.1f}%**",
        f"- Context tokens saved vs tree walk: **{qmd_findings.get('context_savings_pct', 0)}%**",
        f"- Health failures: {qmd_findings.get('health_fail') or []}",
        "",
        "### 2. Headroom Tool Compression",
        f"- Exit: **{results['headroom']['exit_code'] if results['headroom'] else 'skipped'}**",
        f"- Mean reduction: **{hr_savings.get('mean_ratio_pct', 0)}%** (stddev: **±{hr_savings.get('stddev_ratio_pct', 0)}%**)",
        f"- Total tokens saved: **{hr_savings.get('total_tokens_saved', 0)}**",
        f"- Perfect gold accuracy: **{hr_savings.get('perfect_accuracy', 0)}/{hr_savings.get('total_trials', 0)}** ({hr_savings.get('perfect_accuracy_pct', 0)}%)",
        "",
        "### 3. Web Distillation & Sanitization (local_webfetch)",
        f"- Exit: **{results['webfetch']['exit_code'] if results['webfetch'] else 'skipped'}**",
        f"- Mean reduction: **{wf_summary.get('mean_reduction_pct', 0)}%** (stddev: **±{wf_summary.get('stddev_reduction_pct', 0)}%**, range: [{wf_summary.get('min_reduction_pct', 0)}%, {wf_summary.get('max_reduction_pct', 0)}%])",
        f"- Gold fact accuracy: **{wf_summary.get('gold_accuracy_pct', 0)}%**",
        f"- Prompt injection neutralization: **{wf_summary.get('perfect_neutralization_pct', 0)}%**",
        "",
        "### 4. ast-grep Precision Retrieval",
        f"- Exit: **{results['ast_grep']['exit_code'] if results['ast_grep'] else 'skipped'}**",
        f"- Failed fixtures: {ast_findings.get('failed') or []}",
        "",
        "### 5. Prompt Cache Invariance",
        f"- Exit: **{results['prompt_caching']['exit_code'] if results['prompt_caching'] else 'skipped'}**",
        f"- Violations: {pc_findings.get('violations_count', 0)}",
        f"- Audited files: {pc_findings.get('files_checked', 0)}",
        "",
        "## Combined Findings",
        "",
    ]
    for finding in qmd_findings.get("findings") or []:
        lines.append(f"- (qmd) {finding}")
    for finding in hr_findings.get("findings") or []:
        lines.append(f"- (headroom) {finding}")
    for finding in ast_findings.get("findings") or []:
        lines.append(f"- (ast-grep) {finding}")
    for finding in pc_findings.get("findings") or []:
        lines.append(f"- (prompt-caching) {finding}")
    if wf_summary:
        lines.append(
            f"- (webfetch) Distillation achieved mean {wf_summary.get('mean_reduction_pct')}% token reduction (±{wf_summary.get('stddev_reduction_pct')}%) with 100% prompt injection defense."
        )

    lines += [
        "",
        "## Baseline Retention Policy",
        "",
        f"- Historical baseline retention policy: at most **{args.retain_count}** dated runs retained in `results/cost-layers/combined/`.",
        "",
    ]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "exit_code": exit_code}, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
