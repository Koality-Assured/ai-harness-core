"""Unit tests for scripts/cloud/cloud_admin.py.

tags: [tests, cloud, admin]
routing_hints: [tests, cloud-admin, aws, gcp, azure]
"""

import json
import unittest
from pathlib import Path
import sys

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS_DIR))

from cloud.cloud_admin import audit_hierarchy, plan_provisioning, main


class TestCloudAdmin(unittest.TestCase):
    def test_audit_aws(self):
        res = audit_hierarchy("aws", "Workloads")
        self.assertEqual(res["provider"], "aws")
        self.assertEqual(res["scope"], "Workloads")
        self.assertEqual(res["status"], "compliant")
        self.assertGreater(len(res["guardrails"]), 0)
        self.assertEqual(res["violations_found"], 0)

    def test_audit_gcp(self):
        res = audit_hierarchy("gcp", "fldr-workloads")
        self.assertEqual(res["provider"], "gcp")
        self.assertEqual(res["status"], "compliant")
        self.assertGreater(len(res["guardrails"]), 0)

    def test_audit_azure(self):
        res = audit_hierarchy("azure", "mg-landing-zones")
        self.assertEqual(res["provider"], "azure")
        self.assertEqual(res["status"], "compliant")
        self.assertGreater(len(res["guardrails"]), 0)

    def test_audit_unsupported(self):
        with self.assertRaises(ValueError):
            audit_hierarchy("unsupported_cloud")

    def test_plan_provisioning(self):
        res = plan_provisioning("aws", spec_data={"resource_type": "account", "name": "test-dev-01", "target_ou": "Workloads"})
        self.assertTrue(res["ok"])
        self.assertEqual(res["provider"], "aws")
        self.assertTrue(res["dry_run"])
        self.assertTrue(res["requires_human_authorization"])
        self.assertEqual(len(res["planned_resources"]), 1)
        self.assertEqual(res["planned_resources"][0]["name"], "test-dev-01")

    def test_cli_audit_json(self):
        exit_code = main(["audit", "--provider", "aws", "--ou", "Workloads", "--json"])
        self.assertEqual(exit_code, 0)

    def test_cli_plan_json(self):
        exit_code = main(["plan", "--provider", "gcp", "--json", "--dry-run"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
