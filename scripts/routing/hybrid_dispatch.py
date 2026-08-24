"""3-Tier Hybrid Dispatch Pipeline for skills, agents, and area routing.

tags: [routing, ai-tooling]
routing_hints: [dispatch, hybrid-dispatch, bm25, fast-path, ambiguity-gate, router]

Tier 1: Fast-Path Regex/Keyword (<1ms, 0 tokens). Resolves MED-02 by preventing over-triggering on multi-intent queries.
Tier 2: In-Memory BM25 Lexical/Semantic Index (~5ms, 0 tokens) over skill-dispatch and area-map metadata.
Tier 3: Structured LLM Ambiguity Gate for multi-intent triage payloads and disambiguation questions.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import load_area_records, load_nested_defaults  # noqa: E402
from md import heading_titles, load_skill_record, parse_frontmatter, skill_paths  # noqa: E402
from paths import REPO_ROOT as DEFAULT_ROOT  # noqa: E402

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "cannot", "could", "did", "do", "does", "doing", "down", "during", "each", "few",
    "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "let",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves",
}


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric and hyphenated tokens, removing stop words."""
    if not text:
        return []
    # Extract words and hyphenated terms
    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    result: list[str] = []
    for tok in tokens:
        if tok in STOP_WORDS:
            continue
        result.append(tok)
        # If token has hyphens, also index subwords
        if "-" in tok:
            for sub in tok.split("-"):
                if sub and sub not in STOP_WORDS and len(sub) > 1:
                    result.append(sub)
    return result


@dataclass
class Tier1Result:
    tier: int = 1
    matched: bool = False
    skill: str | None = None
    owner_agent: str | None = None
    confidence: float = 0.0
    matched_patterns: list[str] = field(default_factory=list)
    conflicting_skills: list[str] = field(default_factory=list)
    reason: str = "no_match"
    elapsed_ms: float = 0.0


@dataclass
class BM25Candidate:
    name: str
    type: str  # "skill" | "area"
    owner_agent: str
    rank: str
    isolation: str
    score: float
    confidence: float
    matched_terms: list[str]
    description: str


@dataclass
class Tier2Result:
    tier: int = 2
    matched: bool = False
    skill: str | None = None
    owner_agent: str | None = None
    confidence: float = 0.0
    is_ambiguous: bool = True
    candidates: list[BM25Candidate] = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass
class Tier3Result:
    tier: int = 3
    status: str = "ambiguous"  # "ambiguous" | "multi_intent" | "single_candidate"
    query: str = ""
    reason: str = ""
    candidates: list[dict[str, Any]] = field(default_factory=list)
    disambiguation_questions: list[str] = field(default_factory=list)
    recommended_action: str = "clarify_with_user"
    llm_triage_prompt: str = ""
    elapsed_ms: float = 0.0


@dataclass
class HybridDispatchResult:
    query: str
    selected_tier: int
    final_target: str | None
    owner_agent: str | None
    confidence: float
    status: str  # "dispatched" | "ambiguous" | "no_match"
    tier1: Tier1Result | None = None
    tier2: Tier2Result | None = None
    tier3: Tier3Result | None = None
    total_elapsed_ms: float = 0.0


# ----------------------------------------------------------------------
# Tier 1: Fast-Path Regex & Keyword Matching (MED-02 Resilient)
# ----------------------------------------------------------------------

FAST_PATH_RULES: list[dict[str, Any]] = [
    # Git operations
    {
        "skill": "git-basics",
        "owner_agent": "git-fast-operator",
        "patterns": [
            r"\bgit\s+(?:status|diff|log|fetch|pull|branch|sync)\b",
            r"\bfast\s+git\s+(?:inspection|sync|status)\b",
            r"\bgit\s+operations\b",
        ],
    },
    {
        "skill": "isolate-work",
        "owner_agent": "router-maintenance",
        "patterns": [
            r"\b(?:spawn|create|claim)\s+(?:git\s+)?worktree\b",
            r"\bgit\s+worktree\b",
            r"\bisolate\s+work\b",
            r"\bworktree\s+isolation\b",
            r"\bbranch\s+claim\b",
        ],
    },
    {
        "skill": "github-workflow",
        "owner_agent": "github-ops",
        "patterns": [
            r"\bgh\s+pr\s+(?:create|status|view|checks|review)\b",
            r"\bgithub\s+(?:workflow|pull\s+request|pr\s+review)\b",
            r"\bcreate\s+(?:a\s+)?pull\s+request\b",
        ],
    },
    {
        "skill": "github-paths",
        "owner_agent": "github-ops",
        "patterns": [
            r"\b(?:resolve|convert)\s+(?:to\s+)?github\s+path\b",
            r"\bblob/main\s+url\b",
            r"\btree/main\s+url\b",
            r"\bgithub-paths\b",
        ],
    },
    # QMD operations
    {
        "skill": "qmd-usage",
        "owner_agent": "qmd-ops",
        "patterns": [
            r"\bqmd\s+(?:search|get|query)\b",
            r"\bqmd\s+retrieval\b",
            r"\bqmd\s+commands\b",
            r"\bqmd-usage\b",
        ],
    },
    {
        "skill": "qmd-efficiency",
        "owner_agent": "qmd-ops",
        "patterns": [
            r"\bqmd\s+efficiency\b",
            r"\bqmd\s+token\s+(?:report|savings)\b",
            r"\bqmd\s+health\b",
            r"\bqmd-efficiency\b",
        ],
    },
    # AST-grep and Cost Layers
    {
        "skill": "ast-grep",
        "owner_agent": "router-maintenance",
        "patterns": [
            r"\bast-grep\b",
            r"\bastgrep\b",
            r"\bsg\s+scan\b",
            r"\bstructural\s+search\b",
            r"\bprecision\s+retrieval\b",
            r"\bstructured\s+facts\b",
        ],
    },
    {
        "skill": "headroom",
        "owner_agent": "router-maintenance",
        "patterns": [
            r"\bheadroom\b",
            r"\bcontext\s+compression\b",
            r"\bcompression\s+proxy\b",
            r"\blocalhost:8787\b",
        ],
    },
    {
        "skill": "cost-layer-dry-run",
        "owner_agent": "router-maintenance",
        "patterns": [
            r"\bcost\s+layer\s+dry\s*run\b",
            r"\bcost-layer-dry-run\b",
            r"\bcombined\s+cost\s+layers\b",
        ],
    },
    # Diagrams
    {
        "skill": "mermaid-diagram",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\b(?:render|generate|create)\s+mermaid\s+diagram\b",
            r"\bmermaid-diagram\b",
            r"\brender_diagram\.py\b",
            r"\bmermaid\s+(?:flowchart|sequence|graph)\b",
            r"\bmermaid\b",
        ],
    },
    {
        "skill": "architecture-diagram",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\barchitecture\s+diagram\b",
            r"\bsystem\s+context\s+diagram\b",
            r"\bc4\s+model\s+diagram\b",
        ],
    },
    # Security & Assessment
    {
        "skill": "noir-scan",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\b(?:run\s+)?noir\s+scan\b",
            r"\bnoir-scan\b",
            r"\bowasp\s+noir\b",
            r"\bshadow\s+api\s+scan\b",
            r"\brun_noir_scan\.py\b",
            r"\bsecurity\s+scans?\b",
            r"\bnoir\b",
        ],
    },
    {
        "skill": "threat-model",
        "owner_agent": "assessment-agent",
        "patterns": [
            r"\bstride\s+threat\s+model\b",
            r"\bthreat\s+model(?:ing)?\b",
            r"\bthreat-model\b",
            r"\bbuild_threat_model\.py\b",
            r"\bstride\b",
        ],
    },
    {
        "skill": "code-review-report",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\bcode\s+review\s+report\b",
            r"\bcwe\s+code\s+review\b",
            r"\bstandards-backed\s+code\s+review\b",
            r"\bcode\s+review\b",
        ],
    },
    {
        "skill": "antagonistic-review",
        "owner_agent": "detailed-activity",
        "patterns": [
            r"\bantagonistic\s+review\b",
            r"\badversarial\s+(?:audit|findings|review)\b",
            r"\bhole-poking\s+review\b",
            r"\bvalue\s+vs\s+bloat\s+audit\b",
        ],
    },
    # Content & Prose Quality
    {
        "skill": "anti-slop",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\banti-slop\b",
            r"\banti\s+slop\b",
            r"\bstrip\s+(?:ai\s+)?slop\b",
            r"\bremove\s+slop\b",
            r"\bslop\s+detection\b",
            r"\bslop\b",
        ],
    },
    {
        "skill": "humanizer",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\bhumanizer\b",
            r"\bhumanize\s+(?:prose|writing|text)\b",
            r"\brewrite\s+human\b",
        ],
    },
    # Documentation & Maintenance
    {
        "skill": "markdownlint",
        "owner_agent": "documentation-ops",
        "patterns": [
            r"\bmarkdownlint\b",
            r"\blint\s+markdown\b",
            r"\bmarkdownlint-cli2\b",
            r"\bmd001\b",
            r"\bclear\s+md###\s+findings\b",
        ],
    },
    {
        "skill": "doc-builder",
        "owner_agent": "documentation-ops",
        "patterns": [
            r"\bdoc-builder\b",
            r"\bauthor\s+(?:durable\s+)?docs\b",
            r"\bcreate\s+standard\s+doc\b",
            r"\bdurable\s+docs\b",
            r"\b(?:in\s+|under\s+)?docs/\b",
        ],
    },
    {
        "skill": "wiki-structure",
        "owner_agent": "documentation-ops",
        "patterns": [
            r"\bwiki-structure\b",
            r"\bvalidate\s+wiki\s+structure\b",
            r"\bwiki\s+structure\s+check\b",
        ],
    },
    {
        "skill": "scratch-cleanup",
        "owner_agent": "router-maintenance",
        "patterns": [
            r"\bscratch-cleanup\b",
            r"\bclean(?:up)?\s+scratch\b",
            r"\bpurge\s+scratch\b",
        ],
    },
    # Builders & Tooling
    {
        "skill": "skill-builder",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bskill-builder\b",
            r"\bauthor\s+(?:new\s+)?skill\b",
            r"\bcreate\s+skill\b",
        ],
    },
    {
        "skill": "agent-builder",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bagent-builder\b",
            r"\bcreate\s+specialist\s+agent\b",
            r"\brevise\s+agent\s+definition\b",
        ],
    },
    {
        "skill": "skill-dry-run",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bskill-dry-run\b",
            r"\bdry\s*run\s+skill\b",
            r"\bvalidate\s+skill\b",
        ],
    },
    {
        "skill": "as-code-builder",
        "owner_agent": "as-code-agent",
        "patterns": [
            r"\bas-code-builder\b",
            r"\bdraft\s+(?:terraform|pulumi|ansible|kyverno|rego)\b",
            r"\biac\s+artifact\b",
            r"\bpolicy-as-code\b",
        ],
    },
    # Research & Deliverables
    {
        "skill": "deep-research",
        "owner_agent": "detailed-activity",
        "patterns": [
            r"\bdeep-research\b",
            r"\bdeep\s+research\b",
            r"\binternet-backed\s+investigation\b",
        ],
    },
    {
        "skill": "executive-report",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\bexecutive-report\b",
            r"\bexecutive\s+report\b",
            r"\bdecision-oriented\s+summary\b",
        ],
    },
    {
        "skill": "proposal-report",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\bproposal-report\b",
            r"\bproposal\s+report\b",
        ],
    },
    {
        "skill": "tabler-dashboard",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\btabler-dashboard\b",
            r"\btabler\s+dashboard\b",
            r"\bhtml\s+dashboard\b",
        ],
    },
    {
        "skill": "foundation-site",
        "owner_agent": "artifact-agent",
        "patterns": [
            r"\bfoundation-site\b",
            r"\bfoundation\s+sites?\s+html\b",
            r"\bbuild_foundation_site\.py\b",
        ],
    },
    # Memory
    {
        "skill": "memory-create",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bmemory-create\b",
            r"\bcreate\s+memory\s+checkpoint\b",
        ],
    },
    {
        "skill": "memory-adjust",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bmemory-adjust\b",
            r"\bupdate\s+memory\s+checkpoint\b",
        ],
    },
    {
        "skill": "memory-cleanup",
        "owner_agent": "ai-tooling-ops",
        "patterns": [
            r"\bmemory-cleanup\b",
            r"\barchive\s+memory\s+checkpoint\b",
        ],
    },
    # Cloud operators
    {
        "skill": "aws-logs",
        "owner_agent": "cloud-operator",
        "patterns": [r"\baws\s+logs\b", r"\baws-logs\b"],
    },
    {
        "skill": "aws-read",
        "owner_agent": "cloud-operator",
        "patterns": [r"\baws\s+read\b", r"\baws-read\b", r"\binspect\s+aws\b"],
    },
    {
        "skill": "aws-write",
        "owner_agent": "cloud-operator",
        "patterns": [r"\baws\s+write\b", r"\baws-write\b", r"\bauthorize\s+aws\s+write\b"],
    },
    {
        "skill": "azure-logs",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bazure\s+logs\b", r"\bazure-logs\b"],
    },
    {
        "skill": "azure-read",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bazure\s+read\b", r"\bazure-read\b", r"\binspect\s+azure\b"],
    },
    {
        "skill": "azure-write",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bazure\s+write\b", r"\bazure-write\b", r"\bauthorize\s+azure\s+write\b"],
    },
    {
        "skill": "gcp-logs",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bgcp\s+logs\b", r"\bgcp-logs\b"],
    },
    {
        "skill": "gcp-read",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bgcp\s+read\b", r"\bgcp-read\b", r"\binspect\s+gcp\b"],
    },
    {
        "skill": "gcp-write",
        "owner_agent": "cloud-operator",
        "patterns": [r"\bgcp\s+write\b", r"\bgcp-write\b", r"\bauthorize\s+gcp\s+write\b"],
    },
]


class Tier1FastPath:
    """Tier 1 Fast-Path Regex & Keyword Dispatcher.
    
    Sub-millisecond matcher with strict MED-02 multi-intent collision handling.
    """

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self.rules = rules or FAST_PATH_RULES
        self._compiled: list[tuple[str, str, list[re.Pattern]]] = []
        for r in self.rules:
            skill = r["skill"]
            owner = r["owner_agent"]
            patterns = [re.compile(p, re.IGNORECASE) for p in r["patterns"]]
            self._compiled.append((skill, owner, patterns))

    def evaluate(self, query: str) -> Tier1Result:
        t0 = time.perf_counter()
        matched_map: dict[str, tuple[str, list[str]]] = {}

        for skill, owner, patterns in self._compiled:
            for p in patterns:
                m = p.search(query)
                if m:
                    if skill not in matched_map:
                        matched_map[skill] = (owner, [])
                    matched_map[skill][1].append(m.group(0))

        elapsed = (time.perf_counter() - t0) * 1000.0

        if not matched_map:
            return Tier1Result(
                tier=1,
                matched=False,
                reason="no_match",
                elapsed_ms=elapsed,
            )

        if len(matched_map) > 1:
            # MED-02: Multi-intent collision detected. Do NOT over-trigger; fall through to BM25/LLM gate.
            skills = sorted(matched_map.keys())
            all_patterns = [pat for s in skills for pat in matched_map[s][1]]
            return Tier1Result(
                tier=1,
                matched=False,
                conflicting_skills=skills,
                matched_patterns=all_patterns,
                reason="multi_intent_conflict",
                elapsed_ms=elapsed,
            )

        # Exactly 1 skill matched unambiguously
        single_skill = next(iter(matched_map.keys()))
        owner, pats = matched_map[single_skill]
        return Tier1Result(
            tier=1,
            matched=True,
            skill=single_skill,
            owner_agent=owner,
            confidence=1.0,
            matched_patterns=pats,
            reason="unambiguous_match",
            elapsed_ms=elapsed,
        )


# ----------------------------------------------------------------------
# Tier 2: In-Memory BM25 Lexical / Semantic Index
# ----------------------------------------------------------------------

@dataclass
class IndexedDocument:
    doc_id: str
    doc_type: str  # "skill" | "area"
    name: str
    owner_agent: str
    rank: str
    isolation: str
    description: str
    tokens: list[str]
    length: int


class Tier2BM25:
    """In-memory BM25 index over routing metadata (~5ms, 0 tokens)."""

    def __init__(self, root: Path | None = None, k1: float = 1.5, b: float = 0.75) -> None:
        self.root = root or DEFAULT_ROOT
        self.k1 = k1
        self.b = b
        self.docs: list[IndexedDocument] = []
        self.idf: dict[str, float] = {}
        self.avgdl: float = 0.0
        self._build_index()

    def _build_index(self) -> None:
        self.docs.clear()
        # 1. Index skills
        for path in skill_paths(self.root):
            rec = load_skill_record(path)
            # Boost name and hints by duplicating terms
            name_tokens = tokenize(rec["name"]) * 3
            hints_tokens = tokenize(" ".join(rec.get("routing_hints", []))) * 2
            topics_tokens = tokenize(" ".join(rec.get("topics", []))) * 2
            desc_tokens = tokenize(rec["description"])
            body_tokens = tokenize(rec["body"][:500])  # preview body

            all_tokens = name_tokens + hints_tokens + topics_tokens + desc_tokens + body_tokens
            doc = IndexedDocument(
                doc_id=f"skill:{rec['name']}",
                doc_type="skill",
                name=rec["name"],
                owner_agent=rec["owner_agent"],
                rank=rec["rank"],
                isolation=rec["isolation"],
                description=rec["description"],
                tokens=all_tokens,
                length=len(all_tokens),
            )
            self.docs.append(doc)

        # 2. Index areas
        try:
            area_records = load_area_records(self.root)
            for area in area_records:
                area_id = area.get("id", "")
                purpose = area.get("purpose", "")
                owner = area.get("default_agent", "router")
                tokens = (tokenize(area_id) * 3) + tokenize(purpose) * 2
                doc = IndexedDocument(
                    doc_id=f"area:{area_id}",
                    doc_type="area",
                    name=area_id,
                    owner_agent=owner,
                    rank="medium",
                    isolation="mutate" if "mutate" in area.get("load", "") else "read-only",
                    description=purpose,
                    tokens=tokens,
                    length=len(tokens),
                )
                self.docs.append(doc)
        except Exception:
            pass

        # Calculate IDF and avgdl
        N = len(self.docs)
        if N == 0:
            self.avgdl = 0.0
            return

        self.avgdl = sum(d.length for d in self.docs) / N
        df: dict[str, int] = {}
        for doc in self.docs:
            unique_terms = set(doc.tokens)
            for term in unique_terms:
                df[term] = df.get(term, 0) + 1

        for term, freq in df.items():
            # BM25 standard smoothed IDF formula
            self.idf[term] = math.log(1.0 + (N - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 5) -> Tier2Result:
        t0 = time.perf_counter()
        query_tokens = tokenize(query)
        if not query_tokens or not self.docs:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return Tier2Result(tier=2, matched=False, elapsed_ms=elapsed)

        scores: list[tuple[IndexedDocument, float, list[str]]] = []

        for doc in self.docs:
            doc_score = 0.0
            matched_terms: list[str] = []
            tf_map: dict[str, int] = {}
            for t in doc.tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            for q_term in query_tokens:
                if q_term in tf_map:
                    tf = tf_map[q_term]
                    idf = self.idf.get(q_term, 0.1)
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (doc.length / (self.avgdl or 1.0)))
                    term_score = idf * ((tf * (self.k1 + 1.0)) / denom)
                    doc_score += term_score
                    if q_term not in matched_terms:
                        matched_terms.append(q_term)

            if doc_score > 0.0:
                scores.append((doc, doc_score, matched_terms))

        elapsed = (time.perf_counter() - t0) * 1000.0

        if not scores:
            return Tier2Result(tier=2, matched=False, elapsed_ms=elapsed)

        scores.sort(key=lambda x: x[1], reverse=True)
        top_scores = scores[:top_k]

        max_raw = top_scores[0][1]
        candidates: list[BM25Candidate] = []
        for doc, raw_score, matched in top_scores:
            # Normalized confidence against max raw score
            confidence = round(min(1.0, raw_score / (max_raw + 1e-6)), 3)
            candidates.append(
                BM25Candidate(
                    name=doc.name,
                    type=doc.doc_type,
                    owner_agent=doc.owner_agent,
                    rank=doc.rank,
                    isolation=doc.isolation,
                    score=round(raw_score, 3),
                    confidence=confidence,
                    matched_terms=matched,
                    description=doc.description,
                )
            )

        # Ambiguity check: if top candidate has high margin over 2nd candidate
        top_cand = candidates[0]
        second_cand = candidates[1] if len(candidates) > 1 else None

        is_ambiguous = True
        if len(candidates) == 1:
            is_ambiguous = top_cand.score < 2.0
        elif second_cand is not None:
            score_ratio = top_cand.score / (second_cand.score + 1e-6)
            is_ambiguous = score_ratio < 1.4 or top_cand.score < 3.0

        matched = not is_ambiguous and top_cand.score >= 3.0

        return Tier2Result(
            tier=2,
            matched=matched,
            skill=top_cand.name if top_cand.type == "skill" else None,
            owner_agent=top_cand.owner_agent,
            confidence=top_cand.confidence if matched else (top_cand.confidence * 0.8),
            is_ambiguous=is_ambiguous,
            candidates=candidates,
            elapsed_ms=elapsed,
        )


# ----------------------------------------------------------------------
# Tier 3: Structured LLM Ambiguity Gate
# ----------------------------------------------------------------------

class Tier3AmbiguityGate:
    """Constructs structured candidate triage payloads and disambiguation questions."""

    def evaluate(
        self,
        query: str,
        candidates: list[BM25Candidate] | list[dict[str, Any]],
        conflicting_skills: list[str] | None = None,
    ) -> Tier3Result:
        t0 = time.perf_counter()

        cand_list: list[dict[str, Any]] = []
        for c in candidates:
            if isinstance(c, BM25Candidate):
                cand_list.append(asdict(c))
            elif isinstance(c, dict):
                cand_list.append(c)

        if conflicting_skills and not cand_list:
            for s in conflicting_skills:
                cand_list.append(
                    {
                        "name": s,
                        "type": "skill",
                        "owner_agent": "—",
                        "rank": "—",
                        "isolation": "mutate",
                        "score": 1.0,
                        "confidence": 0.5,
                        "matched_terms": [s],
                        "description": f"Skill candidate for {s}",
                    }
                )

        # Formulate disambiguation questions
        questions: list[str] = []
        for c in cand_list[:4]:
            name = c.get("name", "")
            desc = c.get("description", "")
            matched = ", ".join(c.get("matched_terms", [])) or name
            # Truncate description to 120 chars
            short_desc = desc[:120].strip()
            if short_desc and not short_desc.endswith("."):
                short_desc += "..."
            questions.append(
                f"Did you intend to execute `{name}` ({short_desc}) based on '{matched}'?"
            )

        status = "multi_intent" if (conflicting_skills or len(cand_list) > 1) else "ambiguous"
        reason = (
            f"Query matched {len(cand_list)} competing candidate targets across different skill/area domains."
            if len(cand_list) > 1
            else "Query intent is ambiguous or has low match confidence."
        )

        prompt_lines = [
            "You are the Router Ambiguity Triage Gate.",
            f"User Query: {query}",
            "",
            "Candidate Options:",
        ]
        for i, c in enumerate(cand_list[:4], start=1):
            prompt_lines.append(
                f"{i}. [{c.get('name')}] (owner: {c.get('owner_agent')}, type: {c.get('type')}) - {c.get('description')}"
            )
        prompt_lines.extend(
            [
                "",
                "Disambiguation Questions to Ask:",
            ]
        )
        for q in questions:
            prompt_lines.append(f"- {q}")
        prompt_lines.extend(
            [
                "",
                "Evaluate user intent and either select the single best candidate or prompt for clarification.",
            ]
        )

        elapsed = (time.perf_counter() - t0) * 1000.0

        return Tier3Result(
            tier=3,
            status=status,
            query=query,
            reason=reason,
            candidates=cand_list,
            disambiguation_questions=questions,
            recommended_action="clarify_with_user" if len(cand_list) > 1 else "select_top_candidate",
            llm_triage_prompt="\n".join(prompt_lines),
            elapsed_ms=elapsed,
        )


# ----------------------------------------------------------------------
# Unified Hybrid Dispatcher Pipeline
# ----------------------------------------------------------------------

class HybridDispatcher:
    """3-Tier Hybrid Dispatch Pipeline Coordinator."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_ROOT
        self.tier1 = Tier1FastPath()
        self.tier2 = Tier2BM25(root=self.root)
        self.tier3 = Tier3AmbiguityGate()

    def dispatch(self, query: str, tier: str = "all", top_k: int = 5) -> HybridDispatchResult:
        t0 = time.perf_counter()

        t1_res: Tier1Result | None = None
        t2_res: Tier2Result | None = None
        t3_res: Tier3Result | None = None

        if tier in {"1", "all"}:
            t1_res = self.tier1.evaluate(query)
            if tier == "1" or (t1_res.matched and tier == "all"):
                total_elapsed = (time.perf_counter() - t0) * 1000.0
                return HybridDispatchResult(
                    query=query,
                    selected_tier=1,
                    final_target=t1_res.skill,
                    owner_agent=t1_res.owner_agent,
                    confidence=t1_res.confidence,
                    status="dispatched" if t1_res.matched else "no_match",
                    tier1=t1_res,
                    total_elapsed_ms=total_elapsed,
                )

        if tier in {"2", "all"}:
            t2_res = self.tier2.search(query, top_k=top_k)
            if tier == "2" or (t2_res.matched and not t2_res.is_ambiguous and tier == "all"):
                total_elapsed = (time.perf_counter() - t0) * 1000.0
                return HybridDispatchResult(
                    query=query,
                    selected_tier=2,
                    final_target=t2_res.skill or (t2_res.candidates[0].name if t2_res.candidates else None),
                    owner_agent=t2_res.owner_agent or (t2_res.candidates[0].owner_agent if t2_res.candidates else None),
                    confidence=t2_res.confidence,
                    status="dispatched" if t2_res.matched else "ambiguous",
                    tier1=t1_res,
                    tier2=t2_res,
                    total_elapsed_ms=total_elapsed,
                )

        # Tier 3 Ambiguity Gate
        if tier in {"3", "all"}:
            if t2_res is None:
                t2_res = self.tier2.search(query, top_k=top_k)

            conflicts = t1_res.conflicting_skills if t1_res and t1_res.conflicting_skills else None
            t3_res = self.tier3.evaluate(
                query=query,
                candidates=t2_res.candidates if t2_res else [],
                conflicting_skills=conflicts,
            )
            total_elapsed = (time.perf_counter() - t0) * 1000.0

            top_cand = t3_res.candidates[0] if t3_res.candidates else None
            return HybridDispatchResult(
                query=query,
                selected_tier=3,
                final_target=top_cand.get("name") if top_cand else None,
                owner_agent=top_cand.get("owner_agent") if top_cand else None,
                confidence=top_cand.get("confidence", 0.0) if top_cand else 0.0,
                status=t3_res.status,
                tier1=t1_res,
                tier2=t2_res,
                tier3=t3_res,
                total_elapsed_ms=total_elapsed,
            )

        total_elapsed = (time.perf_counter() - t0) * 1000.0
        return HybridDispatchResult(
            query=query,
            selected_tier=0,
            final_target=None,
            owner_agent=None,
            confidence=0.0,
            status="no_match",
            total_elapsed_ms=total_elapsed,
        )


def dispatch_query(query: str, tier: str = "all", top_k: int = 5, root: Path | None = None) -> dict[str, Any]:
    """Convenience functional interface for hybrid dispatch."""
    dispatcher = HybridDispatcher(root=root)
    result = dispatcher.dispatch(query, tier=tier, top_k=top_k)
    return asdict(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="3-Tier Hybrid Dispatch Pipeline (Fast-Path Regex -> BM25 -> Structured Ambiguity Gate)"
    )
    parser.add_argument("--query", "-q", required=True, help="User query text to route")
    parser.add_argument(
        "--tier",
        "-t",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Tier to execute (1=Fast-Path, 2=BM25, 3=Ambiguity Gate, all=Cascade pipeline)",
    )
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of top candidate matches to return")
    parser.add_argument("--repo-root", type=str, help="Repository root path override")

    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else DEFAULT_ROOT

    dispatcher = HybridDispatcher(root=root)
    res = dispatcher.dispatch(args.query, tier=args.tier, top_k=args.top_k)

    if args.json:
        print(json.dumps(asdict(res), indent=2))
        return 0

    print("=" * 60)
    print(f"Hybrid Dispatch Result: {res.status.upper()} (Tier {res.selected_tier})")
    print("=" * 60)
    print(f"Query:        {res.query}")
    print(f"Final Target: {res.final_target or 'None'}")
    print(f"Owner Agent:  {res.owner_agent or 'None'}")
    print(f"Confidence:   {res.confidence:.2f}")
    print(f"Total Time:   {res.total_elapsed_ms:.2f} ms")

    if res.tier1 and res.tier1.matched:
        print(f"\n[Tier 1 Fast-Path Match]: {res.tier1.skill} ({res.tier1.owner_agent}) in {res.tier1.elapsed_ms:.2f}ms")
    elif res.tier1 and res.tier1.conflicting_skills:
        print(f"\n[Tier 1 Conflict]: Multi-intent detected across {res.tier1.conflicting_skills}")

    if res.tier2 and res.tier2.candidates:
        print(f"\n[Tier 2 BM25 Top Matches ({res.tier2.elapsed_ms:.2f}ms)]:")
        for i, c in enumerate(res.tier2.candidates[:3], start=1):
            print(f"  {i}. {c.name} ({c.type}, {c.owner_agent}) - score: {c.score:.2f}, conf: {c.confidence:.2f}")

    if res.tier3 and res.tier3.disambiguation_questions:
        print(f"\n[Tier 3 Disambiguation Questions ({res.tier3.elapsed_ms:.2f}ms)]:")
        for q in res.tier3.disambiguation_questions:
            print(f"  ? {q}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
