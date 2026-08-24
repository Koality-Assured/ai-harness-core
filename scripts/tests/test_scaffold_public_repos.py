"""Unit tests for public ecosystem repositories scaffolding automation.

tags: [tests, repos, scaffold]
routing_hints: [tests, scaffold_public_repos, agent-skills, agent-standards, ai-research, wiki-template]

Run: python -m unittest scripts/tests/test_scaffold_public_repos.py -v
"""

from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
_REPOS = _SCRIPTS / "repos"
_LIB = _SCRIPTS / "_lib"
sys.path.insert(0, str(_REPOS))
sys.path.insert(0, str(_LIB))

from scaffold_public_repos import (  # noqa: E402
    REPO_REGISTRY,
    get_repo_definitions,
    main,
    scaffold_all_repos,
    scaffold_repo,
)


class TestScaffoldPublicRepos(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_scaffold_repos_")
        self.target_dir = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_repo_definitions_registry(self):
        defs = get_repo_definitions()
        self.assertEqual(len(defs), 6)
        self.assertIn("agent-skills-and-tools", defs)
        self.assertIn("agent-standards", defs)
        self.assertIn("security-standards", defs)
        self.assertIn("industry-references", defs)
        self.assertIn("ai-research-and-benchmarks", defs)
        self.assertIn("ai-harness-core", defs)

        for name, d in defs.items():
            self.assertEqual(d.name, name)
            self.assertTrue(len(d.description) > 0)
            self.assertTrue(callable(d.builder))

    def test_scaffold_all_repos_structure_and_mandatory_files(self):
        results = scaffold_all_repos(self.target_dir, overwrite=False, dry_run=False)
        self.assertEqual(len(results), 6)

        expected_repos = [
            "agent-skills-and-tools",
            "agent-standards",
            "security-standards",
            "industry-references",
            "ai-research-and-benchmarks",
            "ai-harness-core",
        ]

        for repo_name in expected_repos:
            repo_path = self.target_dir / repo_name
            self.assertTrue(repo_path.exists(), f"Repo folder {repo_name} should exist")

            # Check mandatory files
            license_path = repo_path / "LICENSE"
            readme_path = repo_path / "README.md"
            ci_path = repo_path / ".github" / "workflows" / "ci.yml"
            gitignore_path = repo_path / ".gitignore"
            editorconfig_path = repo_path / ".editorconfig"

            self.assertTrue(license_path.exists(), f"{repo_name}: LICENSE missing")
            self.assertTrue(readme_path.exists(), f"{repo_name}: README.md missing")
            self.assertTrue(ci_path.exists(), f"{repo_name}: .github/workflows/ci.yml missing")
            self.assertTrue(gitignore_path.exists(), f"{repo_name}: .gitignore missing")
            self.assertTrue(editorconfig_path.exists(), f"{repo_name}: .editorconfig missing")

            # Check LICENSE contents
            license_text = license_path.read_text(encoding="utf-8")
            self.assertIn("MIT License", license_text)
            self.assertIn("Copyright (c) 2026 Koality-Assured", license_text)

            # Check README contents
            readme_text = readme_path.read_text(encoding="utf-8")
            self.assertIn("Mission Statement", readme_text)
            self.assertIn("Architecture Overview", readme_text)
            self.assertIn("Security Notice", readme_text)
            self.assertIn("License", readme_text)

            # Check CI YAML contents
            ci_text = ci_path.read_text(encoding="utf-8")
            self.assertIn("actions/checkout@v4", ci_text)
            self.assertIn("actions/setup-python@v5", ci_text)

    def test_agent_skills_and_tools_specific_files(self):
        res = scaffold_repo("agent-skills-and-tools", self.target_dir)
        repo_path = Path(res["target_path"])

        # Check schemas
        skill_schema = repo_path / "schemas" / "skill.schema.json"
        tool_schema = repo_path / "schemas" / "tool.schema.json"
        self.assertTrue(skill_schema.exists())
        self.assertTrue(tool_schema.exists())

        # Check skills
        worktree_skill = repo_path / "skills" / "git-worktree-manager" / "SKILL.md"
        ast_skill = repo_path / "skills" / "ast-fact-extractor" / "SKILL.md"
        self.assertTrue(worktree_skill.exists())
        self.assertTrue(ast_skill.exists())

        # Check tools and tests
        validator_tool = repo_path / "tools" / "validator.py"
        test_file = repo_path / "tests" / "test_skills.py"
        pyproject = repo_path / "pyproject.toml"
        self.assertTrue(validator_tool.exists())
        self.assertTrue(test_file.exists())
        self.assertTrue(pyproject.exists())

    def test_agent_standards_specific_files(self):
        res = scaffold_repo("agent-standards", self.target_dir)
        repo_path = Path(res["target_path"])

        # Normative standards
        context_std = repo_path / "standards" / "context" / "5-tier-context-management.md"
        proto_std = repo_path / "standards" / "protocols" / "a2a-protocol-v1.md"
        sec_std = repo_path / "standards" / "security" / "security-musts.md"
        self.assertTrue(context_std.exists())
        self.assertTrue(proto_std.exists())
        self.assertTrue(sec_std.exists())

        # Check 5-tier context content
        context_text = context_std.read_text(encoding="utf-8")
        self.assertIn("Tier 1: Fast Routing", context_text)
        self.assertIn("Tier 2: Metadata Index", context_text)
        self.assertIn("Tier 3: Summary Cards", context_text)
        self.assertIn("Tier 4: Extracted AST Facts", context_text)
        self.assertIn("Tier 5: Raw Full Text", context_text)

        # Check security MUSTs content
        sec_text = sec_std.read_text(encoding="utf-8")
        self.assertIn("SEC-01", sec_text)
        self.assertIn("SEC-02", sec_text)
        self.assertIn("SEC-03", sec_text)
        self.assertIn("SEC-04", sec_text)

        # RFCs and specs
        rfc1 = repo_path / "rfcs" / "0001-rfc-process.md"
        rfc_tmpl = repo_path / "rfcs" / "template.md"
        a2a_schema = repo_path / "specs" / "a2a-message.schema.json"
        manifest_schema = repo_path / "specs" / "context-manifest.schema.json"
        self.assertTrue(rfc1.exists())
        self.assertTrue(rfc_tmpl.exists())
        self.assertTrue(a2a_schema.exists())
        self.assertTrue(manifest_schema.exists())

    def test_ai_research_and_benchmarks_specific_files(self):
        res = scaffold_repo("ai-research-and-benchmarks", self.target_dir)
        repo_path = Path(res["target_path"])

        # Benchmark suites
        suite_json = repo_path / "benchmarks" / "suites" / "coding_agent_benchmark_v1.json"
        runner_py = repo_path / "harnesses" / "runner.py"
        cost_py = repo_path / "telemetry" / "cost_calculator.py"
        report_tmpl = repo_path / "reports" / "template_evaluation_report.md"
        test_bench = repo_path / "tests" / "test_benchmarks.py"
        pyproject = repo_path / "pyproject.toml"

        self.assertTrue(suite_json.exists())
        self.assertTrue(runner_py.exists())
        self.assertTrue(cost_py.exists())
        self.assertTrue(report_tmpl.exists())
        self.assertTrue(test_bench.exists())
        self.assertTrue(pyproject.exists())

    def test_all_scaffolded_json_and_python_files_are_valid(self):
        scaffold_all_repos(self.target_dir, overwrite=True)

        for json_path in self.target_dir.rglob("*.json"):
            try:
                json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self.fail(f"Invalid JSON in {json_path}: {exc}")

        for py_path in self.target_dir.rglob("*.py"):
            try:
                ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
            except SyntaxError as exc:
                self.fail(f"Invalid Python syntax in {py_path}: {exc}")

    def test_scaffolded_repos_pass_internal_tests(self):
        scaffold_all_repos(self.target_dir, overwrite=True)

        for repo_name in ["agent-skills-and-tools", "agent-standards", "ai-research-and-benchmarks"]:
            repo_path = self.target_dir / repo_name
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"Internal tests failed in {repo_name}:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}",
            )

    def test_security_standards_specific_files(self):
        res = scaffold_repo("security-standards", self.target_dir)
        repo_path = Path(res["target_path"])
        self.assertTrue((repo_path / "standards" / "README.md").exists())
        self.assertTrue((repo_path / "tools" / "validator.py").exists())
        self.assertTrue((repo_path / "tests" / "test_standards.py").exists())

    def test_industry_references_specific_files(self):
        res = scaffold_repo("industry-references", self.target_dir)
        repo_path = Path(res["target_path"])
        self.assertTrue((repo_path / "references" / "README.md").exists())
        self.assertTrue((repo_path / "tools" / "validator.py").exists())
        self.assertTrue((repo_path / "tests" / "test_references.py").exists())

    def test_ai_harness_core_specific_files(self):
        res = scaffold_repo("ai-harness-core", self.target_dir)
        repo_path = Path(res["target_path"])
        self.assertTrue((repo_path / "AGENTS.md").exists())
        self.assertTrue((repo_path / "docs" / "standards" / "AGENTS.md").exists())
        self.assertTrue((repo_path / "config" / "harness.config.json").exists())
        self.assertTrue((repo_path / "projects" / "AGENTS.md").exists())
        refs_agents = (repo_path / "references" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("conventional-commits", refs_agents)
        self.assertNotIn("owasp", refs_agents.lower())
        self.assertNotIn("nist-ai-rmf", refs_agents.lower())
        self.assertFalse((repo_path / "pyproject.toml").exists())
        self.assertFalse((repo_path / "harness").exists())
        readme = (repo_path / "README.md").read_text(encoding="utf-8")
        self.assertIn("wiki harness template", readme.lower())
        self.assertNotIn("bare-metal", readme.lower())
        self.assertNotIn("harness-init", readme)

    def test_dry_run_does_not_write_to_disk(self):
        results = scaffold_all_repos(self.target_dir, overwrite=False, dry_run=True)
        self.assertEqual(len(results), 6)
        for res in results:
            self.assertTrue(res["dry_run"])
            self.assertGreater(res["file_count"], 0)
            self.assertGreater(res["total_bytes"], 0)

        # Confirm target directory has no created repo folders
        created = list(self.target_dir.iterdir())
        self.assertEqual(len(created), 0)

    def test_overwrite_protection(self):
        scaffold_repo("agent-skills-and-tools", self.target_dir)

        # Attempting without overwrite should raise FileExistsError
        with self.assertRaises(FileExistsError):
            scaffold_repo("agent-skills-and-tools", self.target_dir, overwrite=False)

        # With overwrite=True should succeed
        res = scaffold_repo("agent-skills-and-tools", self.target_dir, overwrite=True)
        self.assertEqual(res["repo_name"], "agent-skills-and-tools")

    def test_unknown_repo_raises_value_error(self):
        with self.assertRaises(ValueError):
            scaffold_repo("non-existent-repo", self.target_dir)

    def test_cli_list_flag(self):
        ret = main(["--list"])
        self.assertEqual(ret, 0)

    def test_cli_dry_run_all(self):
        ret = main(["--dry-run", "--output-dir", str(self.target_dir)])
        self.assertEqual(ret, 0)
        self.assertEqual(len(list(self.target_dir.iterdir())), 0)

    def test_cli_scaffold_single_repo(self):
        ret = main(["--repo", "agent-standards", "--output-dir", str(self.target_dir)])
        self.assertEqual(ret, 0)
        self.assertTrue((self.target_dir / "agent-standards").exists())
        self.assertFalse((self.target_dir / "agent-skills-and-tools").exists())

    def test_cli_json_output(self):
        saved_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            ret = main(["--repo", "all", "--output-dir", str(self.target_dir), "--json"])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = saved_stdout

        self.assertEqual(ret, 0)
        parsed = json.loads(output)
        self.assertEqual(len(parsed), 6)


if __name__ == "__main__":
    unittest.main()
