"""Validate one or all skills against skill-conventions.md.

tags: [ai-tooling, routing]
routing_hints: [skills, dry-run, template, schema-v2]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from md import (  # noqa: E402
    ISOLATION,
    RANKS,
    REQUIRED_SKILL_HEADINGS,
    agent_ids,
    check_required_skill_v2_contracts,
    heading_titles,
    parse_frontmatter,
    skill_paths,
)
from paths import REPO_ROOT as ROOT  # noqa: E402

NAME_MAX = 64
DESC_MAX = 1024
BODY_MAX_LINES = 500


def check_skill(path: Path, owners: set[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)
    folder = path.parent.name
    name = fields.get("name", "")
    desc = fields.get("description", "")
    owner = fields.get("owner_agent", "")
    rank = fields.get("rank", "")
    isolation = fields.get("isolation", "")

    if not fields:
        errors.append("missing YAML frontmatter")
        return errors
    if name != folder:
        errors.append(f"name {name!r} != folder {folder!r}")
    if not name or len(name) > NAME_MAX or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in name):
        errors.append("name must be kebab-case, max 64 chars")
    if not desc:
        errors.append("description missing")
    elif len(desc) > DESC_MAX:
        errors.append("description exceeds 1024 chars")
    else:
        low = desc.lower()
        if "use when" not in low:
            errors.append("description must include 'Use when'")
    if owner not in owners:
        errors.append(f"owner_agent {owner!r} has no AGENT.md")
    if rank not in RANKS:
        errors.append(f"rank must be one of {sorted(RANKS)}")
    if isolation not in ISOLATION:
        errors.append("isolation must be mutate or read-only")
    errors.extend(
        check_required_skill_v2_contracts(
            fields.get("schema_version"),
            fields.get("contracts"),
        )
    )

    titles = heading_titles(body)
    for required in REQUIRED_SKILL_HEADINGS:
        if required not in titles:
            errors.append(f"missing ## {required}")
    lines = body.count("\n") + 1
    if lines > BODY_MAX_LINES:
        errors.append(f"body has {lines} lines (max {BODY_MAX_LINES})")
    if "\\" in text and "scripts\\" in text:
        errors.append("Windows-style path in skill body")
    low = text.lower()
    if "inherits critical cost layers" not in low:
        errors.append(
            "must inherit Critical cost layers (qmd, ast-grep, and Headroom) in the skill body"
        )
    elif not (
        "qmd" in low
        and ("ast-grep" in low or "astgrep" in low)
        and "headroom" in low
    ):
        # Close waiver-by-oracle: naming only qmd + Headroom is not enough.
        errors.append(
            "Critical cost layers sentence must name qmd, ast-grep, and Headroom"
        )
    return errors


def readme_skill_slugs() -> set[str] | None:
    """Return README table slugs when present, else None (README optional)."""
    path = ROOT / "ai-tooling" / "skills" / "README.md"
    if not path.is_file():
        return None
    readme = path.read_text(encoding="utf-8")
    slugs: set[str] = set()
    for line in readme.splitlines():
        if "./" in line and "](./" in line:
            start = line.find("](./")
            if start != -1:
                rest = line[start + 4 :]
                target = rest.split(")")[0].strip("/")
                slug = target.split("/")[-1]
                if slug:
                    slugs.add(slug)
    return slugs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", help="Folder name under ai-tooling/skills/")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for skill-dry-run callers; validation never mutates",
    )
    args = parser.parse_args(argv)
    if not args.skill and not args.all:
        print("error: pass --skill NAME or --all", file=sys.stderr)
        return 2

    owners = agent_ids(ROOT)
    paths = skill_paths(ROOT)
    if args.skill:
        matched = [
            p for p in paths
            if p.parent.name == args.skill
            or p.relative_to(ROOT / "ai-tooling" / "skills").as_posix().startswith(args.skill)
        ]
        if not matched:
            print(f"error: skill {args.skill!r} not found under ai-tooling/skills/", file=sys.stderr)
            return 2
        paths = matched

    report = []
    listed = readme_skill_slugs()
    fail = 0
    for path in paths:
        errs = check_skill(path, owners)
        warns: list[str] = []
        slug = path.parent.name
        # Agent registration = SKILL.md + owner AGENT.md. README is human-only;
        # missing README rows must not fail skill validation.
        if listed is not None and slug not in listed:
            warns.append(
                "human consistency: not listed in ai-tooling/skills/README.md"
            )
        report.append(
            {
                "skill": slug,
                "ok": not errs,
                "errors": errs,
                "warnings": warns,
            }
        )
        if errs:
            fail += 1
            if not args.json:
                print(f"FAIL {slug}")
                for e in errs:
                    print(f"  - {e}")
                for w in warns:
                    print(f"  ! {w}")
        elif not args.json:
            print(f"OK   {slug}")
            for w in warns:
                print(f"  ! {w}")

    if args.json:
        print(json.dumps({"ok": fail == 0, "results": report}, indent=2))
    elif fail:
        print(f"{fail} skill(s) failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())