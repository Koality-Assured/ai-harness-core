"""Unit tests for Schema V2 skill validation.

tags: [tests, ai-tooling, skills, schema-v2]
routing_hints: [tests, validate-skill, skills]

Run: python -m unittest scripts.tests.test_validate_skill -v

Live-catalog ``validate_skill.py --all`` is expected to fail on this branch until
the sibling ai-tooling-ops SKILL.md contract migration merges. Combined-tree
``test_real_skills_catalog_validation`` (see ``test_skill_graph.py``) is the
merge gate. These tests use temp fixtures so they pass in isolation.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "ai-tooling"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from md import check_required_skill_v2_contracts  # noqa: E402
from validate_skill import check_skill  # noqa: E402

_VALID_BODY = """# {name}

## When to use
Use for validator fixtures.

## When not to use
Not for production catalog files.

## Criticality
High.

## Source of truth
scripts/AGENTS.md

## Isolation
mutate.

## How to use
1. Run the validator.

## Dry run
python scripts/ai-tooling/validate_skill.py --dry-run

## Security
Inherits Critical cost layers: qmd, ast-grep, and Headroom.

## Completion gates
Fixture tests pass.
"""

_OWNERS = {"script-ops"}
_DEFAULT_CONTRACTS = {
    "inputs": ["Script specification"],
    "outputs": ["Tagged Python script under scripts/"],
}


def _skill_text(
    name: str,
    *,
    schema_version: object | None = "2.0.0",
    contracts: object | None = _DEFAULT_CONTRACTS,
    omit: set[str] | None = None,
    **fields: object,
) -> str:
    data: dict[str, object] = {
        "name": name,
        "description": "Validate a fixture skill. Use when testing validators.",
        "owner_agent": "script-ops",
        "rank": "high",
        "isolation": "mutate",
    }
    if schema_version is not None:
        data["schema_version"] = schema_version
    if contracts is not None:
        data["contracts"] = contracts
    data.update(fields)
    for key in omit or set():
        data.pop(key, None)
    dumped = yaml.safe_dump(data, sort_keys=False)
    return f"---\n{dumped}---\n{_VALID_BODY.format(name=name)}"


def _write_skill(root: Path, name: str, text: str) -> Path:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    return path


class CheckRequiredSkillV2ContractsTests(unittest.TestCase):
    def test_valid_contracts_pass(self) -> None:
        errs = check_required_skill_v2_contracts(
            "2.0.0",
            {"inputs": ["in"], "outputs": ["out"]},
        )
        self.assertEqual(errs, [])

    def test_missing_schema_version_is_error_not_v1_default(self) -> None:
        errs = check_required_skill_v2_contracts(
            None,
            {"inputs": ["in"], "outputs": ["out"]},
        )
        self.assertTrue(any("schema_version missing" in e for e in errs))
        self.assertFalse(any("1.0.0" in e for e in errs if "schema_version" in e and "!=" not in e))

    def test_explicit_v1_does_not_skip_contract_checks(self) -> None:
        errs = check_required_skill_v2_contracts("1.0.0", None)
        self.assertTrue(any("schema_version" in e and "1.0.0" in e for e in errs))
        self.assertTrue(any("contracts mapping missing" in e for e in errs))

    def test_empty_contract_lists_fail(self) -> None:
        errs = check_required_skill_v2_contracts(
            "2.0.0",
            {"inputs": [], "outputs": []},
        )
        self.assertTrue(any("contracts.inputs must be non-empty" in e for e in errs))
        self.assertTrue(any("contracts.outputs must be non-empty" in e for e in errs))

    def test_dict_style_contracts_fail_list_rule(self) -> None:
        errs = check_required_skill_v2_contracts(
            "2.0.0",
            {"inputs": {"type": "object"}, "outputs": {"task_id": "string"}},
        )
        self.assertTrue(any("contracts.inputs must be non-empty" in e for e in errs))
        self.assertTrue(any("contracts.outputs must be non-empty" in e for e in errs))

    def test_skill_label_prefix_matches_graph_validator(self) -> None:
        errs = check_required_skill_v2_contracts(
            "2.0.0",
            {"inputs": [], "outputs": ["out"]},
            skill_label="cloud-admin-provision",
        )
        self.assertTrue(
            any(
                e == "Skill 'cloud-admin-provision': Schema V2 contracts.inputs must be non-empty"
                for e in errs
            )
        )


class ValidateSkillUnitTests(unittest.TestCase):
    def test_check_skill_passes_valid_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_skill(Path(tmp), "fixture-skill", _skill_text("fixture-skill"))
            errs = check_skill(path, _OWNERS)
            self.assertEqual(errs, [], f"expected valid fixture, got {errs}")

    def test_check_skill_requires_schema_version_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_skill(
                Path(tmp),
                "no-version-skill",
                _skill_text("no-version-skill", omit={"schema_version"}),
            )
            errs = check_skill(path, _OWNERS)
            self.assertTrue(any("schema_version missing" in e for e in errs))

    def test_check_skill_requires_nonempty_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_skill(
                Path(tmp),
                "no-contracts-skill",
                _skill_text("no-contracts-skill", omit={"contracts"}),
            )
            errs = check_skill(path, _OWNERS)
            self.assertTrue(any("contracts" in e.lower() for e in errs))

    def test_check_skill_rejects_empty_contract_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_skill(
                Path(tmp),
                "empty-contracts-skill",
                _skill_text(
                    "empty-contracts-skill",
                    contracts={"inputs": [], "outputs": []},
                ),
            )
            errs = check_skill(path, _OWNERS)
            self.assertTrue(any("contracts.inputs must be non-empty" in e for e in errs))
            self.assertTrue(any("contracts.outputs must be non-empty" in e for e in errs))

    def test_check_skill_keeps_name_and_heading_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = _skill_text("fixture-skill")
            text = text.replace("name: fixture-skill", "name: wrong-name", 1)
            text = text.replace("## When to use", "## When to fire")
            path = _write_skill(Path(tmp), "fixture-skill", text)
            errs = check_skill(path, _OWNERS)
            self.assertTrue(any("name" in e and "wrong-name" in e for e in errs))
            self.assertTrue(any("missing ## When to use" in e for e in errs))

    def test_v2_skill_without_contracts_is_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_skill(
                Path(tmp),
                "v2-no-io",
                _skill_text("v2-no-io", schema_version="2.0.0", omit={"contracts"}),
            )
            errs = check_skill(path, _OWNERS)
            self.assertTrue(errs, "V2 skill lacking contracts must not report OK")
            self.assertTrue(any("contracts" in e.lower() for e in errs))


if __name__ == "__main__":
    unittest.main()
