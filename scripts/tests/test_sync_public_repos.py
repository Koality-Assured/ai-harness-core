"""Unit tests for multi-repo synchronization and redaction engine.

tags: [tests, sync, security, export]
routing_hints: [tests, sync, redaction, multi-repo, wiki-template]

Run: python -m unittest scripts/tests/test_sync_public_repos.py -v
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

_SYNC_DIR = Path(__file__).resolve().parents[1] / "sync"
if str(_SYNC_DIR) not in sys.path:
    sys.path.insert(0, str(_SYNC_DIR))

from sync_public_repos import (
    DEFAULT_REPO_MAPPINGS,
    RedactionAuditEntry,
    RedactionEngine,
    RedactionRule,
    RepoSyncResult,
    SyncEngine,
    SyncReport,
    build_default_rules,
    format_text_report,
    main,
)
from _wiki_template import (
    WIKI_TEMPLATE_MODE,
    agent_is_kept,
    is_wiki_template_rel_kept,
    skill_is_kept,
)


class WikiTemplateRulesTests(unittest.TestCase):
    def test_keep_wiki_machinery(self) -> None:
        self.assertTrue(is_wiki_template_rel_kept("AGENTS.md"))
        self.assertTrue(is_wiki_template_rel_kept("routing/areas.yaml"))
        self.assertTrue(is_wiki_template_rel_kept(".harness/__init__.py"))
        self.assertTrue(is_wiki_template_rel_kept("docs/agent-session-security.md"))
        self.assertTrue(is_wiki_template_rel_kept("docs/standards/context-management.md"))
        self.assertTrue(is_wiki_template_rel_kept("ai-tooling/skills/isolate-work/SKILL.md"))
        self.assertTrue(is_wiki_template_rel_kept("ai-tooling/agents/script-ops/AGENT.md"))
        self.assertTrue(is_wiki_template_rel_kept("scripts/sync/sync_public_repos.py"))
        self.assertTrue(is_wiki_template_rel_kept("scripts/docs/run_markdownlint.py"))
        self.assertTrue(is_wiki_template_rel_kept("scripts/github/resolve_github_path.py"))
        self.assertTrue(is_wiki_template_rel_kept("scripts/ai-tooling/validate_skill.py"))
        self.assertTrue(is_wiki_template_rel_kept("references/conventional-commits/guide.md"))

    def test_drop_domain_fed_paths(self) -> None:
        self.assertFalse(is_wiki_template_rel_kept("references/owasp/catalog.json"))
        self.assertFalse(is_wiki_template_rel_kept("references/nist-csf/catalog.json"))
        self.assertFalse(is_wiki_template_rel_kept("ai-tooling/skills/aws-read/SKILL.md"))
        self.assertFalse(is_wiki_template_rel_kept("ai-tooling/skills/framework-mapper/SKILL.md"))
        self.assertFalse(is_wiki_template_rel_kept("docs/standards/identity-and-access.md"))
        self.assertFalse(is_wiki_template_rel_kept("[REDACTED_WORKTREE_PATH]"))
        self.assertFalse(is_wiki_template_rel_kept("ai-tooling/memory/user/distastefu1/workstation.md"))
        self.assertFalse(is_wiki_template_rel_kept("routing/skill-dispatch.md"))
        self.assertFalse(is_wiki_template_rel_kept("routing/area-map.md"))
        self.assertFalse(is_wiki_template_rel_kept("references/AGENTS.md"))
        self.assertFalse(is_wiki_template_rel_kept("scripts/script-index.md"))
        self.assertFalse(is_wiki_template_rel_kept("scripts/references/refresh_reference_family.py"))
        self.assertFalse(is_wiki_template_rel_kept("scripts/projects/new_project.py"))
        self.assertFalse(is_wiki_template_rel_kept("ai-tooling/agents/cloud-operator/AGENT.md"))
        self.assertFalse(is_wiki_template_rel_kept("ai-tooling/agents/assessment-agent/AGENT.md"))

    def test_skill_allowlist(self) -> None:
        self.assertTrue(skill_is_kept("isolate-work"))
        self.assertTrue(skill_is_kept("script-builder"))
        self.assertFalse(skill_is_kept("aws-write"))
        self.assertFalse(skill_is_kept("azure-logs"))
        self.assertFalse(skill_is_kept("gcp-read"))
        self.assertFalse(skill_is_kept("noir-scan"))
        self.assertFalse(skill_is_kept("threat-model"))

    def test_agent_denylist(self) -> None:
        self.assertTrue(agent_is_kept("script-ops"))
        self.assertTrue(agent_is_kept("router"))
        self.assertTrue(agent_is_kept("documentation-ops"))
        self.assertFalse(agent_is_kept("cloud-operator"))
        self.assertFalse(agent_is_kept("assessment-agent"))


class RedactionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RedactionEngine(usernames=["customuser", "alice"])

    def test_openai_api_key_redacted(self) -> None:
        sample = "export OPENAI_API_KEY='[REDACTED_OPENAI_KEY]'"
        redacted, audits = self.engine.redact_text(sample, "test.env")
        self.assertNotIn("sk-proj-", redacted)
        self.assertIn("[REDACTED_OPENAI_KEY]", redacted)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0].rule, "openai_api_key")
        self.assertEqual(audits[0].line, 1)

    def test_anthropic_api_key_redacted(self) -> None:
        sample = "ANTHROPIC_KEY=[REDACTED_ANTHROPIC_KEY]"
        redacted, audits = self.engine.redact_text(sample, "config.py")
        self.assertNotIn("sk-ant-", redacted)
        self.assertIn("[REDACTED_ANTHROPIC_KEY]", redacted)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0].rule, "anthropic_api_key")

    def test_github_token_redacted(self) -> None:
        sample = "Authorization: token [REDACTED_GITHUB_TOKEN]"
        redacted, audits = self.engine.redact_text(sample, "headers.txt")
        self.assertNotIn("ghp_", redacted)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", redacted)
        self.assertEqual(len(audits), 1)

        pat_sample = "[REDACTED_GITHUB_TOKEN]"
        redacted_pat, audits_pat = self.engine.redact_text(pat_sample, "token.txt")
        self.assertNotIn("github_pat_", redacted_pat)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", redacted_pat)

    def test_aws_access_key_and_secret_redacted(self) -> None:
        sample = (
            "aws_access_key_id = [REDACTED_AWS_KEY]\n"
            "aws_secret_access_key = "[REDACTED_AWS_SECRET]"\n"
        )
        redacted, audits = self.engine.redact_text(sample, "aws.ini")
        self.assertNotIn("[REDACTED_AWS_KEY]", redacted)
        self.assertNotIn("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", redacted)
        self.assertIn("[REDACTED_AWS_KEY]", redacted)
        self.assertIn("[REDACTED_AWS_SECRET]", redacted)
        self.assertEqual(len(audits), 2)

    def test_slack_and_jwt_and_bearer_redacted(self) -> None:
        sample = (
            "SLACK_BOT=[REDACTED_SLACK_TOKEN]\n"
            "TOKEN=[REDACTED_JWT_TOKEN]\n"
            "Header: Bearer [REDACTED_BEARER_TOKEN]\n"
        )
        redacted, audits = self.engine.redact_text(sample, "secrets.txt")
        self.assertNotIn("xoxb-", redacted)
        self.assertNotIn("eyJhbGci", redacted)
        self.assertNotIn("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", redacted)
        self.assertIn("[REDACTED_SLACK_TOKEN]", redacted)
        self.assertIn("[REDACTED_JWT_TOKEN]", redacted)
        self.assertIn("[REDACTED_BEARER_TOKEN]", redacted)
        self.assertGreaterEqual(len(audits), 3)

    def test_private_key_block_redacted(self) -> None:
        sample = (
            "[REDACTED_PRIVATE_KEY_BLOCK]"
        )
        redacted, audits = self.engine.redact_text(sample, "id_rsa")
        self.assertNotIn("BEGIN RSA PRIVATE KEY", redacted)
        self.assertIn("[REDACTED_PRIVATE_KEY_BLOCK]", redacted)
        self.assertEqual(len(audits), 1)

    def test_git_credentials_in_url_redacted(self) -> None:
        sample = "git clone https://github.com/my-org/my-repo.git"
        redacted, audits = self.engine.redact_text(sample, "clone.sh")
        self.assertNotIn("x-access-token", redacted)
        self.assertNotIn("ghp_secretpass", redacted)
        self.assertIn("https://github.com/my-org/my-repo.git", redacted)

    def test_internal_paths_redacted(self) -> None:
        sample = (
            r"Path is C:\Users\developer\AppData\Local\Temp\test" + "\n"
            + "[REDACTED_WORKTREE_PATH]"
            + r"[REDACTED_APPDATA_PATH]" + "\n"
            + r"Repo is at [REPO_ROOT]/docs" + "\n"
        )
        redacted, audits = self.engine.redact_text(sample, "paths.md")
        self.assertNotIn(r"C:\Users\developer\AppData", redacted)
        self.assertNotIn("/home/developer", redacted)
        self.assertNotIn("[REDACTED_WORKTREE_PATH]", redacted)
        self.assertNotIn(r"C:\Code\ai-router", redacted)
        self.assertIn("[REDACTED_APPDATA_PATH]", redacted)
        self.assertIn("[REDACTED_WORKTREE_PATH]", redacted)
        self.assertIn("[REPO_ROOT]/docs", redacted)

    def test_internal_emails_and_git_identities_redacted(self) -> None:
        sample = (
            "Contact team at [REDACTED_INTERNAL_EMAIL] or [REDACTED_INTERNAL_EMAIL]\n"
            "user.email = "developer@example.com"\n"
        )
        redacted, audits = self.engine.redact_text(sample, "team.md")
        self.assertNotIn("@internal.corp", redacted)
        self.assertNotIn("@corp.internal", redacted)
        self.assertIn("[REDACTED_INTERNAL_EMAIL]", redacted)
        self.assertIn('user.email = "developer@example.com"', redacted)

    def test_custom_usernames_redacted(self) -> None:
        sample = "Assignee is customuser or alice for this task."
        redacted, audits = self.engine.redact_text(sample, "task.md")
        self.assertNotIn("customuser", redacted)
        self.assertNotIn("alice", redacted)
        self.assertIn("developer", redacted)

    def test_multiline_line_number_accuracy(self) -> None:
        sample = (
            "# Line 1\n"
            "# Line 2\n"
            "SECRET=[REDACTED_ANTHROPIC_KEY]\n"
            "# Line 4\n"
            "USER_EMAIL=[REDACTED_INTERNAL_EMAIL]\n"
        )
        redacted, audits = self.engine.redact_text(sample, "file.txt")
        self.assertEqual(len(audits), 2)
        self.assertEqual(audits[0].line, 3)
        self.assertEqual(audits[0].rule, "anthropic_api_key")
        self.assertEqual(audits[1].line, 5)
        self.assertEqual(audits[1].rule, "internal_email_domain")

    def test_find_violations(self) -> None:
        clean = "This is safe public documentation with no secrets."
        self.assertEqual(self.engine.find_violations(clean), [])

        dirty = "API Key: [REDACTED_ANTHROPIC_KEY]\nInternal: [REDACTED_INTERNAL_EMAIL]"
        violations = self.engine.find_violations(dirty, "dirty.txt")
        self.assertEqual(len(violations), 2)
        self.assertIn("anthropic_api_key", violations[0])
        self.assertIn("internal_email_domain", violations[1])


class SyncEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_src_dir = tempfile.TemporaryDirectory()
        self.temp_dst_dir = tempfile.TemporaryDirectory()
        self.src_root = Path(self.temp_src_dir.name)
        self.dst_root = Path(self.temp_dst_dir.name)

        # Populate sample source structure matching router mappings
        # 1. ai-tooling/skills/
        skills_dir = self.src_root / "ai-tooling" / "skills" / "demo-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: demo-skill\n---\n# Demo\nAPI token: [REDACTED_GITHUB_TOKEN]\n",
            encoding="utf-8",
        )
        (skills_dir / "helper.py").write_text(
            "# helper\nprint('demo')\n",
            encoding="utf-8",
        )
        # Excluded items
        pycache_dir = skills_dir / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "helper.cpython-313.pyc").write_bytes(b"compiled bytecode")
        (skills_dir / ".DS_Store").write_bytes(b"\x00\x00\x00\x01")

        # 2. docs/standards/
        standards_dir = self.src_root / "docs" / "standards"
        standards_dir.mkdir(parents=True)
        (standards_dir / "sec-policy.md").write_text(
            "# Security Policy\nContact: [REDACTED_INTERNAL_EMAIL]\n",
            encoding="utf-8",
        )

        # 3. research/
        research_dir = self.src_root / "research" / "benchmarks"
        research_dir.mkdir(parents=True)
        (research_dir / "eval.md").write_text(
            "# Benchmark Eval\nAuthor: developer\nScore: 99.5\n",
            encoding="utf-8",
        )
        # Binary asset in research
        (research_dir / "chart.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRsample")

        # 4. references/
        ref_dir = self.src_root / "references" / "owasp"
        ref_dir.mkdir(parents=True)
        (ref_dir / "catalog.json").write_text('{"framework": "owasp"}\n', encoding="utf-8")

        # 5. .harness/ (engine stays nested as .harness/ in the wiki template)
        harness_dir = self.src_root / ".harness"
        harness_dir.mkdir(parents=True)
        (harness_dir / "__init__.py").write_text('"""harness init"""\n', encoding="utf-8")

        # Wiki-template machinery (ai-harness-core copies the wiki tree, not harness/)
        (self.src_root / "AGENTS.md").write_text("# Root AGENTS\n", encoding="utf-8")
        routing_dir = self.src_root / "routing"
        routing_dir.mkdir(parents=True)
        (routing_dir / "AGENTS.md").write_text("# Routing\n", encoding="utf-8")
        (routing_dir / "areas.yaml").write_text("areas:\n", encoding="utf-8")
        (routing_dir / "skill-dispatch.md").write_text(
            "| Skill | Owner |\n| --- | --- |\n"
            "| [`aws-read`](../ai-tooling/skills/aws-read/SKILL.md) | cloud-operator |\n"
            "| [`owasp`](../ai-tooling/skills/owasp/SKILL.md) | artifact-agent |\n",
            encoding="utf-8",
        )
        (routing_dir / "area-map.md").write_text(
            "| Area | Default agent |\n| --- | --- |\n"
            "| `docs/` | cloud-operator |\n"
            "| `research/` | assessment-agent |\n",
            encoding="utf-8",
        )

        docs_dir = self.src_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "AGENTS.md").write_text("# Docs AGENTS\n", encoding="utf-8")
        (docs_dir / "agent-session-security.md").write_text("# Session security MUST\n", encoding="utf-8")
        (docs_dir / "anti-slop.md").write_text("# Anti-slop\n", encoding="utf-8")
        (docs_dir / "standards" / "context-management.md").write_text("# Context management\n", encoding="utf-8")
        (docs_dir / "standards" / "identity-and-access.md").write_text("# IAM (domain-fed)\n", encoding="utf-8")

        cc_dir = self.src_root / "references" / "conventional-commits"
        cc_dir.mkdir(parents=True)
        (cc_dir / "guide.md").write_text("# Conventional Commits\n", encoding="utf-8")
        (self.src_root / "references" / "AGENTS.md").write_text(
            "# References AGENTS\n\n## Current families\n\n"
            "| Folder | Topic |\n| --- | --- |\n"
            "| `owasp/` | Top 10 |\n"
            "| `nist-ai-rmf/` | NIST AI RMF |\n",
            encoding="utf-8",
        )
        nist_dir = self.src_root / "references" / "nist-csf"
        nist_dir.mkdir(parents=True)
        (nist_dir / "catalog.json").write_text('{"framework": "nist-csf"}\n', encoding="utf-8")

        isolate_dir = self.src_root / "ai-tooling" / "skills" / "isolate-work"
        isolate_dir.mkdir(parents=True)
        (isolate_dir / "SKILL.md").write_text("---\nname: isolate-work\n---\n# Isolate\n", encoding="utf-8")
        aws_dir = self.src_root / "ai-tooling" / "skills" / "aws-read"
        aws_dir.mkdir(parents=True)
        (aws_dir / "SKILL.md").write_text("---\nname: aws-read\n---\n# AWS\n", encoding="utf-8")
        owasp_dir = self.src_root / "ai-tooling" / "skills" / "owasp"
        owasp_dir.mkdir(parents=True)
        (owasp_dir / "SKILL.md").write_text("---\nname: owasp\n---\n# OWASP\n", encoding="utf-8")

        scripts_docs = self.src_root / "scripts" / "docs"
        scripts_docs.mkdir(parents=True)
        (scripts_docs / "run_markdownlint.py").write_text('"""markdownlint wrapper."""\n', encoding="utf-8")
        scripts_github = self.src_root / "scripts" / "github"
        scripts_github.mkdir(parents=True)
        (scripts_github / "resolve_github_path.py").write_text('"""github-paths helper."""\n', encoding="utf-8")
        scripts_ai = self.src_root / "scripts" / "ai-tooling"
        scripts_ai.mkdir(parents=True)
        (scripts_ai / "validate_skill.py").write_text('"""skill validator."""\n', encoding="utf-8")
        scripts_refs = self.src_root / "scripts" / "references"
        scripts_refs.mkdir(parents=True)
        (scripts_refs / "refresh_reference_family.py").write_text(
            '"""tags: [references]\\nRefresh a references family (owasp, nist)."""\n',
            encoding="utf-8",
        )
        scripts_projects = self.src_root / "scripts" / "projects"
        scripts_projects.mkdir(parents=True)
        (scripts_projects / "new_project.py").write_text(
            '"""tags: [projects]\\nScaffold a projects slug."""\n',
            encoding="utf-8",
        )
        (self.src_root / "scripts" / "script-index.md").write_text(
            "| Script | Tags |\n| --- | --- |\n"
            "| [`references/refresh_reference_family.py`](./references/refresh_reference_family.py) "
            "| `references` |\n"
            "| [`projects/new_project.py`](./projects/new_project.py) | `projects` |\n",
            encoding="utf-8",
        )
        agents_root = self.src_root / "ai-tooling" / "agents"
        (agents_root / "script-ops").mkdir(parents=True)
        (agents_root / "script-ops" / "AGENT.md").write_text("# script-ops\n", encoding="utf-8")
        (agents_root / "cloud-operator").mkdir(parents=True)
        (agents_root / "cloud-operator" / "AGENT.md").write_text("# cloud-operator\n", encoding="utf-8")
        (agents_root / "assessment-agent").mkdir(parents=True)
        (agents_root / "assessment-agent" / "AGENT.md").write_text(
            "# assessment-agent\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_src_dir.cleanup()
        self.temp_dst_dir.cleanup()

    def test_sync_all_repos(self) -> None:
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
            dry_run=False,
        )
        report = engine.sync_all()

        self.assertTrue(report.summary["success"])
        self.assertEqual(report.summary["total_repos"], 6)
        self.assertGreater(report.summary["total_files_synced"], 0)
        self.assertGreater(report.summary["total_redactions"], 0)

        # Check destination files exist in mapped locations
        skill_file = self.dst_root / "agent-skills-and-tools" / "skills" / "demo-skill" / "SKILL.md"
        self.assertTrue(skill_file.exists())
        content = skill_file.read_text(encoding="utf-8")
        self.assertNotIn("ghp_", content)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", content)

        # Verify security-standards and industry-references synced
        sec_file = self.dst_root / "security-standards" / "standards" / "sec-policy.md"
        self.assertTrue(sec_file.exists())
        ref_file = self.dst_root / "industry-references" / "references" / "owasp" / "catalog.json"
        self.assertTrue(ref_file.exists())
        harness_file = self.dst_root / "ai-harness-core" / ".harness" / "__init__.py"
        self.assertTrue(harness_file.exists())
        self.assertFalse((self.dst_root / "ai-harness-core" / "harness").exists())

        # Verify excluded files are NOT synced
        self.assertFalse((self.dst_root / "agent-skills-and-tools" / "skills" / "demo-skill" / "__pycache__").exists())
        self.assertFalse((self.dst_root / "agent-skills-and-tools" / "skills" / "demo-skill" / ".DS_Store").exists())

        policy_file = self.dst_root / "agent-standards" / "standards" / "sec-policy.md"
        self.assertTrue(policy_file.exists())
        policy_content = policy_file.read_text(encoding="utf-8")
        self.assertNotIn("@internal.corp", policy_content)
        self.assertIn("[REDACTED_INTERNAL_EMAIL]", policy_content)

        eval_file = self.dst_root / "ai-research-and-benchmarks" / "research" / "benchmarks" / "eval.md"
        self.assertTrue(eval_file.exists())

        # Binary file synced intact
        png_file = self.dst_root / "ai-research-and-benchmarks" / "research" / "benchmarks" / "chart.png"
        self.assertTrue(png_file.exists())
        self.assertEqual(png_file.read_bytes(), b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRsample")

    def test_ai_harness_core_is_wiki_template(self) -> None:
        core = self.dst_root / "ai-harness-core"
        leftover_pkg = core / "harness"
        leftover_pkg.mkdir(parents=True)
        (leftover_pkg / "__init__.py").write_text('"""leftover engine package"""\n', encoding="utf-8")
        (core / "pyproject.toml").write_text(
            '[project]\nname = "ai-harness-core"\n', encoding="utf-8"
        )
        leftover_tests = core / "tests"
        leftover_tests.mkdir(parents=True)
        (leftover_tests / "test_harness_core.py").write_text(
            '"""engine unittest"""\n', encoding="utf-8"
        )

        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
            dry_run=False,
        )
        report = engine.sync_all(repo_filter="ai-harness-core")
        self.assertTrue(report.summary["success"])
        self.assertEqual(
            DEFAULT_REPO_MAPPINGS["ai-harness-core"]["mode"],
            WIKI_TEMPLATE_MODE,
        )

        self.assertTrue((core / "AGENTS.md").exists())
        self.assertTrue((core / "routing" / "AGENTS.md").exists())
        self.assertTrue((core / "routing" / "areas.yaml").exists())
        self.assertTrue((core / ".harness" / "__init__.py").exists())
        self.assertTrue((core / "docs" / "AGENTS.md").exists())
        self.assertTrue((core / "docs" / "agent-session-security.md").exists())
        self.assertTrue((core / "docs" / "standards" / "context-management.md").exists())
        self.assertTrue((core / "ai-tooling" / "skills" / "isolate-work" / "SKILL.md").exists())
        self.assertTrue((core / "ai-tooling" / "agents" / "script-ops" / "AGENT.md").exists())
        self.assertTrue((core / "references" / "conventional-commits" / "guide.md").exists())
        self.assertTrue((core / "scripts" / "docs" / "run_markdownlint.py").exists())
        self.assertTrue((core / "scripts" / "github" / "resolve_github_path.py").exists())
        self.assertTrue((core / "scripts" / "ai-tooling" / "validate_skill.py").exists())

        stub = (core / "docs" / "standards" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("generic", stub.lower())
        self.assertIn("template", stub.lower())

        refs_agents = (core / "references" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("conventional-commits", refs_agents)
        self.assertIn("markdown", refs_agents)
        self.assertIn("fed later", refs_agents.lower())
        self.assertNotIn("owasp", refs_agents.lower())
        self.assertNotIn("nist-ai-rmf", refs_agents.lower())

        dispatch = (core / "routing" / "skill-dispatch.md").read_text(encoding="utf-8")
        self.assertIn("[`isolate-work`]", dispatch)
        self.assertNotRegex(dispatch, r"\|\s*\[`aws-read`\]")
        self.assertNotRegex(dispatch, r"\|\s*\[`owasp`\]")
        self.assertFalse((core / "ai-tooling" / "skills" / "owasp").exists())

        area_map = (core / "routing" / "area-map.md").read_text(encoding="utf-8")
        self.assertNotIn("cloud-operator", area_map)
        self.assertNotIn("assessment-agent", area_map)

        script_index = (core / "scripts" / "script-index.md").read_text(encoding="utf-8")
        self.assertIn("docs/run_markdownlint.py", script_index)
        self.assertNotIn("scripts/references", script_index)
        self.assertNotIn("references/refresh_reference_family", script_index)
        self.assertNotIn("scripts/projects", script_index)
        self.assertNotIn("projects/new_project", script_index)

        readme = (core / "README.md").read_text(encoding="utf-8")
        self.assertIn("wiki harness template", readme.lower())
        self.assertNotIn("pip install", readme.lower())
        self.assertNotIn("bare-metal", readme.lower())
        self.assertNotIn("fed security", readme.lower())

        ci = (core / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("compileall", ci)
        self.assertIn("scripts/tests", ci)
        self.assertNotIn("discover -s tests", ci)

        self.assertFalse((core / "harness").exists())
        self.assertFalse((core / "pyproject.toml").exists())
        self.assertFalse((core / "tests").exists())
        self.assertFalse((core / "ai-tooling" / "agents" / "cloud-operator").exists())
        self.assertFalse((core / "ai-tooling" / "agents" / "assessment-agent").exists())
        self.assertFalse((core / "scripts" / "references").exists())
        self.assertFalse((core / "scripts" / "projects").exists())
        self.assertFalse((core / "ai-tooling" / "skills" / "aws-read").exists())
        self.assertFalse((core / "references" / "owasp").exists())
        self.assertFalse((core / "references" / "nist-csf").exists())
        self.assertFalse((core / "docs" / "standards" / "identity-and-access.md").exists())
        self.assertFalse((core / "docs" / "standards" / "sec-policy.md").exists())

    def test_sync_single_repo(self) -> None:
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
            dry_run=False,
        )
        report = engine.sync_all(repo_filter="agent-standards")

        self.assertEqual(report.summary["total_repos"], 1)
        self.assertIn("agent-standards", report.repos)
        self.assertNotIn("agent-skills-and-tools", report.repos)

        policy_file = self.dst_root / "agent-standards" / "standards" / "sec-policy.md"
        self.assertTrue(policy_file.exists())
        skills_file = self.dst_root / "agent-skills-and-tools" / "skills" / "demo-skill" / "SKILL.md"
        self.assertFalse(skills_file.exists())

    def test_sync_into_repo_root_dest(self) -> None:
        # If dest root is named 'agent-standards', destination resolves directly to standards/
        repo_dst = self.dst_root / "agent-standards"
        repo_dst.mkdir()
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=repo_dst,
            dry_run=False,
        )
        report = engine.sync_all(repo_filter="agent-standards")
        self.assertTrue(report.summary["success"])
        self.assertTrue((repo_dst / "standards" / "sec-policy.md").exists())

    def test_dry_run_does_not_modify_dest(self) -> None:
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
            dry_run=True,
        )
        report = engine.sync_all()

        self.assertTrue(report.dry_run)
        self.assertTrue(report.summary["success"])
        self.assertGreater(report.summary["total_files_scanned"], 0)
        self.assertGreater(report.summary["total_redactions"], 0)

        # Verify nothing was written to dst_root
        created_files = list(self.dst_root.rglob("*"))
        self.assertEqual(len(created_files), 0)

    def test_idempotent_sync_tracks_unchanged(self) -> None:
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
            dry_run=False,
        )
        report1 = engine.sync_all()
        self.assertGreater(report1.summary["total_files_modified"], 0)
        self.assertEqual(report1.summary["total_files_unchanged"], 0)

        # Run second sync without changes
        report2 = engine.sync_all()
        self.assertEqual(report2.summary["total_files_modified"], 0)
        self.assertEqual(report2.summary["total_files_unchanged"], report1.summary["total_files_synced"])

    def test_missing_source_directory_reports_error(self) -> None:
        empty_root = Path(tempfile.mkdtemp())
        engine = SyncEngine(
            source_root=empty_root,
            dest_root=self.dst_root,
        )
        report = engine.sync_all(repo_filter="agent-standards")
        self.assertFalse(report.summary["success"])
        self.assertGreater(report.summary["total_errors"], 0)
        self.assertIn("Source directory does not exist", report.repos["agent-standards"].errors[0])
        shutil.rmtree(empty_root, ignore_errors=True)

    def test_validate_sources_reports_dirty_files(self) -> None:
        engine = SyncEngine(
            source_root=self.src_root,
            dest_root=self.dst_root,
        )
        is_clean, violations = engine.validate_sources()
        self.assertFalse(is_clean)
        self.assertGreaterEqual(len(violations), 2)


class CliAndFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_src_dir = tempfile.TemporaryDirectory()
        self.temp_dst_dir = tempfile.TemporaryDirectory()
        self.src_root = Path(self.temp_src_dir.name)
        self.dst_root = Path(self.temp_dst_dir.name)

        # Setup standard trees
        skills_dir = self.src_root / "ai-tooling" / "skills" / "safe-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: safe-skill\n---\n# Safe skill\nClean content.\n",
            encoding="utf-8",
        )
        standards_dir = self.src_root / "docs" / "standards"
        standards_dir.mkdir(parents=True)
        (standards_dir / "doc.md").write_text("# Doc\nSafe doc.\n", encoding="utf-8")

        research_dir = self.src_root / "research"
        research_dir.mkdir(parents=True)
        (research_dir / "res.md").write_text("# Research\nSafe research.\n", encoding="utf-8")

        references_dir = self.src_root / "references"
        references_dir.mkdir(parents=True)
        (references_dir / "ref.md").write_text("# Reference\nSafe reference.\n", encoding="utf-8")

        harness_dir = self.src_root / ".harness"
        harness_dir.mkdir(parents=True)
        (harness_dir / "__init__.py").write_text('"""harness init"""\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_src_dir.cleanup()
        self.temp_dst_dir.cleanup()

    def test_cli_dry_run_json(self) -> None:
        report_file = self.dst_root / "report.json"
        argv = [
            "--source",
            str(self.src_root),
            "--dest",
            str(self.dst_root),
            "--dry-run",
            "--json",
            "--report-file",
            str(report_file),
        ]
        ret = main(argv)
        self.assertEqual(ret, 0)
        self.assertTrue(report_file.exists())
        data = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertTrue(data["dry_run"])
        self.assertTrue(data["summary"]["success"])

    def test_cli_validate_clean(self) -> None:
        argv = [
            "--source",
            str(self.src_root),
            "--validate",
            "--json",
        ]
        ret = main(argv)
        self.assertEqual(ret, 0)

    def test_cli_validate_dirty_fails(self) -> None:
        dirty_file = self.src_root / "research" / "leaked.env"
        dirty_file.write_text("OPENAI_KEY=[REDACTED_OPENAI_KEY]\n", encoding="utf-8")

        argv = [
            "--source",
            str(self.src_root),
            "--validate",
            "--json",
        ]
        ret = main(argv)
        self.assertEqual(ret, 1)

    def test_format_text_report(self) -> None:
        report = SyncReport(
            timestamp_utc="2026-08-24T12:00:00Z",
            source_root=str(self.src_root),
            dest_root=str(self.dst_root),
            dry_run=True,
            repos={
                "agent-skills-and-tools": RepoSyncResult(
                    repo_name="agent-skills-and-tools",
                    status="success",
                    source_dir="src",
                    dest_dir="dst",
                    files_scanned=5,
                    files_synced=5,
                    files_modified=1,
                    files_unchanged=4,
                    redactions_count=1,
                    audit_log=[
                        {
                            "file": "SKILL.md",
                            "line": 10,
                            "rule": "openai_api_key",
                            "match_preview": "sk-proj-...",
                            "replacement": "[REDACTED_OPENAI_KEY]",
                        }
                    ],
                )
            },
            summary={
                "total_repos": 1,
                "total_files_scanned": 5,
                "total_files_synced": 5,
                "total_redactions": 1,
                "total_errors": 0,
                "success": True,
            },
        )
        text = format_text_report(report)
        self.assertIn("Multi-Repo Synchronization & Redaction Report", text)
        self.assertIn("DRY-RUN (Simulated)", text)
        self.assertIn("agent-skills-and-tools", text)
        self.assertIn("openai_api_key", text)


if __name__ == "__main__":
    unittest.main()
