"""Parse routing/areas.yaml (list-of-maps scalars, stdlib only). Not indexed."""

from __future__ import annotations

from pathlib import Path


class AreasYamlError(ValueError):
    """Invalid routing/areas.yaml or mismatch with on-disk areas."""


def parse_areas_yaml(text: str) -> dict[str, list[dict[str, str]]]:
    """Parse the simple areas.yaml shape: top-level keys → lists of scalar maps."""
    sections: dict[str, list[dict[str, str]]] = {}
    current_section: str | None = None
    current_item: dict[str, str] | None = None

    def flush_item() -> None:
        nonlocal current_item
        if current_item is not None:
            if current_section is None:
                raise AreasYamlError("list item before a section key")
            sections.setdefault(current_section, []).append(current_item)
            current_item = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped_comment = raw.split("#", 1)[0].rstrip()
        if not stripped_comment.strip():
            continue
        indent = len(stripped_comment) - len(stripped_comment.lstrip(" "))
        stripped = stripped_comment.strip()

        if indent == 0 and stripped.endswith(":") and not stripped.startswith("-"):
            flush_item()
            current_section = stripped[:-1].strip()
            if not current_section:
                raise AreasYamlError(f"line {lineno}: empty section key")
            sections.setdefault(current_section, [])
            continue

        if current_section is None:
            raise AreasYamlError(f"line {lineno}: unexpected content before a section: {raw!r}")

        if stripped.startswith("- "):
            flush_item()
            current_item = {}
            rest = stripped[2:].strip()
            if rest:
                _assign_field(current_item, rest, lineno)
            continue

        if current_item is None:
            raise AreasYamlError(f"line {lineno}: field outside a list item: {raw!r}")
        _assign_field(current_item, stripped, lineno)

    flush_item()
    return sections


def _assign_field(item: dict[str, str], blob: str, lineno: int) -> None:
    if ":" not in blob:
        raise AreasYamlError(f"line {lineno}: expected key: value, got {blob!r}")
    key, _, value = blob.partition(":")
    key = key.strip()
    if not key:
        raise AreasYamlError(f"line {lineno}: empty field name")
    item[key] = value.strip()


def load_areas_document(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    path = repo_root / "routing" / "areas.yaml"
    if not path.is_file():
        raise AreasYamlError("missing routing/areas.yaml")
    doc = parse_areas_yaml(path.read_text(encoding="utf-8"))
    if "areas" not in doc:
        raise AreasYamlError("routing/areas.yaml missing top-level 'areas:'")
    for i, area in enumerate(doc["areas"]):
        if "id" not in area:
            raise AreasYamlError(f"areas[{i}] missing id")
    return doc


def load_area_records(repo_root: Path) -> list[dict[str, str]]:
    return load_areas_document(repo_root)["areas"]


def load_nested_defaults(repo_root: Path) -> list[dict[str, str]]:
    return load_areas_document(repo_root).get("nested_defaults") or []


def load_area_ids(repo_root: Path) -> set[str]:
    return {row["id"] for row in load_area_records(repo_root)}


def top_level_agent_dirs(repo_root: Path) -> set[str]:
    found: set[str] = set()
    for path in repo_root.iterdir():
        if not path.is_dir() or path.name.startswith("."):
            continue
        if (path / "AGENTS.md").is_file():
            found.add(path.name)
    return found


def check_areas_consistency(repo_root: Path) -> list[str]:
    """Return error strings if yaml ids and on-disk AGENTS.md areas disagree."""
    errors: list[str] = []
    try:
        ids = load_area_ids(repo_root)
    except AreasYamlError as exc:
        return [str(exc)]
    disk = top_level_agent_dirs(repo_root)
    for missing in sorted(disk - ids):
        errors.append(f"top-level {missing}/ has AGENTS.md but is missing from routing/areas.yaml")
    for extra in sorted(ids - disk):
        folder = repo_root / extra
        if not folder.is_dir():
            errors.append(f"routing/areas.yaml id {extra!r} has no folder")
        elif not (folder / "AGENTS.md").is_file():
            errors.append(f"routing/areas.yaml id {extra!r} has no {extra}/AGENTS.md")
        else:
            errors.append(f"routing/areas.yaml id {extra!r} is not a top-level AGENTS.md area")
    return errors
