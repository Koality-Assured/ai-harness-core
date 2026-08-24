"""Shared Markdown frontmatter helpers for repo scripts. Not indexed (underscore)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

REQUIRED_SKILL_HEADINGS = [
    "When to use",
    "When not to use",
    "Criticality",
    "Source of truth",
    "Isolation",
    "How to use",
    "Dry run",
    "Security",
    "Completion gates",
]

RANKS = {"critical", "high", "medium", "low"}
ISOLATION = {"mutate", "read-only"}
MODEL_TIERS = {"fast", "standard", "high", "max"}


try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (fields, body). Fields are parsed YAML dictionary (supports Schema V2)."""
    if not text.startswith("---"):
        return {}, text
    rest = text[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end == -1:
        return {}, text
    raw = rest[:end]
    body = rest[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    if yaml is not None:
        try:
            parsed = yaml.safe_load(raw)
            if isinstance(parsed, dict):
                return parsed, body
        except Exception:
            pass
    return _parse_simple_yaml(raw), body


def _parse_simple_yaml(raw: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    key: str | None = None
    folded: list[str] = []
    folding = False
    for line in raw.splitlines():
        if folding:
            if line.startswith("  ") or line.startswith("\t"):
                folded.append(line.strip())
                continue
            fields[key] = " ".join(folded).strip()
            folding = False
            key = None
            folded = []
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v in {">", ">-", "|", "|-"}:
            key = k
            folding = True
            folded = []
            continue
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fields[k] = v
    if folding and key:
        fields[key] = " ".join(folded).strip()
    return fields


def heading_titles(body: str) -> list[str]:
    titles = []
    for line in body.splitlines():
        if line.startswith("## "):
            titles.append(line[3:].strip())
    return titles


def skill_paths(root: Path) -> list[Path]:
    skills = root / "ai-tooling" / "skills"
    out = []
    for path in sorted(skills.glob("*/SKILL.md")):
        out.append(path)
    return out


def agent_paths(root: Path) -> list[Path]:
    agents = root / "ai-tooling" / "agents"
    out = []
    for path in sorted(agents.glob("*/AGENT.md")):
        out.append(path)
    return out


def agent_ids(root: Path) -> set[str]:
    agents = root / "ai-tooling" / "agents"
    return {p.name for p in agents.iterdir() if p.is_dir() and (p / "AGENT.md").exists()}


def load_skill_record(path: Path) -> dict[str, Any]:
    """Parse a SKILL.md file and return a structured dictionary supporting Schema V2."""
    text = path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)
    folder = path.parent.name
    name = str(fields.get("name", folder))
    desc = str(fields.get("description", ""))
    owner = str(fields.get("owner_agent", "—"))
    rank = str(fields.get("rank", "—"))
    isolation = str(fields.get("isolation", "—"))
    schema_version = str(fields.get("schema_version", "1.0.0"))
    on_failure = str(fields.get("on_failure", "abort_and_rollback"))

    prereqs = fields.get("prerequisites", [])
    if isinstance(prereqs, str):
        prerequisites = [p.strip() for p in prereqs.split(",") if p.strip()]
    elif isinstance(prereqs, list):
        prerequisites = [str(p) for p in prereqs]
    else:
        prerequisites = []

    deps_raw = fields.get("dependencies", {})
    if isinstance(deps_raw, dict):
        dependencies = {
            "required_skills": [str(s) for s in deps_raw.get("required_skills", [])],
            "delegated_skills": [str(s) for s in deps_raw.get("delegated_skills", [])],
            "in_session_skills": [str(s) for s in deps_raw.get("in_session_skills", [])],
        }
    else:
        dependencies = {
            "required_skills": [],
            "delegated_skills": [],
            "in_session_skills": [],
        }

    contracts = fields.get("contracts", {}) if isinstance(fields.get("contracts"), dict) else {}

    topics_raw = fields.get("topics", [])
    if isinstance(topics_raw, str):
        topics = [t.strip() for t in topics_raw.strip("[]").split(",") if t.strip()]
    elif isinstance(topics_raw, list):
        topics = [str(t) for t in topics_raw]
    else:
        topics = []

    hints_raw = fields.get("routing_hints", [])
    if isinstance(hints_raw, str):
        routing_hints = [h.strip() for h in hints_raw.strip("[]").split(",") if h.strip()]
    elif isinstance(hints_raw, list):
        routing_hints = [str(h) for h in hints_raw]
    else:
        routing_hints = []

    return {
        "name": name,
        "path": path,
        "owner_agent": owner,
        "rank": rank,
        "isolation": isolation,
        "description": desc,
        "schema_version": schema_version,
        "on_failure": on_failure,
        "prerequisites": prerequisites,
        "dependencies": dependencies,
        "contracts": contracts,
        "topics": topics,
        "routing_hints": routing_hints,
        "body": body,
    }
