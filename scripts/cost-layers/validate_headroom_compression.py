"""Dry-run Headroom compression: token savings vs gold-fact accuracy.

tags: [headroom, qmd]
routing_hints: [validation, dry-run, tokens, compression]
"""

from __future__ import annotations

import argparse
import json
import os
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


def _json_search_fixture() -> Fixture:
    marker = "FATAL unique-marker-HR-JSON-ZX9"
    rows = [{"id": i, "title": f"Result {i}", "snippet": "boilerplate field " * 20} for i in range(100)]
    rows.append({"id": 999, "title": marker, "snippet": "preserve this incident line"})
    content = json.dumps({"results": rows})
    return Fixture(
        id="json_tool_array",
        kind="json",
        gold_facts=[marker, "preserve this incident line"],
        messages=[
            {"role": "system", "content": "You triage search results."},
            {"role": "user", "content": "What failed?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q":"error"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": content},
        ],
    )


def _build_log_fixture() -> Fixture:
    marker = "error C1234: unique-marker-HR-LOG-QK7"
    lines = []
    for i in range(400):
        lines.append(f"2026-08-20T12:00:{i%60:02d} INFO [build] compiling unit_{i}.c with flags -O2 -Wall")
    lines.insert(300, f"2026-08-20T12:04:12 ERROR [msbuild] FAILED {marker}")
    log = "\n".join(lines)
    return Fixture(
        id="build_log",
        kind="log",
        gold_facts=[marker],
        messages=[
            {"role": "system", "content": "You read CI logs."},
            {"role": "user", "content": "Why did CI fail?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "read_log", "arguments": '{"path":"build.log"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": log},
        ],
    )


def _grep_fixture() -> Fixture:
    marker = "unique-marker-HR-GREP-LM2"
    hits = [f"app/file_{i}.ts:12: const unused_{i} = {i}" for i in range(120)]
    hits.append(f"src/keep.ts:3: export const MUST_KEEP = '{marker}'")
    blob = "\n".join(hits)
    return Fixture(
        id="grep_hits",
        kind="search",
        gold_facts=[marker, "MUST_KEEP"],
        messages=[
            {"role": "system", "content": "You search code."},
            {"role": "user", "content": "Find MUST_KEEP"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "grep", "arguments": '{"q":"MUST_KEEP"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": blob},
        ],
    )


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


def write_report(out_dir: Path, payload: dict) -> None:
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: headroom-dry-run",
        "purpose: [process]",
        "topics: [headroom, tokens]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# Headroom compression dry-run",
        "",
        "Compress bulky tool dumps locally (no provider call). Compare token savings and whether gold facts survive versus the uncompressed original (direct review).",
        "",
        "Headroom `tokens_*` come from its tokenizer. `est_tokens_*` is `chars/4` for comparison with the qmd validator.",
        "",
        "## Fixtures",
        "",
        "| Fixture | Saved (Headroom tok) | Ratio | Gold in original | Gold after compress | vs direct |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["fixtures"]:
        d = row["direct_review"]
        c = row["compressed_accuracy"]
        lines.append(
            f"| `{row['id']}` | {row['headroom_tokens_saved']} | "
            f"{round(row['compression_ratio'] * 100, 1)}% | "
            f"{d['gold_found']}/{d['gold_total']} | {c['gold_found']}/{c['gold_total']} | "
            f"{row['accuracy_vs_direct']}% |"
        )
    s = payload["savings_summary"]
    lines += [
        "",
        "## Savings summary",
        "",
        f"- Mean compression ratio: **{s['mean_ratio_pct']}%**",
        f"- Total Headroom tokens saved: **{s['total_tokens_saved']}**",
        f"- Fixtures with 100% gold-fact survival: **{s['perfect_accuracy']}/{s['fixture_count']}**",
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
    parser.add_argument("--out", default="results/headroom-dry-run", help="Output directory under repo root")
    args = parser.parse_args(argv)

    _ensure_headroom_import()
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    fixtures = [_json_search_fixture(), _build_log_fixture(), _grep_fixture()]
    rows = []
    for fixture in fixtures:
        print(f"running {fixture.id}...", flush=True)
        rows.append(run_fixture(fixture))

    ratios = [r["compression_ratio"] for r in rows]
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    perfect = sum(1 for r in rows if r["ok"])
    findings: list[str] = []
    for r in rows:
        if r["direct_review"]["missing"]:
            findings.append(f"`{r['id']}` gold facts missing from uncompressed original (bad fixture).")
        if r["compressed_accuracy"]["missing"]:
            findings.append(
                f"`{r['id']}` dropped gold facts after compress: {r['compressed_accuracy']['missing']}."
            )
        findings.append(
            f"`{r['id']}` saved {r['headroom_tokens_saved']} tokens "
            f"({round(r['compression_ratio'] * 100, 1)}%)."
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
        "fixtures": rows,
        "savings_summary": {
            "mean_ratio_pct": round(mean_ratio * 100, 1),
            "total_tokens_saved": sum(r["headroom_tokens_saved"] for r in rows),
            "perfect_accuracy": perfect,
            "fixture_count": len(rows),
        },
        "findings": findings,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir, payload)
    failed = [r["id"] for r in rows if not r["ok"]]
    print(json.dumps({"out": str(out_dir), "failed": failed, "findings": findings}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
