"""Tests for Google Suite operations, administration, security gates, and downstream redaction.

tags: [tests, google, drive, gmail, security, redaction]
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.google.google_suite_ops import (
    DEFAULT_TEST_FOLDER_ID,
    DEFAULT_TEST_FOLDER_URL,
    collect_workspace_metadata,
    drive_create_file,
    drive_search,
    drive_sync_down,
    drive_update_file,
    generate_mock_standard_content,
    gmail_draft_email,
    gmail_read_message,
    gmail_search,
    gmail_send_email,
    validate_file_formatting,
)
from scripts.google.google_suite_admin import (
    audit_workspace_domain,
    audit_workspace_licenses,
)
from scripts.sync.sync_public_repos import RedactionEngine


class TestGoogleDriveOps(unittest.TestCase):
    def test_drive_search(self) -> None:
        res = drive_search(query="type:document", limit=2)
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "drive_search")
        self.assertLessEqual(len(res["files"]), 2)
        self.assertEqual(res["folder_id"], DEFAULT_TEST_FOLDER_ID)

    def test_drive_create_file(self) -> None:
        res = drive_create_file(name="test_report.md", content="# Test Report\n\nContent body.")
        self.assertTrue(res["ok"])
        self.assertIn("mock_file_", res["file_id"])
        self.assertGreater(res["bytes_written"], 0)

    def test_drive_update_file(self) -> None:
        res = drive_update_file(file_id="mock_file_123456", content="# Updated\n\nUpdated body.")
        self.assertTrue(res["ok"])
        self.assertEqual(res["file_id"], "mock_file_123456")

    def test_validate_file_formatting_valid(self) -> None:
        valid_md = "---\nkey: val\n---\n\n# Document Title\n\n## Section 1\nBody text.\n"
        res = validate_file_formatting(valid_md, "test.md")
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["errors"]), 0)

    def test_validate_file_formatting_multiple_h1(self) -> None:
        bad_md = "# Title 1\n\n# Title 2\n"
        res = validate_file_formatting(bad_md, "bad.md")
        self.assertFalse(res["ok"])
        self.assertTrue(any("Multiple top-level H1" in e for e in res["errors"]))

    def test_validate_file_formatting_empty(self) -> None:
        res = validate_file_formatting("", "empty.md")
        self.assertFalse(res["ok"])
        self.assertTrue(any("File is completely empty" in e for e in res["errors"]))

    def test_drive_sync_down(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            res = drive_sync_down(dest_dir=tmpdir)
            self.assertTrue(res["ok"])
            self.assertGreater(res["files_synced"], 0)
            synced_file = Path(tmpdir) / "google-suite-interaction-and-administration.md"
            self.assertTrue(synced_file.is_file())


class TestGmailOps(unittest.TestCase):
    def test_gmail_search(self) -> None:
        res = gmail_search(query="subject:security")
        self.assertTrue(res["ok"])
        self.assertGreaterEqual(len(res["messages"]), 1)

    def test_gmail_read_message(self) -> None:
        res = gmail_read_message(message_id="msg_001_sec_alert")
        self.assertTrue(res["ok"])
        self.assertEqual(res["headers"]["SPF"], "PASS")
        self.assertIn("Google Workspace", res["body_plain"])

    def test_gmail_draft_email(self) -> None:
        res = gmail_draft_email(
            to="user@example.com",
            subject="Draft Security Alert",
            body="Security alert body text.",
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "drafted_saved")
        self.assertIn("draft_", res["draft_id"])

    def test_gmail_send_email_unauthorized_rejection(self) -> None:
        # Crucial security gate: Sending WITHOUT authorization MUST fail
        res = gmail_send_email(draft_id="draft_12345", authorization_token=None)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "authorization_rejected")
        self.assertIn("Security Gate Blocked", res["error"])

    def test_gmail_send_email_authorized_success(self) -> None:
        # Sending WITH explicit human approval succeeds
        res = gmail_send_email(
            draft_id="draft_12345",
            authorization_token="EXPLICIT_HUMAN_APPROVAL",
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "sent")
        self.assertTrue(res["authorization_verified"])


class TestGoogleSuiteAdmin(unittest.TestCase):
    def test_audit_workspace_domain(self) -> None:
        res = audit_workspace_domain(domain="example.com")
        self.assertTrue(res["ok"])
        self.assertEqual(res["compliance_status"], "compliant")
        posture = res["security_posture"]
        self.assertTrue(posture["sso_enforced"])
        self.assertEqual(posture["mfa_enforcement"]["status"], "ENFORCED")
        self.assertTrue(posture["zero_data_retention"]["verified"])
        self.assertGreaterEqual(len(posture["dlp_rules"]), 2)

    def test_audit_workspace_licenses(self) -> None:
        res = audit_workspace_licenses(domain="example.com")
        self.assertTrue(res["ok"])
        self.assertEqual(res["total_active_seats"], 28)
        self.assertEqual(res["total_unassigned_seats"], 7)
        self.assertGreater(len(res["cost_optimization_recommendations"]), 0)


class TestMetadataCollector(unittest.TestCase):
    def test_collect_all_services(self) -> None:
        res = collect_workspace_metadata(service="all")
        self.assertTrue(res["ok"])
        self.assertIn("drive", res["metadata"])
        self.assertIn("gmail", res["metadata"])
        self.assertIn("users", res["metadata"])
        self.assertIn("calendar", res["metadata"])


class TestGoogleSuiteRedaction(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RedactionEngine()

    def test_redact_test_folder_url_and_id(self) -> None:
        sample = (
            f"Testing Google Drive folder at {DEFAULT_TEST_FOLDER_URL}\n"
            f"Folder ID: {DEFAULT_TEST_FOLDER_ID}\n"
        )
        redacted, audits = self.engine.redact_text(sample, "test.md")
        self.assertNotIn(DEFAULT_TEST_FOLDER_ID, redacted)
        self.assertIn("[REDACTED_GOOGLE_DRIVE_TEST_FOLDER]", redacted)
        self.assertGreaterEqual(len(audits), 1)


if __name__ == "__main__":
    unittest.main()
