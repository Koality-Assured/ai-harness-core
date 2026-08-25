"""Validate one or all agents against Schema V2 frontmatter and agent conventions.

tags: [ai-tooling, routing, agents]
routing_hints: [agents, validate, dry-run, schema-v2]
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
from md import (  # noqa: E402
    ISOLATION,
    MODEL_TIERS,
    agent_ids,
    agent_paths,
    heading_titles,
    parse_frontmatter,
)
from paths import REPO_ROOT as ROOT  # noqa: E402

NAME_MAX = 128
ID_MAX = 64
DESC_MAX = 1024
BODY_MAX_LINES = 500
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def extract_frontmatter_and_body(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Return (data, body, error_message)."""
    if not text.startswith("---"):
        return None, text, "missing YAML frontmatter (no leading ---)"
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    end = rest.find("\n---")
    if end == -1:
        return None, text, "unterminated YAML frontmatter (no closing ---)"
    data, body = parse_frontmatter(text)
    if not isinstance(data, dict):
        return None, body, "frontmatter is not a YAML mapping"
    return data, body, None


def check_agent(path: Path, known_agents: set[str]) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    fields, body, parse_err = extract_frontmatter_and_body(text)
    if parse_err or fields is None:
        errors.append(parse_err or "missing YAML frontmatter")
        return errors

    folder = path.parent.name
    schema_version = str(fields.get("schema_version", ""))
    agent_id = str(fields.get("agent_id", ""))
    name = str(fields.get("name", ""))
    desc = str(fields.get("description", ""))
    model_tier = str(fields.get("model_tier", ""))
    token_ceiling = fields.get("token_ceiling")
    capabilities = fields.get("capabilities")
    contracts = fields.get("contracts")
    isolation_modes = fields.get("isolation_modes")
    allowed_tools = fields.get("allowed_tools")
    delegation_targets = fields.get("delegation_targets")
    prohibitions = fields.get("prohibitions")
    quirks = fields.get("quirks")
    last_verified = fields.get("last_verified")

    # 1. schema_version
    if not schema_version:
        errors.append("schema_version missing (expected '2.0.0')")
    elif schema_version != "2.0.0":
        errors.append(f"schema_version {schema_version!r} != '2.0.0'")

    # 2. agent_id
    if not agent_id:
        errors.append("agent_id missing")
    elif agent_id != folder:
        errors.append(f"agent_id {agent_id!r} != folder {folder!r}")
    elif len(agent_id) > ID_MAX or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in agent_id
    ):
        errors.append(f"agent_id must be kebab-case, max {ID_MAX} chars")

    # 3. name
    if not name:
        errors.append("name missing")
    elif len(name) > NAME_MAX:
        errors.append(f"name exceeds {NAME_MAX} chars")

    # 4. description
    if not desc:
        errors.append("description missing")
    elif len(desc) > DESC_MAX:
        errors.append(f"description exceeds {DESC_MAX} chars")
    else:
        low_desc = desc.lower()
        if not any(k in low_desc for k in ("use for", "use when", "specialist", "dispatcher")):
            errors.append("description must include usage guidance ('Use for', 'Use when', or role summary)")

    # 5. model_tier
    if model_tier not in MODEL_TIERS:
        errors.append(f"model_tier {model_tier!r} must be one of {sorted(MODEL_TIERS)}")

    # 6. token_ceiling
    if token_ceiling is None:
        errors.append("token_ceiling missing (e.g. 100000)")
    elif not isinstance(token_ceiling, int) or isinstance(token_ceiling, bool) or token_ceiling <= 0:
        errors.append(f"token_ceiling must be a positive integer, got {token_ceiling!r}")

    # 7. capabilities
    if capabilities is None:
        errors.append("capabilities missing")
    elif not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list of strings")
    elif not all(isinstance(c, str) and c.strip() for c in capabilities):
        errors.append("capabilities items must be non-empty strings")

    # 8. contracts
    if contracts is None:
        errors.append("contracts mapping missing (contracts.inputs, contracts.outputs)")
    elif not isinstance(contracts, dict):
        errors.append("contracts must be a mapping with 'inputs' and 'outputs'")
    else:
        inputs = contracts.get("inputs")
        outputs = contracts.get("outputs")
        if inputs is None or not isinstance(inputs, list) or not inputs:
            errors.append("contracts.inputs must be a non-empty list of strings")
        elif not all(isinstance(i, str) and i.strip() for i in inputs):
            errors.append("contracts.inputs items must be non-empty strings")
        if outputs is None or not isinstance(outputs, list) or not outputs:
            errors.append("contracts.outputs must be a non-empty list of strings")
        elif not all(isinstance(o, str) and o.strip() for o in outputs):
            errors.append("contracts.outputs items must be non-empty strings")

    # 9. isolation_modes
    if isolation_modes is None:
        errors.append("isolation_modes missing")
    elif not isinstance(isolation_modes, list) or not isolation_modes:
        errors.append("isolation_modes must be a non-empty list")
    else:
        for mode in isolation_modes:
            if mode not in ISOLATION:
                errors.append(f"isolation_modes contains invalid mode {mode!r} (must be in {sorted(ISOLATION)})")

    # 10. allowed_tools
    if allowed_tools is None:
        errors.append("allowed_tools missing")
    elif not isinstance(allowed_tools, list) or not allowed_tools:
        errors.append("allowed_tools must be a non-empty list of tool names")
    elif not all(isinstance(t, str) and t.strip() for t in allowed_tools):
        errors.append("allowed_tools items must be non-empty strings")

    # 11. delegation_targets
    if delegation_targets is not None:
        if not isinstance(delegation_targets, list):
            errors.append("delegation_targets must be a list of agent IDs")
        else:
            for target in delegation_targets:
                if not isinstance(target, str) or target not in known_agents:
                    errors.append(f"delegation_targets item {target!r} is not a registered agent")

    # 12. Optional prohibitions / quirks / last_verified
    if prohibitions is not None and not isinstance(prohibitions, list):
        errors.append("prohibitions must be a list of strings")
    if quirks is not None and not isinstance(quirks, list):
        errors.append("quirks must be a list of strings")
    if last_verified is not None:
        lv_str = str(last_verified)
        if not DATE_RE.match(lv_str):
            errors.append(f"last_verified {lv_str!r} must match YYYY-MM-DD")

    # Body checks
    titles = heading_titles(body)
    if "Read first" not in titles:
        errors.append("missing ## Read first heading in body")
    if "Security" not in titles:
        errors.append("missing ## Security heading in body")
    if folder != "router":
        if "Owns" not in titles:
            errors.append("missing ## Owns heading in body")
        if "Isolation" not in titles:
            errors.append("missing ## Isolation heading in body")
        if "Return to parent" not in titles:
            errors.append("missing ## Return to parent heading in body")

    lines = body.count("\n") + 1
    if lines > BODY_MAX_LINES:
        errors.append(f"body has {lines} lines (max {BODY_MAX_LINES})")
    if "\\" in text and ("scripts\\" in text or "ai-tooling\\" in text):
        errors.append("Windows-style path in agent document")

    low_body = body.lower()
    if "inherits critical cost layers" not in low_body:
        errors.append(
            "must inherit Critical cost layers (qmd, ast-grep, and Headroom) in the agent body"
        )
    elif not (
        "qmd" in low_body
        and ("ast-grep" in low_body or "astgrep" in low_body)
        and "headroom" in low_body
    ):
        errors.append(
            "Critical cost layers sentence must name qmd, ast-grep, and Headroom"
        )

    return errors


def readme_agent_slugs() -> set[str] | None:
    """Return README table slugs when present, else None (README optional)."""
    path = ROOT / "ai-tooling" / "agents" / "README.md"
    if not path.is_file():
        return None
    readme = path.read_text(encoding="utf-8")
    slugs: set[str] = set()
    for line in readme.splitlines():
        if "./" in line and "](./" in line:
            start = line.find("](./")
            if start != -1:
                rest = line[start + 4 :]
                slug = rest.split(")")[0].strip("/").split("/")[0]
                if slug:
                    slugs.add(slug)
    return slugs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", help="Folder name under ai-tooling/agents/")
    parser.add_argument("--all", action="store_true", help="Validate all agents")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for agent-dry-run callers; validation never mutates",
    )
    args = parser.parse_args(argv)
    if not args.agent and not args.all:
        print("error: pass --agent NAME or --all", file=sys.stderr)
        return 2

    known = agent_ids(ROOT)
    paths = agent_paths(ROOT)
    if args.agent:
        target = ROOT / "ai-tooling" / "agents" / args.agent / "AGENT.md"
        if not target.exists():
            print(f"error: missing {target.relative_to(ROOT)}", file=sys.stderr)
            return 2
        paths = [target]

    report = []
    listed = readme_agent_slugs()
    fail = 0
    for path in paths:
        errs = check_agent(path, known)
        warns: list[str] = []
        slug = path.parent.name
        if listed is not None and slug not in listed:
            warns.append(
                "human consistency: not listed in ai-tooling/agents/README.md"
            )
        report.append(
            {
                "agent": slug,
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
        print(f"{fail} agent(s) failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
