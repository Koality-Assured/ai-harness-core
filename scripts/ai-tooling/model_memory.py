"""Search, validate, and propose promotion of model-family capability memory.

tags: [ai-tooling, memory]
routing_hints: [model-memory, model-capability-memory, capability-retrieval, promote-model-learning]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import AreasYamlError, load_area_records  # noqa: E402
from md import parse_frontmatter  # noqa: E402
from paths import resolve_repo_root  # noqa: E402

MODEL_FAMILIES = ("cursor", "gpt", "claude", "gemini")
MODEL_MEMORY_REL = Path("ai-tooling") / "memory" / "model"
SKIP_FILENAMES = frozenset({"AGENTS.md", "README.md", ".gitkeep"})
ALLOWED_ROOT_FILES = frozenset({"AGENTS.md", "README.md", ".gitkeep"})
ALLOWED_NON_RECORD_FILES = frozenset({".gitkeep"})

CATEGORY_SUCCESS = "success"
CATEGORY_UNAVAILABLE = "unavailable"
CATEGORIES = (CATEGORY_SUCCESS, CATEGORY_UNAVAILABLE)

SUCCESS_ALIASES = frozenset(
    {
        "success",
        "successful",
        "successful-capability",
        "successful-capability-execution",
        "how",
        "successful capability execution",
        "successful capability execution/how",
    }
)
UNAVAILABLE_ALIASES = frozenset(
    {
        "unavailable",
        "failed",
        "unavailable-or-failed",
        "unavailable-failed",
        "recovery",
        "why",
        "unavailable or failed capability",
        "unavailable or failed capability/why/recovery",
        "unavailable/failed capability",
        "unavailable/failed capability/why/recovery",
    }
)

DURABLE_OWNING_AREAS = frozenset(
    {
        "ai-tooling",
        "docs",
        "projects",
        "references",
        "research",
        "results",
        "routing",
        "scripts",
        "supporting",
    }
)
NON_OWNING_AREAS = frozenset({"scratch", "actionable", "change-history"})

SECRET_VALUE_RE = re.compile(
    r"(?i)\b("
    r"sk-(?!EXAMPLE)(?:ant-|proj-|live-)?[a-zA-Z0-9_-]{16,}"
    r"|ghp_[a-zA-Z0-9]{20,}"
    r"|github_pat_[a-zA-Z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"
    r"|Bearer\s+\S+"
    r")\b"
)
PERSONAL_PATH_RE = re.compile(
    r"(?i)(?:[a-z]:\\users\\(?!public\b|default\b|example\b|placeholder\b)[^\\\s]+"
    r"|/users/(?!shared\b|example\b|placeholder\b)[^/\s]+"
    r"|/home/(?!example\b|placeholder\b)[^/\s]+"
    r"|%userprofile%|%localappdata%)"
)
PICKER_ID_RE = re.compile(
    r"(?i)\b(?:picker[_-]?id|model[_-]?picker|host[_-]?picker)(?:\s*[:=]\s*\S+)?"
)

SNIPPET_MAX = 160


class UsageError(ValueError):
    """Invalid CLI arguments or unusable paths."""


def model_memory_root(repo_root: Path) -> Path:
    return repo_root / MODEL_MEMORY_REL


def posix_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def canonicalize_category(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = " ".join(str(raw).strip().lower().replace("_", "-").split())
    if not key:
        return None
    if key in SUCCESS_ALIASES:
        return CATEGORY_SUCCESS
    if key in UNAVAILABLE_ALIASES:
        return CATEGORY_UNAVAILABLE
    return None


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_under_root(raw: str, repo_root: Path) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def scan_forbidden(text: str) -> list[str]:
    """Return discipline errors for secret-like, personal, or picker content."""
    errors: list[str] = []
    if SECRET_VALUE_RE.search(text):
        errors.append("secret-like token")
    if PERSONAL_PATH_RE.search(text):
        errors.append("personal path")
    if PICKER_ID_RE.search(text):
        errors.append("host picker identifier")
    return errors


def redact_text(text: str) -> str:
    out = SECRET_VALUE_RE.sub("[REDACTED]", text)
    out = PERSONAL_PATH_RE.sub("[REDACTED_PATH]", out)
    out = PICKER_ID_RE.sub("[REDACTED_PICKER]", out)
    return out


def _heading_categories(body: str) -> set[str]:
    found: set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            canon = canonicalize_category(title)
            if canon:
                found.add(canon)
    return found


def _path_category(path: Path, family_dir: Path) -> str | None:
    try:
        rel = path.resolve().parent.relative_to(family_dir.resolve())
    except ValueError:
        return None
    for part in rel.parts:
        canon = canonicalize_category(part)
        if canon:
            return canon
    return None


def resolve_category(
    path: Path, family_dir: Path, fields: dict[str, Any], body: str
) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    from_fm = canonicalize_category(
        str(fields["category"]) if "category" in fields and fields["category"] is not None else None
    )
    if "category" in fields and fields["category"] is not None and from_fm is None:
        errors.append(f"unknown category {fields['category']!r} (want success or unavailable)")
    from_path = _path_category(path, family_dir)
    from_headings = _heading_categories(body)
    if len(from_headings) > 1:
        errors.append("record mixes both durable categories; keep exactly one")

    candidates = {c for c in (from_fm, from_path) if c}
    if len(from_headings) == 1:
        heading_cat = next(iter(from_headings))
        if candidates and heading_cat not in candidates:
            errors.append("category frontmatter/path does not match heading")
        candidates.add(heading_cat)

    if len(candidates) > 1:
        errors.append("conflicting category signals (frontmatter vs path)")
        return None, errors
    if not candidates:
        errors.append(
            "missing two-category discipline "
            "(category: success|unavailable, or a success/unavailable folder or heading)"
        )
        return None, errors
    return next(iter(candidates)), errors


def record_family(path: Path, model_root: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(model_root.resolve())
    except ValueError:
        return None
    if not rel.parts:
        return None
    family = rel.parts[0]
    if family in MODEL_FAMILIES:
        return family
    return None


def iter_record_paths(repo_root: Path, family: str | None = None) -> list[Path]:
    """Markdown records under ai-tooling/memory/model/ only (no repo-wide walk)."""
    root = model_memory_root(repo_root)
    if not root.is_dir():
        return []
    families = (family,) if family else MODEL_FAMILIES
    out: list[Path] = []
    for fam in families:
        family_dir = root / fam
        if not family_dir.is_dir():
            continue
        for path in sorted(family_dir.rglob("*.md")):
            if any(part.startswith(".") for part in path.relative_to(family_dir).parts):
                continue
            if path.name in SKIP_FILENAMES:
                continue
            out.append(path)
    return out


def load_record(path: Path, repo_root: Path) -> dict[str, Any]:
    model_root = model_memory_root(repo_root)
    family = record_family(path, model_root)
    text = path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)
    family_dir = model_root / family if family else model_root
    category, cat_errors = resolve_category(path, family_dir, fields, body)
    title = ""
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = path.stem.replace("-", " ")
    return {
        "path": path,
        "relpath": posix_rel(path, repo_root),
        "family": family,
        "category": category,
        "category_errors": cat_errors,
        "fields": fields,
        "body": body,
        "text": text,
        "title": title,
        "forbidden": scan_forbidden(text),
    }


def check_record(path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    model_root = model_memory_root(repo_root)
    if not _is_under(path, model_root):
        errors.append("record is not under ai-tooling/memory/model/")
        return errors
    rel = path.resolve().relative_to(model_root.resolve())
    if rel.parts and rel.parts[0] in {"user", "agent"}:
        errors.append("do not copy user or agent memory into model memory")
        return errors
    family = record_family(path, model_root)
    if family is None:
        errors.append("record is not under an allowed model family folder")
        return errors
    try:
        rec = load_record(path, repo_root)
    except OSError as exc:
        return [f"cannot read {posix_rel(path, repo_root)}: {exc}"]
    errors.extend(rec["category_errors"])
    errors.extend(rec["forbidden"])
    return errors


def validate_tree(repo_root: Path, family: str | None = None) -> dict[str, Any]:
    root = model_memory_root(repo_root)
    errors: list[str] = []
    warnings: list[str] = []
    record_count = 0
    seen_families: list[str] = []

    if not root.exists():
        return {
            "ok": True,
            "root": MODEL_MEMORY_REL.as_posix(),
            "families": [],
            "records": 0,
            "errors": [],
            "warnings": ["model memory directory is absent"],
        }
    if not root.is_dir():
        return {
            "ok": False,
            "root": MODEL_MEMORY_REL.as_posix(),
            "families": [],
            "records": 0,
            "errors": [f"{MODEL_MEMORY_REL.as_posix()} is not a directory"],
            "warnings": [],
        }

    for child in sorted(root.iterdir()):
        if child.is_file():
            if child.name not in ALLOWED_ROOT_FILES:
                errors.append(
                    f"unexpected file at model memory root: {child.name} "
                    "(records must live under a family folder)"
                )
            continue
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        if child.name not in MODEL_FAMILIES:
            errors.append(f"unknown model family folder {child.name!r}")
            continue
        if family is not None and child.name != family:
            continue
        seen_families.append(child.name)
        for path in sorted(child.rglob("*")):
            if not path.is_file():
                continue
            if any(part.startswith(".") and part != path.name for part in path.relative_to(child).parts):
                continue
            if path.name in ALLOWED_NON_RECORD_FILES:
                continue
            if path.suffix.lower() != ".md":
                errors.append(
                    f"{posix_rel(path, repo_root)}: files must be markdown "
                    "(or .gitkeep)"
                )
                continue
            if path.name in SKIP_FILENAMES:
                continue
            record_count += 1
            rec_errs = check_record(path, repo_root)
            for err in rec_errs:
                errors.append(f"{posix_rel(path, repo_root)}: {err}")

    if family is not None and family not in seen_families and (root / family).is_dir():
        seen_families.append(family)

    return {
        "ok": not errors,
        "root": MODEL_MEMORY_REL.as_posix(),
        "families": seen_families,
        "records": record_count,
        "errors": errors,
        "warnings": warnings,
    }


def _query_terms(query: str) -> list[str]:
    return [t for t in query.lower().split() if t]


def _record_matches(rec: dict[str, Any], terms: list[str]) -> bool:
    hay = f"{rec['relpath']}\n{rec['title']}\n{rec['text']}".lower()
    return all(term in hay for term in terms)


def _snippet(rec: dict[str, Any], terms: list[str]) -> str:
    blob = redact_text(rec["text"])
    lines = blob.splitlines()
    for line in lines:
        low = line.lower()
        if any(term in low for term in terms):
            stripped = line.strip()
            if len(stripped) > SNIPPET_MAX:
                return stripped[: SNIPPET_MAX - 1] + "…"
            return stripped
    fallback = redact_text(rec["title"] or rec["relpath"])
    return fallback[:SNIPPET_MAX]


def search_records(repo_root: Path, family: str, query: str) -> dict[str, Any]:
    if family not in MODEL_FAMILIES:
        raise UsageError(f"unknown model family {family!r}; want {', '.join(MODEL_FAMILIES)}")
    terms = _query_terms(query)
    if not terms:
        raise UsageError("query must contain at least one term")
    hits: list[dict[str, Any]] = []
    for path in iter_record_paths(repo_root, family):
        rec = load_record(path, repo_root)
        if not _record_matches(rec, terms):
            continue
        warnings = list(rec["forbidden"]) + list(rec["category_errors"])
        hits.append(
            {
                "path": rec["relpath"],
                "family": rec["family"],
                "category": rec["category"],
                "title": redact_text(rec["title"]),
                "snippet": _snippet(rec, terms),
                "warnings": warnings,
            }
        )
    return {
        "ok": True,
        "model": family,
        "query": query,
        "count": len(hits),
        "records": hits,
    }


def owning_area_for_target(target: Path, repo_root: Path) -> tuple[str | None, str | None, list[str]]:
    """Return (area_id, owner_agent, errors) for a promotion target."""
    errors: list[str] = []
    if not _is_under(target, repo_root):
        return None, None, ["target is outside the repository"]
    rel = target.resolve().relative_to(repo_root.resolve())
    if not rel.parts:
        return None, None, ["target must be a path under an owning source area"]
    area = rel.parts[0]
    owner_agent: str | None = None
    try:
        records = load_area_records(repo_root)
        by_id = {row["id"]: row for row in records}
    except (AreasYamlError, OSError):
        by_id = {}
    if area in NON_OWNING_AREAS:
        errors.append(f"target area {area!r} is not an owning source area")
        return area, None, errors
    if area not in DURABLE_OWNING_AREAS and area not in by_id:
        errors.append(f"target area {area!r} is not an owning source area")
        return area, None, errors
    if area not in DURABLE_OWNING_AREAS:
        errors.append(f"target area {area!r} is not a durable owning source area")
        return area, by_id.get(area, {}).get("default_agent"), errors
    if by_id and area in by_id:
        agent = by_id[area].get("default_agent")
        if agent and agent != "none":
            owner_agent = agent
    memory_user = repo_root / "ai-tooling" / "memory" / "user"
    memory_agent = repo_root / "ai-tooling" / "memory" / "agent"
    memory_model = model_memory_root(repo_root)
    if _is_under(target, memory_user) or _is_under(target, memory_agent):
        errors.append("do not copy user or agent memory; target must be an owning source area")
    if _is_under(target, memory_model):
        errors.append("promotion target must be an owning source area, not model memory")
    return area, owner_agent, errors


def propose_promote(
    repo_root: Path,
    record_raw: str,
    target_raw: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    record_path = resolve_under_root(record_raw, repo_root)
    target_path = resolve_under_root(target_raw, repo_root)
    errors: list[str] = []
    if not record_path.is_file():
        errors.append(f"record does not exist: {posix_rel(record_path, repo_root)}")
    else:
        errors.extend(check_record(record_path, repo_root))

    area, owner_agent, area_errors = owning_area_for_target(target_path, repo_root)
    errors.extend(area_errors)

    wrote = False
    rec_meta: dict[str, Any] | None = None
    if record_path.is_file() and _is_under(record_path, model_memory_root(repo_root)):
        rec_meta = load_record(record_path, repo_root)

    proposal = {
        "action": "promote",
        "record": posix_rel(record_path, repo_root),
        "family": rec_meta["family"] if rec_meta else None,
        "category": rec_meta["category"] if rec_meta else None,
        "title": redact_text(rec_meta["title"]) if rec_meta else None,
        "target": posix_rel(target_path, repo_root),
        "owning_area": area,
        "owner_agent": owner_agent,
        "dry_run": dry_run,
        "wrote": wrote,
        "handoff": (
            f"Hand this proposal to {owner_agent or 'the destination area owner'} "
            "in that owner's isolated worktree. Do not copy user or agent memory."
        ),
    }
    return {
        "ok": not errors,
        "dry_run": dry_run,
        "wrote": wrote,
        "proposal": proposal,
        "errors": errors,
    }


def _emit(payload: dict[str, Any], *, as_json: bool, human_lines: list[str]) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    for line in human_lines:
        print(line)


def cmd_search(args: argparse.Namespace, repo_root: Path) -> int:
    try:
        payload = search_records(repo_root, args.model, args.query)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    lines = [
        f"{payload['count']} record(s) for model={payload['model']!r} query={payload['query']!r}"
    ]
    for rec in payload["records"]:
        cat = rec["category"] or "uncategorized"
        lines.append(f"- [{cat}] {rec['path']}: {rec['title']}")
        if rec.get("snippet"):
            lines.append(f"    {rec['snippet']}")
    _emit(payload, as_json=args.json, human_lines=lines)
    return 0


def cmd_promote(args: argparse.Namespace, repo_root: Path) -> int:
    payload = propose_promote(
        repo_root,
        args.record,
        args.target,
        dry_run=True,
    )
    # Promotion is always a proposal and never writes, with or without --dry-run.
    payload["wrote"] = False
    payload["proposal"]["wrote"] = False
    payload["dry_run"] = True
    payload["proposal"]["dry_run"] = True
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if payload["ok"]:
            prop = payload["proposal"]
            print(f"PROPOSE {prop['record']} -> {prop['target']}")
            print(f"  area={prop['owning_area']} owner={prop['owner_agent']}")
            print(f"  wrote={prop['wrote']} dry_run={prop['dry_run']}")
            print(f"  {prop['handoff']}")
        else:
            print("FAIL promote proposal")
            for err in payload["errors"]:
                print(f"  - {err}")
    return 0 if payload["ok"] else 1


def cmd_validate(args: argparse.Namespace, repo_root: Path) -> int:
    family = args.model
    payload = validate_tree(repo_root, family)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        status = "OK" if payload["ok"] else "FAIL"
        print(
            f"{status} {payload['root']} "
            f"families={payload['families']} records={payload['records']}"
        )
        for err in payload["errors"]:
            print(f"  - {err}")
        for warn in payload["warnings"]:
            print(f"  ! {warn}")
    return 0 if payload["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    shared.add_argument(
        "--repo-root",
        metavar="DIR",
        help="Override repository root (for tests / worktrees)",
    )
    parser = argparse.ArgumentParser(
        description="Search, validate, and propose promotion of model-family capability memory.",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser(
        "search",
        help="Query markdown records under ai-tooling/memory/model/<family>/",
        parents=[shared],
    )
    p_search.add_argument(
        "--model",
        required=True,
        choices=MODEL_FAMILIES,
        help="Model family (cursor, gpt, claude, gemini)",
    )
    p_search.add_argument("--query", required=True, help="Search terms (AND, case-insensitive)")

    p_promote = sub.add_parser(
        "promote",
        help="Validate a record and emit a source-area promotion proposal (never writes)",
        parents=[shared],
    )
    p_promote.add_argument("--record", required=True, help="Path to a model-memory markdown record")
    p_promote.add_argument("--target", required=True, help="Owning source-area destination path")
    p_promote.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write (promotion is always a proposal; this flag is required by callers)",
    )

    p_validate = sub.add_parser(
        "validate",
        help="Check family folders, two-category markdown discipline, and secret-like strings",
        parents=[shared],
    )
    p_validate.add_argument(
        "--model",
        choices=MODEL_FAMILIES,
        help="Limit validation to one family",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2
    repo_root = resolve_repo_root(args.repo_root)
    if args.cmd == "search":
        return cmd_search(args, repo_root)
    if args.cmd == "promote":
        return cmd_promote(args, repo_root)
    if args.cmd == "validate":
        return cmd_validate(args, repo_root)
    print("error: unknown command", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
