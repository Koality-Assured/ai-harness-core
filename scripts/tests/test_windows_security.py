"""Focused tests for fixture-only Windows security audit evaluators.

tags: [windows-security, active-directory, group-policy, audit, tests]
routing_hints: [windows-security-tests, fixture-validation, read-only]
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

_SECURITY_DIR = Path(__file__).resolve().parents[1] / "windows-security"
sys.path.insert(0, str(_SECURITY_DIR))

from evaluate_ad_gpo_snapshot import evaluate_ad_gpo_snapshot, main as ad_main  # noqa: E402
from evaluate_host_security import evaluate_host_security, main as host_main  # noqa: E402
from _common import FixtureError  # noqa: E402


AD_COMPLIANT = {
    "domain": {"recycle_bin_enabled": True, "protected_users_group_present": True},
    "controls": {
        "password_min_length": 14,
        "password_history_count": 24,
        "account_lockout_threshold": 5,
        "account_lockout_duration_minutes": 15,
        "sysvol_dfrs_enabled": True,
        "windows_laps_enabled": True,
        "ldap_signing": "required",
        "ldap_channel_binding": "enforced",
        "smb_signing": True,
        "ntlm_restriction": "enabled",
    },
}

HOST_COMPLIANT = {
    "security_options": {
        "firewall_domain_enabled": True,
        "firewall_private_enabled": True,
        "firewall_public_enabled": True,
        "defender_realtime_monitoring": True,
        "uac_enabled": True,
        "uac_admin_approval_mode": True,
        "lsa_protection_enabled": True,
        "credential_guard_enabled": True,
        "smb1_disabled": True,
        "smb_signing_required": True,
    },
    "audit_policy": {
        "Account Logon": {"Credential Validation": ["Success", "Failure"]},
        "Logon/Logoff": {"Logon": "Success and Failure", "Account Lockout": "Failure"},
        "Account Management": {"User Account Management": "Success and Failure"},
        "Policy Change": {"Audit Policy Change": "Success and Failure"},
        "Detailed Tracking": {"Process Creation": "Success"},
    },
}


class WindowsSecurityEvaluatorTests(unittest.TestCase):
    def test_ad_compliant_fixture_is_deterministic_and_declares_safety(self) -> None:
        first, first_code = evaluate_ad_gpo_snapshot(
            AD_COMPLIANT, scope="example.test domain", authorization_note="ticket-AD-READONLY", dry_run=True
        )
        second, second_code = evaluate_ad_gpo_snapshot(
            AD_COMPLIANT, scope="example.test domain", authorization_note="ticket-AD-READONLY", dry_run=True
        )
        self.assertEqual(first, second)
        self.assertEqual(first_code, 0)
        self.assertTrue(first["ok"])
        self.assertEqual(first["status"], "compliant")
        self.assertEqual(first["scope"]["authorization"]["note"], "ticket-AD-READONLY")
        self.assertFalse(first["scope"]["authorization"]["verified"])
        self.assertFalse(first["safety"]["network_access"])
        self.assertFalse(first["safety"]["mutations_performed"])
        self.assertEqual(first["scope"]["baseline_profile"], "non-universal-ad-starter-v1")

    def test_ad_failed_and_missing_controls_are_nonzero(self) -> None:
        snapshot = {"controls": {"password_min_length": 8, "ldap_signing": "disabled"}}
        report, exit_code = evaluate_ad_gpo_snapshot(
            snapshot, scope="example.test", authorization_note="approved-read-only"
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "non_compliant")
        self.assertGreater(report["summary"]["failed"], 0)
        self.assertGreater(report["summary"]["unknown"], 0)

    def test_host_compliant_fixture_supports_success_failure_lists(self) -> None:
        report, exit_code = evaluate_host_security(
            HOST_COMPLIANT, scope="WIN-TEST-01", authorization_note="change-review-read-only"
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["status"], "compliant")
        self.assertEqual(report["summary"]["controls_evaluated"], 16)
        self.assertEqual(report["scope"]["baseline_profile"], "non-universal-windows-host-starter-v1")

    def test_host_bad_audit_policy_is_reported(self) -> None:
        snapshot = {"security_options": {"firewall_public_enabled": False}, "audit_policy": {}}
        report, exit_code = evaluate_host_security(
            snapshot, scope="WIN-TEST-02", authorization_note="approved-read-only"
        )
        self.assertEqual(exit_code, 1)
        self.assertEqual(report["status"], "non_compliant")
        self.assertTrue(any(check["control"] == "host.firewall_public" for check in report["checks"]))

    def test_credential_fields_are_rejected_even_for_direct_api_use(self) -> None:
        with self.assertRaises(FixtureError):
            evaluate_ad_gpo_snapshot(
                {"controls": {"password": "not-accepted"}},
                scope="example.test",
                authorization_note="approved-read-only",
            )

    def test_cli_fixture_path_emits_json_and_returns_findings_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "host.json"
            fixture.write_text(json.dumps(HOST_COMPLIANT), encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = host_main(
                    [
                        "--fixture",
                        str(fixture),
                        "--scope",
                        "WIN-TEST-03",
                        "--authorization-note",
                        "ci-fixture-approved",
                        "--dry-run",
                        "--baseline-profile",
                        "org-windows-server-v1",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["evaluator"], "windows-host-security")
            self.assertTrue(result["scope"]["dry_run"])
            self.assertEqual(result["scope"]["baseline_profile"], "org-windows-server-v1")

    def test_baseline_profile_rejects_empty_and_control_text(self) -> None:
        for evaluator, snapshot, scope in (
            (evaluate_ad_gpo_snapshot, AD_COMPLIANT, "example.test"),
            (evaluate_host_security, HOST_COMPLIANT, "WIN-TEST-04"),
        ):
            for profile in ("", "starter\nprofile"):
                with self.subTest(profile=profile):
                    with self.assertRaises(FixtureError):
                        evaluator(snapshot, scope=scope, authorization_note="approved-read-only", baseline_profile=profile)

    def test_cli_requires_fixture_and_metadata(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            ad_main([])
        self.assertEqual(raised.exception.code, 2)

        with self.assertRaises(SystemExit) as raised:
            ad_main(["--fixture", "-", "--scope", "example.test", "--authorization-note", "approved-read-only"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
