"""Dry-run ast-grep precision retrieval and Headroom structural-fact survival.

tags: [qmd, headroom, ast-grep]
routing_hints: [validation, dry-run, tokens, structural-facts]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from ast_grep import AstGrepError, find_ast_grep, run_ast_grep  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_ast_facts import (  # noqa: E402
    extract_agent_cards,
    extract_scripts,
    extract_skills_frontmatter,
)
from validate_headroom_compression import (  # noqa: E402
    CHARS_PER_TOKEN,
    _ensure_headroom_import,
    est_tokens,
    gold_hits,
    messages_text,
)

SAMPLES = [
    {
        "id": "python-script",
        "area": "scripts",
        "path": "scripts/cost-layers/validate_headroom_compression.py",
    },
    {
        "id": "agent-card-yaml",
        "area": "agent-cards",
        "path": "ai-tooling/agents/ai-tooling-ops/AGENT.md",
    },
    {
        "id": "skill-frontmatter",
        "area": "skills-frontmatter",
        "path": "ai-tooling/skills/script-builder/SKILL.md",
    },
]
MIN_GOLD_LEN = 6
MAX_GOLD_FACTS = 8


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def facts_for_file(all_facts: list[dict], rel: str) -> list[dict]:
    want = rel.replace("\\", "/")
    return [f for f in all_facts if f.get("file") == want]


def fact_blob(facts: list[dict]) -> str:
    lines = []
    for fact in facts:
        value = fact.get("value")
        snippet = fact.get("snippet") or ""
        if value:
            lines.append(f"{fact['kind']} {fact['name']}={value} {snippet}")
        else:
            lines.append(f"{fact['kind']} {fact['name']} {snippet}")
    return "\n".join(lines)


def gold_values(facts: list[dict]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        candidate = str(fact.get("value") or fact.get("name") or "").strip()
        if len(candidate) < MIN_GOLD_LEN or candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
        if len(out) >= MAX_GOLD_FACTS:
            break
    return out


def collect_sample_facts(root: Path) -> list[dict]:
    buckets = [
        extract_scripts(root),
        extract_agent_cards(root),
        extract_skills_frontmatter(root),
    ]
    facts: list[dict] = []
    for bucket in buckets:
        facts.extend(bucket)
    return facts


def retrieval_rows(root: Path, facts: list[dict]) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    failed: list[str] = []
    for sample in SAMPLES:
        rel = sample["path"]
        path = root / rel
        subset = facts_for_file(facts, rel)
        if not path.is_file():
            failed.append(sample["id"])
            rows.append({"id": sample["id"], "ok": False, "error": "missing file"})
            continue
        full = path.read_text(encoding="utf-8")
        blob = fact_blob(subset)
        before = est_tokens(full)
        after = est_tokens(blob) if blob else 0
        saved = max(0, before - after)
        ok = bool(subset) and after <= before
        if not ok:
            failed.append(sample["id"])
        rows.append(
            {
                "id": sample["id"],
                "path": rel,
                "ok": ok,
                "facts": len(subset),
                "chars_full": len(full),
                "chars_facts": len(blob),
                "est_tokens_full": before,
                "est_tokens_facts": after,
                "est_tokens_saved": saved,
                "savings_pct": round(100.0 * saved / before, 1) if before else None,
                "token_method_est": f"chars/{CHARS_PER_TOKEN:g}",
            }
        )
    return rows, failed


def headroom_structural_fixture(gold: list[str]) -> dict:
    rows = [{"id": i, "title": f"Result {i}", "snippet": "boilerplate field " * 20} for i in range(100)]
    for i, fact in enumerate(gold):
        rows.append(
            {
                "id": 9000 + i,
                "title": f"STRUCTURAL_KEEP {fact}",
                "snippet": f"must keep structural fact {fact}",
            }
        )
    content = json.dumps({"results": rows})
    messages = [
        {"role": "system", "content": "You triage structural search results."},
        {"role": "user", "content": "Which structural facts must be kept?"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "search", "arguments": '{"q":"STRUCTURAL_KEEP"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": content},
    ]
    return {"gold_facts": gold, "messages": messages}


def run_headroom_oracle(gold: list[str]) -> dict:
    from headroom import compress

    fixture = headroom_structural_fixture(gold)
    before = messages_text(fixture["messages"])
    direct = gold_hits(before, gold)
    result = compress(fixture["messages"], model="gpt-4o")
    after = messages_text(result.messages)
    fetched = gold_hits(after, gold)
    ok = fetched["gold_found"] == fetched["gold_total"] and direct["gold_found"] == direct["gold_total"]
    return {
        "id": "ast_structural_survival",
        "ok": ok,
        "skipped": False,
        "gold_facts": gold,
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
    }


def run_cli_health(root: Path) -> dict:
    import subprocess

    exe = find_ast_grep()
    ver = subprocess.run(
        [str(exe), "--version"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        shell=False,
    )
    version = (ver.stdout or ver.stderr or "").strip()
    sgconfig = root / "sgconfig.yml"
    scan = run_ast_grep(
        [
            "scan",
            "--json=compact",
            "--filter",
            "python-function-defs|python-class-defs|agent-card-json-pairs",
            "scripts/cost-layers",
            "ai-tooling/a2a/agent-cards",
        ],
        cwd=root,
        timeout=90,
        check=False,
    )
    scan_ok = isinstance(scan, list)
    ok = ver.returncode == 0 and sgconfig.is_file() and scan_ok
    return {
        "ok": ok,
        "exe": str(exe),
        "version": version,
        "sgconfig": sgconfig.is_file(),
        "scan_matches": len(scan) if scan_ok else 0,
        "version_exit": ver.returncode,
        "scan_ok": scan_ok,
    }


def write_report(out_dir: Path, payload: dict) -> None:
    hr = payload.get("headroom") or {}
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: ast-grep-dry-run",
        "purpose: [process]",
        "topics: [ast-grep, qmd, headroom, tokens]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# ast-grep cost-layer dry-run",
        "",
        "Precision retrieval (outline/kind facts vs full files) and Headroom survival of structural facts. Not a third compressor.",
        "",
        f"Token estimate is chars/{CHARS_PER_TOKEN:g}, same as the other cost-layer validators.",
        "",
        "## CLI health",
        "",
        f"- ast-grep: **{payload['health'].get('version') or 'missing'}**",
        f"- sgconfig.yml: **{payload['health'].get('sgconfig')}**",
        f"- scan: **{payload['health'].get('scan_ok')}** ({payload['health'].get('scan_matches')} matches in sample paths)",
        "",
        "## Precision retrieval",
        "",
        "| Sample | Facts | Full tok | Fact tok | Saved | % |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["retrieval"]:
        lines.append(
            f"| `{row['id']}` | {row.get('facts', 0)} | {row.get('est_tokens_full', '')} | "
            f"{row.get('est_tokens_facts', '')} | {row.get('est_tokens_saved', '')} | "
            f"{row.get('savings_pct', '')}% |"
        )
    lines += ["", "## Headroom structural oracle", ""]
    if hr.get("skipped"):
        lines.append(f"- Skipped: {hr.get('reason') or 'Headroom unavailable'}")
    else:
        c = hr.get("compressed_accuracy") or {}
        lines.append(
            f"- Fixture `{hr.get('id')}`: gold {c.get('gold_found')}/{c.get('gold_total')} "
            f"after compress; Headroom saved {hr.get('headroom_tokens_saved')} tokens "
            f"({round((hr.get('compression_ratio') or 0) * 100, 1)}%)."
        )
    lines += ["", "## Findings", ""]
    for finding in payload["findings"]:
        lines.append(f"- {finding}")
    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="results/ast-grep-dry-run",
        help="Output directory under repo root",
    )
    parser.add_argument(
        "--skip-headroom",
        action="store_true",
        help="Skip Headroom survival oracle (retrieval + CLI still run)",
    )
    args = parser.parse_args(argv)

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    findings: list[str] = []
    failed: list[str] = []

    try:
        health = run_cli_health(ROOT)
    except AstGrepError as exc:
        health = {"ok": False, "error": str(exc)}
        failed.append("cli")
        findings.append(f"CLI health failed: {exc}")
    else:
        if not health["ok"]:
            failed.append("cli")
            findings.append("CLI health failed (version, sgconfig.yml, or scan).")
        else:
            findings.append(f"CLI ok: {health.get('version')} ; scan matched {health.get('scan_matches')} nodes.")

    retrieval: list[dict] = []
    gold: list[str] = []
    try:
        facts = collect_sample_facts(ROOT)
        retrieval, retrieval_failed = retrieval_rows(ROOT, facts)
        failed.extend(retrieval_failed)
        for row in retrieval:
            if row.get("ok"):
                findings.append(
                    f"`{row['id']}` saved {row['est_tokens_saved']} est tokens "
                    f"({row['savings_pct']}% vs full file)."
                )
            else:
                findings.append(f"`{row['id']}` precision retrieval fixture failed.")
        for sample in SAMPLES:
            gold.extend(gold_values(facts_for_file(facts, sample["path"])))
        gold = gold_values([{"name": g} for g in gold])
    except AstGrepError as exc:
        failed.append("retrieval")
        findings.append(f"Fact extraction failed: {exc}")

    headroom_row: dict = {"skipped": True, "ok": True, "reason": "not run"}
    if args.skip_headroom:
        headroom_row = {"skipped": True, "ok": True, "reason": "--skip-headroom"}
        findings.append("Headroom oracle skipped (--skip-headroom).")
    else:
        try:
            _ensure_headroom_import()
            if not gold:
                headroom_row = {
                    "skipped": False,
                    "ok": False,
                    "id": "ast_structural_survival",
                    "reason": "no gold facts long enough to assert",
                }
                failed.append("headroom")
                findings.append("Headroom oracle failed: no structural gold facts.")
            else:
                print("running ast_structural_survival...", flush=True)
                headroom_row = run_headroom_oracle(gold)
                if not headroom_row["ok"]:
                    failed.append("headroom")
                    missing = (headroom_row.get("compressed_accuracy") or {}).get("missing") or []
                    findings.append(f"Headroom dropped structural facts: {missing}.")
                else:
                    findings.append(
                        f"Headroom kept {len(gold)} structural facts; saved "
                        f"{headroom_row.get('headroom_tokens_saved')} tokens."
                    )
        except SystemExit as exc:
            headroom_row = {"skipped": True, "ok": True, "reason": str(exc)}
            findings.append("Headroom oracle skipped (cannot import headroom).")
        except Exception as exc:  # noqa: BLE001 — report oracle failures
            failed.append("headroom")
            headroom_row = {"skipped": False, "ok": False, "error": str(exc)}
            findings.append(f"Headroom oracle error: {exc}")

    payload = {
        "generated_at_utc": utc_now(),
        "token_method_est": f"chars/{CHARS_PER_TOKEN:g}",
        "health": health,
        "retrieval": retrieval,
        "headroom": headroom_row,
        "findings": findings,
        "failed": failed,
        "pass": not failed,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir, payload)
    summary = {"out": str(out_dir), "failed": failed, "findings": findings, "pass": not failed}
    print(json.dumps(summary, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
