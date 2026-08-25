"""Generate routing/area-map.md and routing/skill-dispatch.md.

tags: [routing]
routing_hints: [area-map, skill-dispatch, areas.yaml, index]
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import (  # noqa: E402
    AreasYamlError,
    check_areas_consistency,
    load_area_records,
    load_nested_defaults,
)
from md import load_skill_record, parse_frontmatter, skill_paths  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

GENERATOR = "scripts/routing/generate_routing_index.py"
AREA_MAP = ROOT / "routing" / "area-map.md"
SKILL_DISPATCH = ROOT / "routing" / "skill-dispatch.md"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _agent_cell(owner: str) -> str:
    if owner in {"", "—", "none"}:
        return "`none`" if owner == "none" else (owner or "—")
    return f"[`{owner}`](../ai-tooling/agents/{owner}/AGENT.md)"


def render_area_map(repo_root: Path, *, now: str) -> str:
    """Return area-map.md generated from ``repo_root/routing/areas.yaml``."""
    areas = load_area_records(repo_root)
    nested = load_nested_defaults(repo_root)
    lines = [
        "---",
        "doc_kind: routing_map",
        "canonical_id: area-map",
        "topics: [routing, write-back, structure]",
        f"generated_at_utc: {now}",
        f"generator: {GENERATOR}",
        "---",
        "",
        "# Area map",
        "",
        "Generated from [`areas.yaml`](./areas.yaml). Do not hand-edit — run "
        f"`python {GENERATOR}`.",
        "",
        "Match [`skill-dispatch.md`](./skill-dispatch.md) first. Use this table only when no skill row applies.",
        "",
        "## Areas",
        "",
        "| Area | Purpose | Default agent | Load | Write-back |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in areas:
        area_id = row["id"]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{area_id}/`",
                    _md_cell(row.get("purpose", "")),
                    _agent_cell(row.get("default_agent", "—")),
                    _md_cell(row.get("load", "")),
                    _md_cell(row.get("write_back", "")),
                ]
            )
            + " |"
        )
    if nested:
        lines.extend(
            [
                "",
                "## Nested defaults",
                "",
                "| Path | Default agent |",
                "| --- | --- |",
            ]
        )
        for row in nested:
            path = row.get("path", "")
            shown = path if path.endswith("/") else f"{path}/"
            lines.append(f"| `{shown}` | {_agent_cell(row.get('default_agent', '—'))} |")
    lines.append("")
    return "\n".join(lines)


def write_area_map(*, now: str, repo_root: Path | None = None) -> None:
    root = repo_root if repo_root is not None else ROOT
    (root / "routing" / "area-map.md").write_text(
        render_area_map(root, now=now),
        encoding="utf-8",
    )


def collect_skill_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in skill_paths(ROOT):
        rec = load_skill_record(path)
        rows.append(rec)
    return rows


def write_skill_dispatch(*, now: str, rows: list[dict[str, Any]] | None = None) -> int:
    rows = collect_skill_rows() if rows is None else rows
    lines = [
        "---",
        "doc_kind: routing_map",
        "canonical_id: skill-dispatch",
        "topics: [routing, skills, agents]",
        f"generated_at_utc: {now}",
        f"generator: {GENERATOR}",
        "---",
        "",
        "# Skill dispatch",
        "",
        "Generated from `ai-tooling/skills/*/SKILL.md` frontmatter. Do not hand-edit — run "
        f"`python {GENERATOR}`.",
        "",
        "| Skill | Owner agent | Rank | Isolation | When |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        skill_link = f"[`{row['name']}`](../ai-tooling/skills/{row['name']}/SKILL.md)"
        lines.append(
            f"| {skill_link} | {_agent_cell(row['owner_agent'])} | `{row['rank']}` | "
            f"`{row['isolation']}` | {_md_cell(row['description'])} |"
        )

    # Composite skill prerequisites and failure policies section
    lines.extend(
        [
            "",
            "## Composite skill prerequisites and failure policies",
            "",
            "| Skill | Required skills | Delegated skills | In-session skills | Binary prerequisites | Failure policy |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        skill_link = f"[`{row['name']}`](../ai-tooling/skills/{row['name']}/SKILL.md)"
        deps = row.get("dependencies", {})
        req_list = deps.get("required_skills", [])
        del_list = deps.get("delegated_skills", [])
        ins_list = deps.get("in_session_skills", [])
        prereqs_list = row.get("prerequisites", [])

        req_str = ", ".join(f"[`{s}`](../ai-tooling/skills/{s}/SKILL.md)" for s in req_list) if req_list else "—"
        del_str = ", ".join(f"[`{s}`](../ai-tooling/skills/{s}/SKILL.md)" for s in del_list) if del_list else "—"
        ins_str = ", ".join(f"[`{s}`](../ai-tooling/skills/{s}/SKILL.md)" for s in ins_list) if ins_list else "—"
        prereqs_str = ", ".join(f"`{p}`" for p in prereqs_list) if prereqs_list else "—"
        fail_str = f"`{row.get('on_failure', 'abort_and_rollback')}`"

        lines.append(
            f"| {skill_link} | {req_str} | {del_str} | {ins_str} | {prereqs_str} | {fail_str} |"
        )

    lines.append("")
    SKILL_DISPATCH.write_text("\n".join(lines), encoding="utf-8")
    return len(rows)


def main() -> int:
    try:
        mismatches = check_areas_consistency(ROOT)
    except AreasYamlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if mismatches:
        print("error: routing/areas.yaml does not match on-disk areas:", file=sys.stderr)
        for msg in mismatches:
            print(f"  - {msg}", file=sys.stderr)
        return 2

    now = _utc_now()
    write_area_map(now=now)
    n_skills = write_skill_dispatch(now=now)
    n_areas = len(load_area_records(ROOT))
    n_nested = len(load_nested_defaults(ROOT))
    print(f"wrote {AREA_MAP.relative_to(ROOT).as_posix()} ({n_areas} areas, {n_nested} nested defaults)")
    print(f"wrote {SKILL_DISPATCH.relative_to(ROOT).as_posix()} ({n_skills} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
