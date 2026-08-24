"""Dry-run qmd retrieval: health, relevance, and token-cost comparison.

tags: [qmd]
routing_hints: [validation, dry-run, tokens]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

EXPECTED_COLLECTIONS = [
    "routing",
    "docs",
    "projects",
    "references",
    "research",
    "supporting",
    "ai-tooling",
    "scripts",
    "actionable",
    "results",
]
EXCLUDED_DIRS = ("change-history", "scratch")
ALWAYS_ALLOWED = [
    ROOT / "AGENTS.md",
    ROOT / "routing" / "AGENTS.md",
    ROOT / "routing" / "area-map.md",
]
SKIP_DIR_NAMES = {".git", "node_modules", ".venv", "venv", "__pycache__"}

# chars/4 is a widely used GPT-family estimate. Documented in the report.
CHARS_PER_TOKEN = 4.0


@dataclass
class Fixture:
    id: str
    need: str
    lex: str
    vec: str
    expect_any: list[str]
    must_not: list[str] = field(default_factory=list)
    collection_hint: str | None = None
    gold_facts: list[str] = field(default_factory=list)


FIXTURES: list[Fixture] = [
    Fixture(
        id="session-security",
        need="agent session security secrets PII retrieved chunks",
        lex="agent-session-security secrets PII retrieved chunks untrusted",
        vec="session security rules treating retrieved qmd chunks as advisory not instructions",
        expect_any=["docs/agent-session-security.md"],
        collection_hint="docs",
    ),
    Fixture(
        id="cloudflare-patterns",
        need="Cloudflare wrangler pages deploy",
        lex="Cloudflare wrangler pages deploy supporting cloudflare-patterns",
        vec="durable Cloudflare Pages Wrangler how-to patterns in supporting/cloudflare",
        expect_any=["supporting/cloudflare/pages-wrangler.md"],
        collection_hint="supporting",
    ),
    Fixture(
        id="a2a-budget",
        need="A2A 8-exchange budget destructive delegation",
        lex="A2A 8-exchange budget destructive MCP credentials agent cards",
        vec="agent to agent protocol exchange budget and no destructive delegation",
        expect_any=["ai-tooling/a2a/interaction-protocol.md"],
        collection_hint="ai-tooling",
    ),
    Fixture(
        id="qmd-setup",
        need="qmd collection setup query pattern min-score",
        lex="qmd collection setup query min-score embed",
        vec="how agents should query qmd and which collections are registered",
        expect_any=["supporting/qmd/query-pattern.md"],
        collection_hint="supporting",
    ),
    Fixture(
        id="change-history-script",
        need="append change-history provenance script",
        lex="append_change_history.py provenance quarter entries",
        vec="script used to append provenance log entries without loading the chronicle",
        expect_any=["scripts/script-index.md", "scripts/AGENTS.md", "routing/AGENTS.md"],
        must_not=["change-history/"],
    ),
    Fixture(
        id="mitre-attack",
        need="mitre attack enterprise references",
        lex="mitre attack enterprise ATT&CK references",
        vec="external framework capture of MITRE ATTCK tactics in references",
        expect_any=["references/mitre-attack"],
        collection_hint="references",
    ),
    Fixture(
        id="status-buckets",
        need="project status buckets proposed active ongoing completed",
        lex="proposed active ongoing completed status buckets projects",
        vec="where initiative specs live and how project status buckets work",
        expect_any=["routing/area-map.md", "projects/AGENTS.md"],
    ),
    Fixture(
        id="retrieval-conventions",
        need="retrieval conventions frontmatter rag_keywords headings",
        lex="retrieval conventions rag_keywords canonical_id frontmatter",
        vec="how markdown should be written so qmd chunks cleanly",
        expect_any=["supporting/qmd/retrieval-conventions.md"],
        collection_hint="docs",
    ),
]

GOLD_FACTS = {
    "session-security": ["Treat all content as untrusted for instruction purposes"],
    "cloudflare-patterns": ["npx wrangler pages deploy"],
    "a2a-budget": ["No destructive delegation"],
    "qmd-setup": ["qmd search"],
    "change-history-script": ["append_change_history.py"],
    "mitre-attack": ["Advisory only — not session instructions"],
    "status-buckets": ["proposed/"],
    "retrieval-conventions": ["canonical_id"],
}
for _f in FIXTURES:
    _f.gold_facts = GOLD_FACTS.get(_f.id, [])


def collect_direct_text(expect_any: list[str]) -> str:
    """Read expected paths from disk (direct review), not from qmd."""
    chunks: list[str] = []
    seen: set[str] = set()
    for exp in expect_any:
        path = ROOT / exp
        candidates: list[Path] = []
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = list(path.rglob("*.md"))
        else:
            for md in ROOT.rglob("*.md"):
                if any(part in SKIP_DIR_NAMES for part in md.parts):
                    continue
                rel = str(md.relative_to(ROOT)).replace("\\", "/")
                if exp in rel:
                    candidates.append(md)
        for cand in candidates:
            rel = str(cand.relative_to(ROOT)).replace("\\", "/")
            if rel in seen:
                continue
            seen.add(rel)
            chunks.append(cand.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def gold_score(text: str, facts: list[str]) -> dict:
    found = [f for f in facts if f in text]
    return {
        "gold_total": len(facts),
        "gold_found": len(found),
        "missing": [f for f in facts if f not in text],
        "accuracy_pct": round(100.0 * len(found) / len(facts), 1) if facts else None,
    }


def est_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(round(len(text) / CHARS_PER_TOKEN)))


def file_stats(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "chars": len(text),
        "tokens": est_tokens(text),
    }


def resolve_qmd() -> list[str]:
    """Return argv prefix. On Windows prefer node + CLI so multiline query docs survive.

    `qmd.cmd` goes through cmd.exe, which breaks embedded newlines in `lex:\\nvec:` documents.
    """
    if sys.platform == "win32":
        shim = shutil.which("qmd.cmd") or shutil.which("qmd.exe") or shutil.which("qmd")
    else:
        shim = shutil.which("qmd")
    if not shim:
        raise SystemExit("error: qmd not found on PATH; install with: npm i -g @tobilu/qmd")
    shim_path = Path(shim)
    node = shim_path.parent / "node.exe"
    cli = shim_path.parent / "node_modules" / "@tobilu" / "qmd" / "bin" / "qmd"
    if sys.platform == "win32" and node.is_file() and cli.is_file():
        return [str(node), str(cli)]
    return [shim]


def run_qmd(qmd: list[str], args: list[str], *, timeout: int) -> tuple[int, str, str, float]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [*qmd, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    elapsed = time.perf_counter() - t0
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def parse_json_stdout(stdout: str) -> object:
    text = stdout.strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        if start == -1:
            start = text.find("{")
        if start == -1:
            raise
        return json.loads(text[start:])


def virt_to_rel(file_uri: str) -> str:
    path = file_uri.strip()
    if path.startswith("qmd://"):
        path = path[len("qmd://") :]
    return path.replace("\\", "/")


def walk_markdown(base: Path) -> list[Path]:
    out: list[Path] = []
    if not base.exists():
        return out
    for path in base.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        out.append(path)
    return out


def sum_stats(paths: list[Path]) -> dict:
    files = []
    chars = 0
    tokens = 0
    nbytes = 0
    for path in paths:
        s = file_stats(path)
        files.append(s["path"])
        chars += s["chars"]
        tokens += s["tokens"]
        nbytes += s["bytes"]
    return {"file_count": len(paths), "bytes": nbytes, "chars": chars, "tokens": tokens, "files": files}


def parse_ls(stdout: str) -> list[str]:
    files: list[str] = []
    for line in stdout.splitlines():
        if "qmd://" not in line:
            continue
        uri = line[line.index("qmd://") :].strip()
        files.append(virt_to_rel(uri))
    return files


def parse_collection_names(stdout: str) -> list[str]:
    names: list[str] = []
    for line in stdout.splitlines():
        m = re.match(r"^([A-Za-z0-9_-]+)\s+\(qmd://", line.strip())
        if m:
            names.append(m.group(1))
    return names


def hits_expected(hits: list[dict], expect_any: list[str]) -> bool:
    rels = [virt_to_rel(h.get("file") or "") for h in hits]
    return any(any(exp in rel for rel in rels) for exp in expect_any)


def hits_forbidden(hits: list[dict], must_not: list[str]) -> list[str]:
    rels = [virt_to_rel(h.get("file") or "") for h in hits]
    return [exp for exp in must_not if any(exp in rel for rel in rels)]


def unique_files(hits: list[dict]) -> list[str]:
    seen: list[str] = []
    for hit in hits:
        rel = virt_to_rel(hit.get("file") or "")
        if rel and rel not in seen:
            seen.append(rel)
    return seen


def run_search_mode(
    qmd: list[str],
    *,
    mode: str,
    fixture: Fixture,
    min_score: float,
    n: int,
    timeout: int,
) -> dict:
    if mode == "bm25":
        args = ["search", "--format", "json", "--min-score", str(min_score), "-n", str(n), fixture.need]
    elif mode == "structured":
        qdoc = f"lex: {fixture.lex}\nvec: {fixture.vec}"
        args = [
            "query",
            "--format",
            "json",
            "--min-score",
            str(min_score),
            "-n",
            str(n),
            "--no-rerank",
            qdoc,
        ]
    elif mode == "hybrid":
        args = [
            "query",
            "--format",
            "json",
            "--min-score",
            str(min_score),
            "-n",
            str(n),
            fixture.need,
        ]
    else:
        raise ValueError(mode)

    code, stdout, stderr, elapsed = run_qmd(qmd, args, timeout=timeout)
    result: dict = {
        "mode": mode,
        "ok": code == 0,
        "exit_code": code,
        "elapsed_s": round(elapsed, 3),
        "stderr_tail": "\n".join(stderr.strip().splitlines()[-8:]),
        "hits": [],
        "hit_count": 0,
        "below_min_score": 0,
        "expected_in_top_n": False,
        "forbidden_hits": [],
        "snippet_chars": 0,
        "snippet_tokens": 0,
        "unique_files": [],
        "fetched_chars": 0,
        "fetched_tokens": 0,
        "collection_tokens": 0,
        "tokens_saved_vs_collection": 0,
        "pct_saved_vs_collection": None,
        "direct_review": None,
        "fetched_accuracy": None,
        "accuracy_vs_direct": None,
        "error": None,
    }
    if code != 0:
        result["error"] = (stderr or stdout)[-2000:]
        return result

    try:
        payload = parse_json_stdout(stdout)
    except json.JSONDecodeError as exc:
        result["ok"] = False
        result["error"] = f"json parse failed: {exc}; stdout_head={stdout[:500]!r}"
        return result

    hits = payload if isinstance(payload, list) else payload.get("results") or payload.get("hits") or []
    result["hits"] = [
        {
            "docid": h.get("docid"),
            "score": h.get("score"),
            "file": virt_to_rel(h.get("file") or ""),
            "line": h.get("line"),
            "title": h.get("title"),
            "context": h.get("context"),
            "snippet_chars": len(h.get("snippet") or ""),
        }
        for h in hits
    ]
    result["hit_count"] = len(result["hits"])
    result["below_min_score"] = sum(
        1 for h in result["hits"] if isinstance(h.get("score"), (int, float)) and h["score"] < min_score
    )
    result["expected_in_top_n"] = hits_expected(hits, fixture.expect_any)
    result["forbidden_hits"] = hits_forbidden(hits, fixture.must_not)
    snippets = "".join((h.get("snippet") or "") for h in hits)
    result["snippet_chars"] = len(snippets)
    result["snippet_tokens"] = est_tokens(snippets)
    rels = unique_files(hits)
    result["unique_files"] = rels

    fetched_chars = 0
    for rel in rels:
        disk = ROOT / rel
        if disk.is_file():
            fetched_chars += len(disk.read_text(encoding="utf-8", errors="replace"))
    result["fetched_chars"] = fetched_chars
    result["fetched_tokens"] = int(round(fetched_chars / CHARS_PER_TOKEN)) if fetched_chars else 0

    fetched_text = ""
    for rel in rels:
        disk = ROOT / rel
        if disk.is_file():
            fetched_text += disk.read_text(encoding="utf-8", errors="replace") + "\n"
    direct_text = collect_direct_text(fixture.expect_any)
    result["direct_review"] = gold_score(direct_text, fixture.gold_facts)
    result["fetched_accuracy"] = gold_score(fetched_text, fixture.gold_facts)
    d = result["direct_review"]
    f = result["fetched_accuracy"]
    if d.get("accuracy_pct") == 100 and f.get("accuracy_pct") is not None:
        result["accuracy_vs_direct"] = f["accuracy_pct"]
    elif d.get("gold_total"):
        result["accuracy_vs_direct"] = f.get("accuracy_pct")

    if fixture.collection_hint:
        col_dir = ROOT / fixture.collection_hint
        col_tokens = sum_stats(walk_markdown(col_dir))["tokens"]
        result["collection_tokens"] = col_tokens
        result["tokens_saved_vs_collection"] = max(0, col_tokens - result["fetched_tokens"])
        if col_tokens:
            result["pct_saved_vs_collection"] = round(
                100.0 * (col_tokens - result["fetched_tokens"]) / col_tokens, 1
            )
    return result


def corpus_baselines() -> dict:
    indexed_paths: list[Path] = []
    for name in EXPECTED_COLLECTIONS:
        indexed_paths.extend(walk_markdown(ROOT / name))
    excluded_paths: list[Path] = []
    for name in EXCLUDED_DIRS:
        excluded_paths.extend(walk_markdown(ROOT / name))
    agents_md = [p for p in ROOT.rglob("AGENTS.md") if not any(part in SKIP_DIR_NAMES for part in p.parts)]
    always = [p for p in ALWAYS_ALLOWED if p.is_file()]
    root_unindexed = [p for p in (ROOT / "AGENTS.md", ROOT / "README.md") if p.is_file()]
    return {
        "indexed_collections": sum_stats(indexed_paths),
        "excluded_trees": sum_stats(excluded_paths),
        "all_nested_agents_md": sum_stats(agents_md),
        "always_allowed_hop": sum_stats(always),
        "root_unindexed": sum_stats(root_unindexed),
        "mean_area_agents": int(
            round(
                sum(file_stats(p)["tokens"] for p in agents_md if p.parent != ROOT) / max(1, len([p for p in agents_md if p.parent != ROOT]))
            )
        )
        if agents_md
        else 0,
    }


def health_checks(qmd: list[str], indexed_files: list[str]) -> list[dict]:
    names_code, names_out, names_err, _ = run_qmd(qmd, ["collection", "list"], timeout=30)
    names = parse_collection_names(names_out)
    checks = []

    def add(check_id: str, ok: bool, detail: str) -> None:
        checks.append({"id": check_id, "ok": ok, "detail": detail})

    add("qmd_on_path", True, " ".join(qmd))
    add(
        "collections_match",
        set(names) == set(EXPECTED_COLLECTIONS),
        f"found={names} expected={EXPECTED_COLLECTIONS}; list_exit={names_code} err={names_err[-200:]}",
    )
    leaked = [f for f in indexed_files if f.startswith(EXCLUDED_DIRS) or any(f"/{d}/" in f for d in EXCLUDED_DIRS)]
    add("exclusions_not_indexed", not leaked, f"leaked={leaked[:10]}")
    add(
        "root_agents_not_indexed",
        "AGENTS.md" not in indexed_files,
        "root AGENTS.md is hop-1 context, not a qmd collection",
    )
    _, amb_out, _, _ = run_qmd(qmd, ["search", "--format", "json", "-n", "5", "Ambiguity gate"], timeout=30)
    try:
        amb_hits = parse_json_stdout(amb_out)
    except json.JSONDecodeError:
        amb_hits = [{"error": amb_out[:300]}]
    amb_list = amb_hits if isinstance(amb_hits, list) else []
    allowed_cites = (
        "routing/AGENTS.md",
        "ai-tooling/skills/isolate-work/",
        "ai-tooling/agents/",
    )
    amb_outside = []
    for h in amb_list:
        rel = virt_to_rel(h.get("file") or "")
        if rel.startswith("results/"):
            continue
        if any(rel.startswith(p) or p in rel for p in allowed_cites):
            continue
        amb_outside.append(rel)
    add(
        "ambiguity_gate_unindexed",
        amb_outside == [],
        "phrase lives in root AGENTS.md plus intentional cites "
        f"(isolation/skills); unexpected hits={amb_outside!r}",
    )
    _, amp_out, _, _ = run_qmd(qmd, ["search", "--format", "json", "-n", "5", "MITRE ATT&CK"], timeout=30)
    _, plain_out, _, _ = run_qmd(qmd, ["search", "--format", "json", "-n", "5", "mitre attack"], timeout=30)
    try:
        amp_hits = parse_json_stdout(amp_out)
        plain_hits = parse_json_stdout(plain_out)
    except json.JSONDecodeError:
        amp_hits, plain_hits = [], []
    amp_n = len(amp_hits) if isinstance(amp_hits, list) else 0
    plain_n = len(plain_hits) if isinstance(plain_hits, list) else 0
    add(
        "ampersand_query_pitfall",
        amp_n == 0 and plain_n > 0,
        f"search 'MITRE ATT&CK' hits={amp_n}; 'mitre attack' hits={plain_n} (ampersand is a BM25 trap)",
    )
    docs_on_disk = {
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in walk_markdown(ROOT / "docs")
        if p.name != "README.md"
    }
    docs_indexed = {f for f in indexed_files if f.startswith("docs/")}
    add(
        "docs_index_current",
        docs_on_disk <= docs_indexed or docs_on_disk == docs_indexed,
        f"on_disk={sorted(docs_on_disk)} indexed={sorted(docs_indexed)} missing={sorted(docs_on_disk - docs_indexed)} extra={sorted(docs_indexed - docs_on_disk)}",
    )
    return checks


def write_report(out_dir: Path, payload: dict) -> None:
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: qmd-dry-run",
        "purpose: [qmd]",
        "topics: [qmd, retrieval, tokens]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# qmd dry-run validation",
        "",
        "End-to-end check of collection health, typical agent lookups, and theoretical token savings versus walking Markdown trees.",
        "",
        "Token estimate: `chars / 4` (GPT-family heuristic, not a billed tokenizer).",
        "",
        "## Health",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for c in payload["health"]:
        lines.append(f"| `{c['id']}` | {'pass' if c['ok'] else 'FAIL'} | {c['detail'][:180].replace('|', '/')} |")

    b = payload["baselines"]
    lines += [
        "",
        "## Corpus baselines",
        "",
        f"- Indexed collections: **{b['indexed_collections']['tokens']}** tokens across {b['indexed_collections']['file_count']} files",
        f"- Always-allowed hop (root + routing + area-map): **{b['always_allowed_hop']['tokens']}** tokens",
        f"- All nested `AGENTS.md` (Cursor currently injects these): **{b['all_nested_agents_md']['tokens']}** tokens",
        f"- Excluded trees (`change-history/`, `scratch/`): **{b['excluded_trees']['tokens']}** tokens not in the index",
        f"- Root `AGENTS.md` + `README.md` (unindexed): **{b['root_unindexed']['tokens']}** tokens",
        "",
        "## Lookups",
        "",
        "Each fixture is a realistic agent discovery question. BM25 is `qmd search`. Structured is agent-authored `lex:`/`vec:` with `--no-rerank`. Hybrid is the documented bare `qmd query` (expansion + rerank).",
        "",
        "| Fixture | Mode | Hits | Expected in top-N | Gold vs direct | Elapsed | Fetched tok | vs collection |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["lookups"]:
        for mode_run in row["runs"]:
            pct = mode_run.get("pct_saved_vs_collection")
            vs = f"{pct}%" if pct is not None else "—"
            acc = mode_run.get("accuracy_vs_direct")
            acc_s = f"{acc}%" if acc is not None else "—"
            lines.append(
                f"| `{row['id']}` | {mode_run['mode']} | {mode_run['hit_count']} | "
                f"{'yes' if mode_run['expected_in_top_n'] else 'NO'} | {acc_s} | "
                f"{mode_run['elapsed_s']}s | "
                f"{mode_run['fetched_tokens']} | {vs} |"
            )

    lines += [
        "",
        "## Theoretical savings (BM25 + fetch unique top hits)",
        "",
        "Compared with reading the hinted collection (or the full indexed corpus when no hint).",
        "",
    ]
    s = payload["savings_summary"]
    lines += [
        f"- Mean tokens loaded via qmd fetch: **{s['mean_fetched_tokens']}**",
        f"- Mean tokens if the agent walked the target collection: **{s['mean_collection_tokens']}**",
        f"- Mean savings vs collection walk: **{s['mean_pct_vs_collection']}%**",
        f"- Full indexed corpus: **{s['indexed_tokens']}** tokens; mean qmd fetch is **{s['pct_vs_corpus']}%** of that",
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
        default="results/cost-layers/qmd-dry-run",
        help=(
            "Output directory under repo root "
            "(default: results/cost-layers/qmd-dry-run; legacy dated paths still accepted)"
        ),
    )
    parser.add_argument("--min-score", type=float, default=0.5)
    parser.add_argument("-n", type=int, default=5, help="Max hits per query")
    parser.add_argument("--hybrid-n", type=int, default=3, help="How many fixtures also run documented hybrid query")
    parser.add_argument("--hybrid-timeout", type=int, default=180)
    parser.add_argument("--skip-hybrid", action="store_true")
    parser.add_argument("--skip-structured", action="store_true")
    args = parser.parse_args(argv)

    qmd = resolve_qmd()
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    indexed_files: list[str] = []
    for name in EXPECTED_COLLECTIONS:
        code, stdout, _, _ = run_qmd(qmd, ["ls", name], timeout=30)
        if code == 0:
            indexed_files.extend(parse_ls(stdout))

    health = health_checks(qmd, indexed_files)
    baselines = corpus_baselines()

    lookups = []
    hybrid_ids = {f.id for f in FIXTURES[: args.hybrid_n]} if not args.skip_hybrid else set()

    for fixture in FIXTURES:
        modes = ["bm25"]
        if not args.skip_structured:
            modes.append("structured")
        if fixture.id in hybrid_ids:
            modes.append("hybrid")
        runs = []
        for mode in modes:
            timeout = args.hybrid_timeout if mode == "hybrid" else 90
            print(f"running {fixture.id}/{mode}...", flush=True)
            try:
                runs.append(
                    run_search_mode(
                        qmd,
                        mode=mode,
                        fixture=fixture,
                        min_score=args.min_score,
                        n=args.n,
                        timeout=timeout,
                    )
                )
            except subprocess.TimeoutExpired:
                runs.append(
                    {
                        "mode": mode,
                        "ok": False,
                        "error": f"timeout after {timeout}s",
                        "elapsed_s": timeout,
                        "hit_count": 0,
                        "expected_in_top_n": False,
                        "hits": [],
                        "snippet_tokens": 0,
                        "fetched_tokens": 0,
                    }
                )
        lookups.append(
            {
                "id": fixture.id,
                "need": fixture.need,
                "expect_any": fixture.expect_any,
                "must_not": fixture.must_not,
                "collection_hint": fixture.collection_hint,
                "runs": runs,
            }
        )

    bm25_runs = [r for row in lookups for r in row["runs"] if r["mode"] == "bm25" and r.get("ok")]
    hinted = [r for r in bm25_runs if r.get("collection_tokens")]
    mean_fetched = int(round(sum(r["fetched_tokens"] for r in bm25_runs) / max(1, len(bm25_runs))))
    mean_col = int(round(sum(r["collection_tokens"] for r in hinted) / max(1, len(hinted)))) if hinted else 0
    mean_pct = round(sum(r["pct_saved_vs_collection"] for r in hinted) / len(hinted), 1) if hinted else None
    indexed_tokens = baselines["indexed_collections"]["tokens"]

    findings: list[str] = []
    failed_health = [c["id"] for c in health if not c["ok"]]
    if failed_health:
        findings.append(f"Health failures: {', '.join(failed_health)}.")
    else:
        findings.append("Collection set, exclusions, and docs index freshness all passed.")

    for row in lookups:
        for run in row["runs"]:
            if run.get("ok") and not run.get("expected_in_top_n"):
                top = ", ".join(h.get("file") or "?" for h in run.get("hits", [])[:3]) or "(no hits)"
                findings.append(
                    f"`{row['id']}` / {run['mode']} missed expected {row['expect_any']}; top hits: {top}."
                )
            if run.get("fetched_accuracy") and run["fetched_accuracy"].get("missing"):
                findings.append(
                    f"`{row['id']}` / {run['mode']} missed gold facts vs direct review: "
                    f"{run['fetched_accuracy']['missing']}."
                )
            if run.get("forbidden_hits"):
                findings.append(
                    f"`{row['id']}` / {run['mode']} returned excluded path(s): {run['forbidden_hits']}."
                )

    hybrid_runs = [r for row in lookups for r in row["runs"] if r["mode"] == "hybrid"]
    if hybrid_runs:
        mean_hy = round(sum(r["elapsed_s"] for r in hybrid_runs) / len(hybrid_runs), 1)
        findings.append(
            f"Documented hybrid `qmd query` averaged {mean_hy}s per lookup "
            f"(expansion + embed + rerank). BM25 `qmd search` is the fast path."
        )

    bm25_mean_s = round(sum(r["elapsed_s"] for r in bm25_runs) / max(1, len(bm25_runs)), 3)
    findings.append(f"BM25 lookups averaged {bm25_mean_s}s.")
    findings.append(
        "Root `AGENTS.md` is not in any collection; Critical rules stay in the hop, not in qmd."
    )
    findings.append(
        "Token savings assume the agent fetches unique top-N files instead of reading the whole area tree. "
        "Snippets alone are cheaper still, but qmd skill/docs say not to answer from snippets."
    )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "qmd": qmd if isinstance(qmd, str) else " ".join(qmd),
        "index": "C:/home/developer/.cache/qmd/index.sqlite",
        "min_score": args.min_score,
        "n": args.n,
        "token_method": "chars/4",
        "indexed_file_count": len(indexed_files),
        "indexed_files": indexed_files,
        "health": health,
        "baselines": {
            k: ({kk: vv for kk, vv in v.items() if kk != "files"} if isinstance(v, dict) else v)
            for k, v in baselines.items()
        },
        "lookups": lookups,
        "savings_summary": {
            "mean_fetched_tokens": mean_fetched,
            "mean_collection_tokens": mean_col,
            "mean_pct_vs_collection": mean_pct,
            "indexed_tokens": indexed_tokens,
            "pct_vs_corpus": round(100.0 * mean_fetched / indexed_tokens, 2) if indexed_tokens else None,
            "always_allowed_tokens": baselines["always_allowed_hop"]["tokens"],
            "all_agents_md_tokens": baselines["all_nested_agents_md"]["tokens"],
            "excluded_tokens": baselines["excluded_trees"]["tokens"],
        },
        "findings": findings,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir, payload)
    print(json.dumps({"out": str(out_dir), "health_fail": failed_health, "findings": findings}, indent=2))
    bm25_gold_fail = any(
        run.get("ok")
        and run.get("mode") == "bm25"
        and (run.get("fetched_accuracy") or {}).get("missing")
        for row in lookups
        for run in row["runs"]
    )
    return 0 if not failed_health and not bm25_gold_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
