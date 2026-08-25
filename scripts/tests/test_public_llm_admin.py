"""Unit tests for scripts/llm/public_llm_admin.py.

tags: [tests, llm, admin]
routing_hints: [tests, public-llm-admin, openai, anthropic, gemini]
"""

import unittest
from pathlib import Path
import sys

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))

from llm.public_llm_admin import audit_workspace, audit_spend, main


class TestPublicLLMAdmin(unittest.TestCase):
    def test_audit_anthropic(self):
        res = audit_workspace("anthropic", "ws-engineering-dev")
        self.assertEqual(res["provider"], "anthropic")
        self.assertEqual(res["workspace_id"], "ws-engineering-dev")
        self.assertTrue(res["zero_data_retention"])
        self.assertTrue(res["sso_enforced"])
        self.assertEqual(res["compliance_status"], "compliant")

    def test_audit_openai(self):
        res = audit_workspace("openai", "proj-dev-sandbox")
        self.assertEqual(res["provider"], "openai")
        self.assertEqual(res["project_id"], "proj-dev-sandbox")
        self.assertTrue(res["zero_data_retention"])
        self.assertTrue(res["scim_enabled"])

    def test_audit_gemini(self):
        res = audit_workspace("gemini", "prj-ai-dev-sandbox")
        self.assertEqual(res["provider"], "gemini")
        self.assertTrue(res["vpc_service_controls_enforced"])
        self.assertEqual(res["compliance_status"], "compliant")

    def test_audit_unsupported(self):
        with self.assertRaises(ValueError):
            audit_workspace("unsupported_provider")

    def test_audit_spend(self):
        res = audit_spend("openai", "proj-dev-sandbox")
        self.assertEqual(res["provider"], "openai")
        self.assertEqual(res["monthly_budget_usd"], 5000.00)
        self.assertEqual(res["budget_status"], "normal")

    def test_cli_audit_json(self):
        exit_code = main(["audit", "--provider", "anthropic", "--workspace", "ws-dev", "--json"])
        self.assertEqual(exit_code, 0)

    def test_cli_spend_json(self):
        exit_code = main(["spend", "--provider", "gemini", "--project", "prj-dev", "--json"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
