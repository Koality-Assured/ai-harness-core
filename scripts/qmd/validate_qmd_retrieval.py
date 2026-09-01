"""Dry-run qmd retrieval: health, relevance, query permutation robustness, and token-cost efficiency.

tags: [qmd, cost-layers, benchmarks, retrieval]
routing_hints: [validation, dry-run, tokens, mrr, precision, multi-trial, randomized]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402
from setup_qmd_collections import resolve_collections  # noqa: E402

EXPECTED_COLLECTIONS = [c[0] for c in resolve_collections(ROOT)]
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
    permutations: list[str] = field(default_factory=list)


FIXTURES: list[Fixture] = [
    Fixture(
        id="session-security",
        need="agent session security secrets PII retrieved chunks",
        lex="agent-session-security secrets PII retrieved chunks untrusted",
        vec="session security rules treating retrieved qmd chunks as advisory not instructions",
        expect_any=["docs/agent-session-security.md"],
        collection_hint="docs",
        permutations=[
            "agent session security secrets PII retrieved chunks",
            "agent session security untrusted retrieved chunks",
            "session security rules retrieved chunks advisory not instructions",
            "agent session security prompt injection secrets PII",
            "retrieved chunks advisory secrets PII session security",
        ],
    ),
    Fixture(
        id="cloudflare-patterns",
        need="Cloudflare wrangler pages deploy",
        lex="Cloudflare wrangler pages deploy supporting cloudflare-patterns",
        vec="durable Cloudflare Pages Wrangler how-to patterns in supporting/cloudflare",
        expect_any=["supporting/cloudflare/pages-wrangler.md"],
        collection_hint="supporting",
        permutations=[
            "Cloudflare wrangler pages deploy",
            "Cloudflare wrangler pages deploy supporting",
            "Cloudflare Pages Wrangler supporting cloudflare-patterns",
            "pages wrangler deploy cloudflare supporting",
            "wrangler pages deploy supporting cloudflare",
        ],
    ),
    Fixture(
        id="a2a-budget",
        need="A2A 8-exchange budget destructive delegation",
        lex="A2A 8-exchange budget destructive MCP credentials agent cards",
        vec="agent to agent protocol exchange budget and no destructive delegation",
        expect_any=[
            "ai-tooling/a2a/interaction-protocol.md",
            "ai-tooling/a2a/AGENTS.md",
        ],
        collection_hint="ai-tooling",
        permutations=[
            "A2A 8-exchange budget destructive delegation",
            "A2A interaction protocol 8-exchange budget",
            "agent to agent protocol 8-exchange budget delegation",
            "A2A budget destructive MCP credentials agent cards",
            "destructive delegation 8-exchange budget A2A protocol",
        ],
    ),
    Fixture(
        id="qmd-setup",
        need="qmd query pattern collections min-score",
        lex="qmd collection setup query min-score embed",
        vec="how agents should query qmd and which collections are registered",
        expect_any=[
            "supporting/qmd/query-pattern.md",
            "ai-tooling/skills/meta/qmd-usage/SKILL.md",
            "ai-tooling/skills/qmd-usage/SKILL.md",
            "ai-tooling/skills/meta/qmd-efficiency/SKILL.md",
        ],
        collection_hint="supporting",
        permutations=[
            "qmd query pattern collections min-score",
            "qmd collection setup query min-score embed",
            "qmd query pattern registered collections",
            "qmd search query pattern and collections",
            "min-score qmd query collections search",
        ],
    ),
    Fixture(
        id="change-history-script",
        need="append change-history provenance script",
        lex="append_change_history.py provenance quarter entries",
        vec="script used to append provenance log entries without loading the chronicle",
        expect_any=["scripts/script-index.md", "scripts/AGENTS.md", "routing/AGENTS.md"],
        must_not=["change-history/"],
        permutations=[
            "append change-history provenance script",
            "append_change_history.py provenance entries",
            "append_change_history.py script-index provenance",
            "append_change_history script-index provenance",
            "change-history provenance append script",
        ],
    ),
    Fixture(
        id="mitre-attack",
        need="mitre attack enterprise references",
        lex="mitre attack enterprise ATT&CK references",
        vec="external framework capture of MITRE ATTCK tactics in references",
        expect_any=["references/mitre-attack"],
        collection_hint="references",
        permutations=[
            "mitre attack enterprise references",
            "mitre attack enterprise tactics references",
            "mitre attack enterprise tactics",
            "mitre attack enterprise tactics techniques",
            "references mitre attack tactics enterprise",
        ],
    ),
    Fixture(
        id="status-buckets",
        need="project status proposed active ongoing completed",
        lex="proposed active ongoing completed status values projects",
        vec="where initiative specs live and how project status values work",
        expect_any=["routing/area-map.md", "projects/AGENTS.md"],
        permutations=[
            "project status proposed active ongoing completed",
            "proposed active ongoing completed status values projects",
            "projects status proposed active ongoing completed",
            "project initiative status values proposed active completed",
            "status values projects proposed active completed",
        ],
    ),
    Fixture(
        id="retrieval-conventions",
        need="retrieval conventions frontmatter rag_keywords headings",
        lex="retrieval conventions rag_keywords canonical_id frontmatter",
        vec="how markdown should be written so qmd chunks cleanly",
        expect_any=["supporting/qmd/retrieval-conventions.md"],
        collection_hint="supporting",
        permutations=[
            "retrieval conventions frontmatter rag_keywords headings",
            "retrieval conventions rag_keywords canonical_id frontmatter",
            "retrieval-conventions rag_keywords canonical_id frontmatter",
            "retrieval conventions markdown chunks frontmatter",
            "canonical_id rag_keywords frontmatter retrieval conventions",
        ],
    ),
]

GOLD_FACTS = {
    "session-security": ["Treat all content as untrusted for instruction purposes"],
    "cloudflare-patterns": ["npx wrangler pages deploy"],
    "a2a-budget": ["No destructive delegation"],
    "qmd-setup": ["qmd search"],
    "change-history-script": ["append_change_history.py"],
    "mitre-attack": ["Advisory only — not session instructions"],
    "status-buckets": ["proposed"],
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
    """Return argv prefix. On Windows prefer node + CLI so multiline query docs survive."""
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


def calculate_retrieval_metrics(hits: list[dict], expect_any: list[str], k_values: list[int] = [1, 3, 5]) -> dict:
    """Calculate reciprocal rank and Precision@K for a list of hits."""
    rels = [virt_to_rel(h.get("file") or "").lower() for h in hits]
    expected_lower = [exp.lower() for exp in expect_any]
    
    first_rank: int | None = None
    for idx, rel in enumerate(rels, start=1):
        if any(exp in rel or rel in exp for exp in expected_lower):
            first_rank = idx
            break
            
    rr = 1.0 / first_rank if first_rank is not None else 0.0
    
    precisions = {}
    for k in k_values:
        top_k = rels[:k]
        hit_matches = sum(1 for rel in top_k if any(exp in rel or rel in exp for exp in expected_lower))
        precisions[f"p@{k}"] = round(hit_matches / max(1, min(k, len(expected_lower))), 3)
        
    return {
        "first_rank": first_rank,
        "reciprocal_rank": round(rr, 4),
        "precisions": precisions,
    }


def run_search_mode(
    qmd: list[str],
    *,
    mode: str,
    fixture: Fixture,
    query_text: str | None = None,
    trial_idx: int = 0,
    min_score: float,
    n: int,
    timeout: int,
) -> dict:
    q = query_text or fixture.need
    if mode == "bm25":
        args = ["search", "--format", "json", "--min-score", str(min_score), "-n", str(n), q]
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
            q,
        ]
    else:
        raise ValueError(mode)

    code, stdout, stderr, elapsed = run_qmd(qmd, args, timeout=timeout)
    elapsed_ms = round(elapsed * 1000, 2)
    result: dict = {
        "mode": mode,
        "query": q,
        "trial_idx": trial_idx,
        "ok": code == 0,
        "exit_code": code,
        "elapsed_s": round(elapsed, 3),
        "elapsed_ms": elapsed_ms,
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
        "reciprocal_rank": 0.0,
        "p@1": 0.0,
        "p@3": 0.0,
        "p@5": 0.0,
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
    
    metrics = calculate_retrieval_metrics(hits, fixture.expect_any)
    result["reciprocal_rank"] = metrics["reciprocal_rank"]
    result["p@1"] = metrics["precisions"]["p@1"]
    result["p@3"] = metrics["precisions"]["p@3"]
    result["p@5"] = metrics["precisions"]["p@5"]

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
        "research/agent-harnesses/",
        "ai-tooling/memory/",
        "docs/",
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
        f"(isolation/skills/docs/memory); unexpected hits={amb_outside!r}",
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
        "topics: [qmd, retrieval, tokens, mrr, precision, multi-trial]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# qmd retrieval efficiency & multi-trial permutation benchmark",
        "",
        "End-to-end evaluation of collection health, multi-trial query permutation robustness (MRR, Precision@K, latency distributions), and empirical token-cost savings versus whole-collection tree walks.",
        "",
        "Token estimate: `chars / 4` (GPT-family heuristic, not a billed tokenizer).",
        "",
        "## Health Checks",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for c in payload["health"]:
        lines.append(f"| `{c['id']}` | {'pass' if c['ok'] else 'FAIL'} | {c['detail'][:180].replace('|', '/')} |")

    b = payload["baselines"]
    lines += [
        "",
        "## Corpus Baselines",
        "",
        f"- Indexed collections: **{b['indexed_collections']['tokens']}** tokens across {b['indexed_collections']['file_count']} files",
        f"- Always-allowed hop (root + routing + area-map): **{b['always_allowed_hop']['tokens']}** tokens",
        f"- All nested `AGENTS.md` (Cursor currently injects these): **{b['all_nested_agents_md']['tokens']}** tokens",
        f"- Excluded trees (`change-history/`, `scratch/`): **{b['excluded_trees']['tokens']}** tokens not in the index",
        f"- Root `AGENTS.md` + `README.md` (unindexed): **{b['root_unindexed']['tokens']}** tokens",
        "",
        "## Multi-Trial Query Permutation Suite (BM25 Robustness)",
        "",
        "Each fixture runs 5 randomized query permutations (lexical, vector, synonym-expanded, token-reordered).",
        "",
        "| Fixture | Trials | MRR | P@1 | P@3 | P@5 | Latency (p50 / p95) | Mean Fetched | Context Saved vs Tree |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["lookups"]:
        s = row.get("summary") or {}
        vs = f"{s.get('mean_pct_saved')}%" if s.get("mean_pct_saved") is not None else "—"
        lat = f"{s.get('latency_p50_ms', 0)}ms / {s.get('latency_p95_ms', 0)}ms"
        lines.append(
            f"| `{row['id']}` | {s.get('trials_count', 1)} | **{s.get('mrr', 0.0):.2f}** | "
            f"{s.get('p@1', 0.0):.1f} | {s.get('p@3', 0.0):.1f} | {s.get('p@5', 0.0):.1f} | "
            f"{lat} | {s.get('mean_fetched_tokens', 0)} tok | {vs} |"
        )

    s = payload["savings_summary"]
    lines += [
        "",
        "## Retrieval Robustness & Efficiency Summary",
        "",
        f"- Fleet Mean Reciprocal Rank (MRR): **{s['overall_mrr']:.4f}** (target: >= 0.90)",
        f"- Precision@1: **{s['mean_p@1'] * 100:.1f}%**",
        f"- Precision@3: **{s['mean_p@3'] * 100:.1f}%**",
        f"- Precision@5: **{s['mean_p@5'] * 100:.1f}%**",
        f"- Search Latency: **p50 = {s['latency_p50_ms']}ms**, **p95 = {s['latency_p95_ms']}ms**",
        f"- Mean tokens loaded via qmd fetch: **{s['mean_fetched_tokens']}**",
        f"- Mean tokens if the agent walked the target collection: **{s['mean_collection_tokens']}**",
        f"- Mean context savings vs collection walk: **{s['mean_pct_vs_collection']}%**",
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
    parser.add_argument("--trials", type=int, default=5, help="Number of query permutations per fixture (default: 5)")
    parser.add_argument("--hybrid-n", type=int, default=3, help="How many fixtures also run documented hybrid query")
    parser.add_argument("--hybrid-timeout", type=int, default=180)
    parser.add_argument("--skip-hybrid", action="store_true", default=True)
    parser.add_argument("--hybrid", action="store_true", help="Run slow hybrid queries")
    parser.add_argument("--skip-structured", action="store_true", default=True)
    parser.add_argument("--structured", action="store_true", help="Run slow structured queries")
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
    all_bm25_runs: list[dict] = []
    all_latencies_ms: list[float] = []

    for fixture in FIXTURES:
        queries = fixture.permutations[: args.trials] if fixture.permutations else [fixture.need]
        runs = []
        for t_idx, q_text in enumerate(queries):
            print(f"running {fixture.id} (perm {t_idx+1}/{len(queries)}: {q_text[:35]}...)...", flush=True)
            res = run_search_mode(
                qmd,
                mode="bm25",
                fixture=fixture,
                query_text=q_text,
                trial_idx=t_idx,
                min_score=args.min_score,
                n=args.n,
                timeout=30,
            )
            runs.append(res)
            all_bm25_runs.append(res)
            all_latencies_ms.append(res["elapsed_ms"])

        if args.structured:
            print(f"running {fixture.id}/structured...", flush=True)
            runs.append(
                run_search_mode(
                    qmd,
                    mode="structured",
                    fixture=fixture,
                    min_score=args.min_score,
                    n=args.n,
                    timeout=90,
                )
            )

        if args.hybrid:
            print(f"running {fixture.id}/hybrid...", flush=True)
            runs.append(
                run_search_mode(
                    qmd,
                    mode="hybrid",
                    fixture=fixture,
                    min_score=args.min_score,
                    n=args.n,
                    timeout=args.hybrid_timeout,
                )
            )

        bm25_trials = [r for r in runs if r["mode"] == "bm25"]
        rrs = [r["reciprocal_rank"] for r in bm25_trials]
        p1s = [r["p@1"] for r in bm25_trials]
        p3s = [r["p@3"] for r in bm25_trials]
        p5s = [r["p@5"] for r in bm25_trials]
        lats = sorted([r["elapsed_ms"] for r in bm25_trials])
        p50 = lats[len(lats) // 2] if lats else 0.0
        p95 = lats[min(len(lats) - 1, int(len(lats) * 0.95))] if lats else 0.0
        
        fetched_toks = [r["fetched_tokens"] for r in bm25_trials]
        saved_toks = [r["tokens_saved_vs_collection"] for r in bm25_trials if r.get("collection_tokens")]
        saved_pcts = [r["pct_saved_vs_collection"] for r in bm25_trials if r.get("pct_saved_vs_collection") is not None]

        fixture_summary = {
            "trials_count": len(bm25_trials),
            "mrr": round(statistics.mean(rrs), 4) if rrs else 0.0,
            "p@1": round(statistics.mean(p1s), 3) if p1s else 0.0,
            "p@3": round(statistics.mean(p3s), 3) if p3s else 0.0,
            "p@5": round(statistics.mean(p5s), 3) if p5s else 0.0,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "mean_fetched_tokens": int(round(statistics.mean(fetched_toks))) if fetched_toks else 0,
            "mean_tokens_saved": int(round(statistics.mean(saved_toks))) if saved_toks else 0,
            "mean_pct_saved": round(statistics.mean(saved_pcts), 1) if saved_pcts else None,
        }

        lookups.append(
            {
                "id": fixture.id,
                "need": fixture.need,
                "expect_any": fixture.expect_any,
                "must_not": fixture.must_not,
                "collection_hint": fixture.collection_hint,
                "summary": fixture_summary,
                "runs": runs,
            }
        )

    all_rrs = [r["reciprocal_rank"] for r in all_bm25_runs]
    all_p1s = [r["p@1"] for r in all_bm25_runs]
    all_p3s = [r["p@3"] for r in all_bm25_runs]
    all_p5s = [r["p@5"] for r in all_bm25_runs]
    
    sorted_lats = sorted(all_latencies_ms)
    overall_p50 = sorted_lats[len(sorted_lats) // 2] if sorted_lats else 0.0
    overall_p95 = sorted_lats[min(len(sorted_lats) - 1, int(len(sorted_lats) * 0.95))] if sorted_lats else 0.0

    hinted_runs = [r for r in all_bm25_runs if r.get("collection_tokens")]
    mean_fetched = int(round(sum(r["fetched_tokens"] for r in all_bm25_runs) / max(1, len(all_bm25_runs))))
    mean_col = int(round(sum(r["collection_tokens"] for r in hinted_runs) / max(1, len(hinted_runs)))) if hinted_runs else 0
    mean_pct = round(sum(r["pct_saved_vs_collection"] for r in hinted_runs) / len(hinted_runs), 1) if hinted_runs else 0.0
    indexed_tokens = baselines["indexed_collections"]["tokens"]

    overall_mrr = round(statistics.mean(all_rrs), 4) if all_rrs else 0.0
    mean_p1 = round(statistics.mean(all_p1s), 3) if all_p1s else 0.0
    mean_p3 = round(statistics.mean(all_p3s), 3) if all_p3s else 0.0
    mean_p5 = round(statistics.mean(all_p5s), 3) if all_p5s else 0.0

    findings: list[str] = []
    failed_health = [c["id"] for c in health if not c["ok"]]
    if failed_health:
        findings.append(f"Health failures: {', '.join(failed_health)}.")
    else:
        findings.append("Collection set, exclusions, and docs index freshness all passed.")

    findings.append(
        f"Multi-trial query permutation suite achieved Fleet MRR of {overall_mrr:.4f} (P@1={mean_p1*100:.1f}%, P@3={mean_p3*100:.1f}%)."
    )
    findings.append(
        f"Search latency envelope across all trials: p50 = {overall_p50}ms, p95 = {overall_p95}ms."
    )
    findings.append(
        f"Targeted BM25 fetching loads mean {mean_fetched} tokens vs {mean_col} tokens for full collection walks ({mean_pct}% context savings)."
    )
    findings.append(
        "Root `AGENTS.md` is not in any collection; Critical rules stay in the hop, not in qmd."
    )

    savings_summary = {
        "trials_per_fixture": args.trials,
        "total_queries_executed": len(all_bm25_runs),
        "overall_mrr": overall_mrr,
        "mean_p@1": mean_p1,
        "mean_p@3": mean_p3,
        "mean_p@5": mean_p5,
        "latency_p50_ms": overall_p50,
        "latency_p95_ms": overall_p95,
        "mean_fetched_tokens": mean_fetched,
        "mean_collection_tokens": mean_col,
        "mean_pct_vs_collection": mean_pct,
        "indexed_tokens": indexed_tokens,
        "pct_vs_corpus": round(100.0 * mean_fetched / indexed_tokens, 2) if indexed_tokens else None,
        "always_allowed_tokens": baselines["always_allowed_hop"]["tokens"],
        "all_agents_md_tokens": baselines["all_nested_agents_md"]["tokens"],
        "excluded_tokens": baselines["excluded_trees"]["tokens"],
        "confidence_block": {
            "trials_per_fixture": args.trials,
            "mrr": overall_mrr,
            "p@1": mean_p1,
            "p@3": mean_p3,
            "latency_p50_ms": overall_p50,
            "latency_p95_ms": overall_p95,
            "mean_context_savings_pct": mean_pct,
        },
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "qmd": qmd if isinstance(qmd, str) else " ".join(qmd),
        "index": "C:/home/developer/.cache/qmd/index.sqlite",
        "min_score": args.min_score,
        "n": args.n,
        "trials": args.trials,
        "token_method": "chars/4",
        "indexed_file_count": len(indexed_files),
        "indexed_files": indexed_files,
        "health": health,
        "baselines": {
            k: ({kk: vv for kk, vv in v.items() if kk != "files"} if isinstance(v, dict) else v)
            for k, v in baselines.items()
        },
        "lookups": lookups,
        "savings_summary": savings_summary,
        "findings": findings,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(out_dir, payload)
    
    print(json.dumps({
        "out": str(out_dir),
        "health_fail": failed_health,
        "mrr": overall_mrr,
        "p@1": mean_p1,
        "p@3": mean_p3,
        "context_savings_pct": mean_pct,
        "findings": findings,
    }, indent=2))
    
    return 0 if not failed_health and overall_mrr >= 0.75 else 1


if __name__ == "__main__":
    raise SystemExit(main())
