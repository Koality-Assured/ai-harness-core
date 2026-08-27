"""Validate router structure (areas, catalogs, frontmatter, dispatch, results layout).

tags: [docs, routing]
routing_hints: [router, structure, validation, results-layout]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from areas import (  # noqa: E402
    AreasYamlError,
    check_areas_consistency,
    load_area_ids,
)
from md import agent_ids, parse_frontmatter, skill_paths  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

QMD_EXCLUDED = ("change-history", "scratch")
DOC_SKIP_NAMES = {"README.md"}

# Ops/process pages that must not regress back into docs/ root (docs/standards/ OK).
DOCS_ROOT_FORBIDDEN = (
    "isolation-and-dispatch.md",
    "agent-model-tiers.md",
    "skill-conventions.md",
    "readme-conventions.md",
    "results-conventions.md",
    "docs-maintenance.md",
    "workstation-onboarding.md",
    "retrieval-conventions.md",
)

# Canonical homes after the docs/ops split and routing-index redesign.
OPS_SOT_REQUIRED = (
    "routing/areas.yaml",
    "ai-tooling/skills/skill-conventions.md",
    "supporting/workstation-onboarding.md",
    "supporting/qmd/retrieval-conventions.md",
    "ai-tooling/agents/model-tiers.md",
    "ai-tooling/skills/meta/isolate-work/SKILL.md",
)
GENERATED_MAPS = (
    "routing/area-map.md",
    "routing/skill-dispatch.md",
)


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def check_areas(errors: list[str]) -> None:
    yaml_path = ROOT / "routing" / "areas.yaml"
    if not yaml_path.is_file():
        err(errors, "missing routing/areas.yaml")
        return
    try:
        yaml_ids = load_area_ids(ROOT)
    except AreasYamlError as exc:
        err(errors, f"routing/areas.yaml: {exc}")
        return
    for msg in check_areas_consistency(ROOT):
        err(errors, msg)
    area_map_path = ROOT / "routing" / "area-map.md"
    area_map = area_map_path.read_text(encoding="utf-8") if area_map_path.is_file() else ""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for area in sorted(yaml_ids):
        if f"`{area}/`" not in area_map:
            err(errors, f"routing/area-map.md missing `{area}/` row")
        if f"`{area}/`" not in readme and f"]({area}/)" not in readme:
            err(errors, f"root README.md layout missing {area}/")


def check_docs(errors: list[str]) -> None:
    docs = ROOT / "docs"
    for path in sorted(docs.rglob("*.md")):
        if path.name in DOC_SKIP_NAMES or path.name == "AGENTS.md":
            continue
        text = path.read_text(encoding="utf-8")
        fields, _ = parse_frontmatter(text)
        rel = path.relative_to(ROOT).as_posix()
        if not fields:
            err(errors, f"{rel}: missing frontmatter")
            continue
        if "doc_kind" not in fields:
            err(errors, f"{rel}: missing doc_kind")
        if "canonical_id" not in fields:
            err(errors, f"{rel}: missing canonical_id")


def check_ops_docs_split(errors: list[str]) -> None:
    """Fail if ops pages regress into docs/ root or canonical SoT files are missing."""
    docs = ROOT / "docs"
    for name in DOCS_ROOT_FORBIDDEN:
        path = docs / name
        if path.is_file():
            err(
                errors,
                f"docs/{name}: ops/process page must not live at docs/ root "
                f"(moved out of docs/; docs/standards/ is allowed)",
            )
    for rel in OPS_SOT_REQUIRED:
        if not (ROOT / rel).is_file():
            err(errors, f"missing SoT after docs/ops split: {rel}")
    for rel in GENERATED_MAPS:
        path = ROOT / rel
        if not path.is_file():
            err(errors, f"missing generated map: {rel}")
            continue
        fields, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if "generator" not in fields:
            err(errors, f"{rel}: missing generator: in frontmatter")


def check_scripts(errors: list[str]) -> None:
    tag_re = re.compile(r"tags:\s*\[", re.I)
    scripts_root = ROOT / "scripts"
    for path in sorted(scripts_root.rglob("*.py")):
        rel_parts = path.relative_to(scripts_root).parts
        if rel_parts[0] == "_lib" or path.name.startswith("_"):
            continue
        doc = path.read_text(encoding="utf-8")[:2000]
        if "tags:" not in doc and not tag_re.search(doc):
            err(errors, f"{path.relative_to(ROOT).as_posix()}: missing tags: in docstring")


def check_skills_agents(errors: list[str], *, warnings: list[str]) -> None:
    """Agent registration is folder + AGENT.md (+ A2A card). README is human-only.

    Missing README table rows must not fail validation. If a README table exists,
    emit warnings for human consistency only.
    """
    owners = agent_ids(ROOT)
    if not owners:
        err(errors, "no agents with AGENT.md under ai-tooling/agents/")
    skills = skill_paths(ROOT)
    if not skills:
        err(errors, "no SKILL.md files under ai-tooling/skills/")

    skills_readme_path = ROOT / "ai-tooling" / "skills" / "README.md"
    agents_readme_path = ROOT / "ai-tooling" / "agents" / "README.md"
    skills_readme = (
        skills_readme_path.read_text(encoding="utf-8") if skills_readme_path.is_file() else ""
    )
    agents_readme = (
        agents_readme_path.read_text(encoding="utf-8") if agents_readme_path.is_file() else ""
    )

    for path in skills:
        slug = path.parent.name
        if (
            skills_readme
            and f"/{slug}/" not in skills_readme
            and f"/{slug})" not in skills_readme
            and f"/{slug}]" not in skills_readme
        ):
            warnings.append(
                f"human consistency: skill {slug} not listed in ai-tooling/skills/README.md"
            )
    for owner in sorted(owners):
        if agents_readme and owner not in agents_readme:
            warnings.append(
                f"human consistency: agent {owner} not listed in ai-tooling/agents/README.md"
            )
        agent_file = ROOT / "ai-tooling" / "agents" / owner / "AGENT.md"
        if not agent_file.exists():
            err(errors, f"missing agent definition ai-tooling/agents/{owner}/AGENT.md")


def check_qmd_exclusions(errors: list[str], *, warnings: list[str]) -> None:
    """Exclusions are documented on the agent SoT page, not the human README."""
    sot = ROOT / "supporting" / "qmd" / "query-pattern.md"
    if not sot.is_file():
        warnings.append(
            "supporting/qmd/query-pattern.md missing; skipped exclusion doc check "
            "(expected after docs/supporting merge)"
        )
    else:
        text = sot.read_text(encoding="utf-8")
        for name in QMD_EXCLUDED:
            if name not in text:
                err(
                    errors,
                    f"supporting/qmd/query-pattern.md should mention exclusion {name}/",
                )

    setup = (ROOT / "scripts" / "qmd" / "setup_qmd_collections.py").read_text(encoding="utf-8")
    for name in QMD_EXCLUDED:
        # Only fail if listed as a collection entry, not mere docstring mentions.
        if f'("{name}", "{name}"' in setup or f"('{name}', '{name}'" in setup:
            err(errors, f"setup_qmd_collections.py must not add {name}/ as a collection")


def check_dispatch(errors: list[str]) -> None:
    dispatch = ROOT / "routing" / "skill-dispatch.md"
    if not dispatch.exists():
        err(errors, "missing routing/skill-dispatch.md (run generate_routing_index.py)")
        return
    text = dispatch.read_text(encoding="utf-8")
    for path in skill_paths(ROOT):
        slug = path.parent.name
        if f"`{slug}`" not in text:
            err(errors, f"skill-dispatch.md missing {slug} (regenerate)")


def check_memory(errors: list[str]) -> None:
    mem = ROOT / "ai-tooling" / "memory"
    user = mem / "user"
    agent = mem / "agent"
    model = mem / "model"
    if not user.is_dir():
        err(errors, "missing ai-tooling/memory/user/")
    if not agent.is_dir():
        err(errors, "missing ai-tooling/memory/agent/")
    if not model.is_dir():
        err(errors, "missing ai-tooling/memory/model/")
    for flat in sorted(mem.glob("*.md")):
        if flat.name in {"README.md", "AGENTS.md"}:
            continue
        err(
            errors,
            f"{flat.relative_to(ROOT).as_posix()}: thread files must live under "
            "memory/user/<git-identity>/, memory/agent/<owner_agent_id>/, or memory/model/<model-family>/",
        )
    for path in sorted(mem.rglob("*.md")):
        if path.name in {"README.md", "AGENTS.md"}:
            continue
        rel = path.relative_to(mem).as_posix()
        if not (rel.startswith("user/") or rel.startswith("agent/") or rel.startswith("model/")):
            continue
        text = path.read_text(encoding="utf-8")
        if "**Status:**" not in text:
            err(errors, f"{path.relative_to(ROOT).as_posix()}: missing Status")
        if "**Last updated:**" not in text:
            err(errors, f"{path.relative_to(ROOT).as_posix()}: missing Last updated")


ALLOWED_RESULTS_FILES = frozenset({"AGENTS.md", "README.md", "results-conventions.md"})
ALLOWED_RESULTS_FAMILIES = frozenset(
    {"reports", "research", "diagrams", "threat-model", "as-code", "cost-layers"}
)
RETIRED_REVIEWS_DIR = "reviews"
GITKEEP_NAME = ".gitkeep"


def check_results_layout(errors: list[str], *, root: Path | None = None) -> None:
    """Fail leftover scratch-shaped dirs and antagonistic review runs under results/.

    Inspects ``results/`` immediate children only, plus one extra level into
    ``results/reviews/`` when that directory exists. Does not walk family trees.
    """
    base = ROOT if root is None else root
    results = base / "results"
    if not results.is_dir():
        err(errors, "missing results/ directory")
        return

    allowed_family_csv = ", ".join(sorted(ALLOWED_RESULTS_FAMILIES))
    allowed_file_csv = ", ".join(sorted(ALLOWED_RESULTS_FILES))

    for child in sorted(results.iterdir(), key=lambda p: p.name):
        name = child.name
        if child.is_file():
            if name not in ALLOWED_RESULTS_FILES:
                err(
                    errors,
                    f"results/{name}: unexpected top-level file "
                    f"(allowed: {allowed_file_csv})",
                )
            continue
        if not child.is_dir():
            err(errors, f"results/{name}: unexpected top-level entry")
            continue
        if name in ALLOWED_RESULTS_FAMILIES:
            continue
        if name == RETIRED_REVIEWS_DIR:
            _check_retired_reviews(errors, child)
            continue
        err(
            errors,
            f"results/{name}/: unexpected top-level directory "
            f"(allowed families: {allowed_family_csv}; "
            "retired reviews/.gitkeep only)",
        )


def _check_retired_reviews(errors: list[str], reviews: Path) -> None:
    """Allow ``results/reviews/.gitkeep`` only; fail topic run directories."""
    for child in sorted(reviews.iterdir(), key=lambda p: p.name):
        if child.is_file() and child.name == GITKEEP_NAME:
            continue
        if child.is_dir():
            err(
                errors,
                f"results/reviews/{child.name}/: antagonistic review runs must not "
                "live under results/ (interim notes belong in scratch/)",
            )
            continue
        err(
            errors,
            f"results/reviews/{child.name}: unexpected file "
            "(only .gitkeep is allowed under retired reviews/)",
        )


def check_context_budget_limits(errors: list[str]) -> None:
    try:
        from validate_context_budget import check_context_budgets
        ok, _, budget_errors = check_context_budgets(ROOT)
        if not ok:
            errors.extend(budget_errors)
    except Exception as exc:
        err(errors, f"context budget validation failed: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Alias: validation never mutates")
    args = parser.parse_args(argv)
    errors: list[str] = []
    warnings: list[str] = []
    check_areas(errors)
    check_docs(errors)
    check_ops_docs_split(errors)
    check_scripts(errors)
    check_skills_agents(errors, warnings=warnings)
    check_qmd_exclusions(errors, warnings=warnings)
    check_dispatch(errors)
    check_memory(errors)
    check_results_layout(errors)
    check_context_budget_limits(errors)
    payload = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(payload, indent=2))
    elif errors:
        print(f"FAIL ({len(errors)})")
        for e in errors:
            print(f"  - {e}")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print("OK router structure")
        for w in warnings:
            print(f"  ! {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())