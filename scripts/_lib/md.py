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
REQUIRED_SKILL_SCHEMA_VERSION = "2.0.0"


def check_required_skill_v2_contracts(
    schema_version: object,
    contracts: object,
    *,
    skill_label: str | None = None,
) -> list[str]:
    """Return errors when Schema V2 version or contracts are missing/empty.

    ``schema_version`` is required and must be ``\"2.0.0\"``. Do not default a
    missing version to ``1.0.0`` to skip these checks. ``contracts`` must be a
    mapping with non-empty ``inputs`` and ``outputs`` lists of strings.

    Shared by ``validate_skill.py`` and ``resolve_skill_graph.py`` so the two
    validators cannot disagree.
    """
    prefix = f"Skill {skill_label!r}: " if skill_label else ""
    errors: list[str] = []
    version = "" if schema_version is None else str(schema_version).strip()
    if not version:
        errors.append(f"{prefix}schema_version missing (expected '{REQUIRED_SKILL_SCHEMA_VERSION}')")
    elif version != REQUIRED_SKILL_SCHEMA_VERSION:
        errors.append(
            f"{prefix}schema_version {version!r} != {REQUIRED_SKILL_SCHEMA_VERSION!r}"
        )

    if contracts is None or (isinstance(contracts, dict) and not contracts):
        errors.append(
            f"{prefix}Schema V2 contracts mapping missing (contracts.inputs, contracts.outputs)"
        )
    elif not isinstance(contracts, dict):
        errors.append(
            f"{prefix}Schema V2 contracts must be a mapping with 'inputs' and 'outputs'"
        )
    else:
        inputs = contracts.get("inputs")
        outputs = contracts.get("outputs")
        if inputs is None or not isinstance(inputs, list) or not inputs:
            errors.append(f"{prefix}Schema V2 contracts.inputs must be non-empty")
        elif not all(isinstance(item, str) and item.strip() for item in inputs):
            errors.append(f"{prefix}Schema V2 contracts.inputs items must be non-empty strings")
        if outputs is None or not isinstance(outputs, list) or not outputs:
            errors.append(f"{prefix}Schema V2 contracts.outputs must be non-empty")
        elif not all(isinstance(item, str) and item.strip() for item in outputs):
            errors.append(f"{prefix}Schema V2 contracts.outputs items must be non-empty strings")
    return errors


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


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse the schema's small YAML subset when PyYAML is unavailable.

    The harness frontmatter uses mappings, block lists, inline lists, and folded
    descriptions.  This is deliberately not a general YAML parser; it prevents
    an optional dependency from silently flattening nested keys into a false
    top-level field during offline validation.
    """
    lines = raw.splitlines()

    def indentation(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def scalar(value: str) -> Any:
        value = value.strip()
        if value in {"[]", "{}"}:
            return [] if value == "[]" else {}
        if value.startswith("[") and value.endswith("]"):
            return [scalar(item) for item in value[1:-1].split(",") if item.strip()]
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        if value.isdigit():
            return int(value)
        if value in {"true", "false"}:
            return value == "true"
        if value in {"null", "~"}:
            return None
        return value

    def next_content(start: int) -> int | None:
        for pos in range(start, len(lines)):
            stripped = lines[pos].strip()
            if stripped and not stripped.startswith("#"):
                return pos
        return None

    def folded(start: int, parent_indent: int, literal: bool) -> tuple[str, int]:
        parts: list[str] = []
        pos = start
        while pos < len(lines):
            line = lines[pos]
            if line.strip() and indentation(line) <= parent_indent:
                break
            if line.strip():
                parts.append(line.strip())
            pos += 1
        return ("\n" if literal else " ").join(parts).strip(), pos

    def block(start: int, indent: int) -> tuple[Any, int]:
        pos = start
        first = next_content(pos)
        if first is None or indentation(lines[first]) < indent:
            return {}, pos
        is_list = lines[first].lstrip().startswith("- ") and indentation(lines[first]) == indent
        result: Any = [] if is_list else {}
        pos = first
        while pos < len(lines):
            line = lines[pos]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                pos += 1
                continue
            current_indent = indentation(line)
            if current_indent < indent or current_indent != indent:
                break
            if is_list:
                if not stripped.startswith("- "):
                    break
                result.append(scalar(stripped[2:]))
                pos += 1
                continue
            if ":" not in stripped:
                pos += 1
                continue
            key, _, value = stripped.partition(":")
            value = value.strip()
            pos += 1
            if value in {">", ">-", "|", "|-"}:
                result[key], pos = folded(pos, current_indent, value.startswith("|"))
            elif value:
                result[key] = scalar(value)
                continuation, next_pos = folded(pos, current_indent, literal=False)
                if continuation:
                    result[key] = f"{result[key]} {continuation}".strip()
                    pos = next_pos
            else:
                child = next_content(pos)
                child_is_root_list = child is not None and lines[child].lstrip().startswith("- ")
                if child is None or indentation(lines[child]) < current_indent or (
                    indentation(lines[child]) == current_indent and not child_is_root_list
                ):
                    result[key] = {}
                else:
                    result[key], pos = block(pos, indentation(lines[child]))
        return result, pos

    parsed, _ = block(0, 0)
    return parsed if isinstance(parsed, dict) else {}


def heading_titles(body: str) -> list[str]:
    titles = []
    for line in body.splitlines():
        if line.startswith("## "):
            titles.append(line[3:].strip())
    return titles


def skill_paths(root: Path) -> list[Path]:
    skills = root / "ai-tooling" / "skills"
    out = []
    if not skills.exists():
        return out
    for path in sorted(skills.rglob("SKILL.md")):
        if any(part.startswith(".") for part in path.parts):
            continue
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
    raw_schema = fields.get("schema_version")
    schema_version = str(raw_schema).strip() if raw_schema is not None else ""
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
