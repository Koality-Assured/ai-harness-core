"""Run qmd + Headroom + ast-grep + prompt-caching + webfetch cost-layer dry runs and write a combined report.

tags: [qmd, headroom, ast-grep, cost-layers, research]
routing_hints: [validation, dry-run, tokens, cost-layers, prompt-caching, webfetch]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from tool_output import format_tool_execution  # noqa: E402


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
    # Child prints a JSON object last.
    text = proc.stdout.strip()
    start = text.rfind("{")
    if start != -1:
        try:
            payload["summary"] = json.loads(text[start:])
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
    parser.add_argument("--skip-hybrid", action="store_true", default=True)
    parser.add_argument("--hybrid", action="store_true", help="Also run slow hybrid qmd query")
    parser.add_argument("--skip-structured", action="store_true")
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
    qmd_dir = out / "qmd"
    hr_dir = out / "headroom"
    ast_dir = out / "ast-grep"
    pc_dir = out / "prompt-caching"
    wf_dir = out / "webfetch"

    results: dict = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "qmd": None,
        "headroom": None,
        "ast_grep": None,
        "prompt_caching": None,
        "webfetch": None,
    }
    exit_code = 0

    if not args.skip_qmd:
        extra = ["--out", str(qmd_dir.relative_to(ROOT)).replace("\\", "/")]
        if args.hybrid:
            pass
        else:
            extra.append("--skip-hybrid")
        if args.skip_structured:
            extra.append("--skip-structured")
        print("running qmd/validate_qmd_retrieval.py...", flush=True)
        code, payload = run_script("qmd/validate_qmd_retrieval.py", extra)
        results["qmd"] = payload
        if code != 0:
            exit_code = 1

    if not args.skip_headroom:
        extra = ["--out", str(hr_dir.relative_to(ROOT)).replace("\\", "/")]
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
        extra = ["--dry-run"]
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

    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: cost-layer-dry-run",
        "purpose: [process]",
        "topics: [qmd, headroom, ast-grep, prompt-caching, webfetch, tokens]",
        f"generated_at_utc: {results['generated_at_utc']}",
        "---",
        "",
        "# Cost-layer dry-run (qmd + Headroom + ast-grep + prompt-caching + webfetch)",
        "",
        "Combined validation of retrieval context savings (qmd), tool-dump compression (Headroom), ast-grep precision retrieval, prompt cache prefix invariance, and local web distillation token reduction versus uncompressed originals.",
        "",
        "## How to re-run",
        "",
        "```bash",
        "python scripts/cost-layers/validate_cost_layers.py",
        "# default: results/cost-layers/combined/<YYYY-MM-DD>/",
        "```",
        "",
        "Add `--hybrid` to include slow `qmd query`. Flags: `--skip-ast-grep`, `--skip-prompt-caching`, `--skip-webfetch`. Reports: `qmd/report.md`, `headroom/report.md`, `ast-grep/report.md`, `prompt-caching/report.md`.",
        "",
        "## qmd",
        "",
        f"- Exit: **{results['qmd']['exit_code'] if results['qmd'] else 'skipped'}**",
        f"- Health failures: {qmd_findings.get('health_fail') or []}",
        "",
        "## Headroom",
        "",
        f"- Exit: **{results['headroom']['exit_code'] if results['headroom'] else 'skipped'}**",
        f"- Failed fixtures: {hr_findings.get('failed') or []}",
        "",
        "## ast-grep",
        "",
        f"- Exit: **{results['ast_grep']['exit_code'] if results['ast_grep'] else 'skipped'}**",
        f"- Failed fixtures: {ast_findings.get('failed') or []}",
        "",
        "## Prompt Cache Invariance",
        "",
        f"- Exit: **{results['prompt_caching']['exit_code'] if results['prompt_caching'] else 'skipped'}**",
        f"- Violations: {pc_findings.get('violations_count', 0)}",
        f"- Audited files: {pc_findings.get('files_checked', 0)}",
        "",
        "## Web Distillation (local_webfetch)",
        "",
        f"- Exit: **{results['webfetch']['exit_code'] if results['webfetch'] else 'skipped'}**",
        f"- Extractor: `{wf_summary.get('extractor', 'n/a')}`",
        f"- Token reduction: **{wf_summary.get('reduction_pct', 0)}%** (Saved {wf_summary.get('est_tokens_saved', 0)} tokens)",
        f"- Gold fact accuracy: **{wf_summary.get('gold_accuracy_pct', 0)}%** ({wf_summary.get('gold_facts_retained', 0)}/{wf_summary.get('gold_facts_total', 0)})",
        "",
        "## Combined findings",
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
            f"- (webfetch) Distillation achieved {wf_summary.get('reduction_pct')}% token reduction with {wf_summary.get('gold_accuracy_pct')}% gold fact retention using {wf_summary.get('extractor')}."
        )

    lines += [
        "",
        "## Patterns / adjustments",
        "",
        "- BM25 `qmd search` is the Critical discovery path; structured `lex`/`vec` without rerank can miss the owning file (gold facts then fail vs direct review).",
        "- Path hits are not enough — gold-fact checks compare fetched file text to a direct read of the expected paths.",
        "- Vague queries like “where do Cloudflare tool patterns live” can rank `supporting/AGENTS.md` instead of `supporting/cloudflare/pages-wrangler.md`. Distinctive tokens from the owning page (`wrangler pages deploy`) hit it; extra words not in the file (`tool`) AND-zero BM25.",
        "- Headroom JSON arrays compress well (~70%+). Search-style dumps may drop path-only markers; keep gold facts in match text. Short compile listings may not trigger the log compressor.",
        "- Headroom savings do not apply to hosts that do not route through the proxy unless BYOK, custom base URL, or MCP compress.",
        "- ast-grep is precision retrieval + a structural oracle, not a third compressor. YAML frontmatter uses `-k block_mapping_pair` (JSON uses `-k pair`).",
        "- Prompt cache invariance ensures system prompt headers remain byte-stable across calls, preserving provider KV-cache hits (saving 90% input costs).",
        "- Local web distillation purifies raw external HTML into clean Markdown, neutralizing hidden prompt injections and stripping boilerplate (navbars, tracking pixels, ads).",
        "- Re-index after new Markdown or qmd health `docs_index_current` fails.",
        "- Root “Ambiguity gate” cited from isolation docs/skills is expected, not index leakage.",
        "",
    ]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "exit_code": exit_code}, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
