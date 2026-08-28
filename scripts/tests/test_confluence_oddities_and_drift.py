"""Comprehensive test suite for Confluence oddities, formatting edge cases, and bi-directional drift reconciliation.

tags: [tests, confluence, oddities, drift, bi-directionality, storage-format]
routing_hints: [tests, confluence-sync, confluence-drift, confluence-oddities]

Run: python -m unittest scripts/tests/test_confluence_oddities_and_drift.py -v
"""

from __future__ import annotations

import html
from pathlib import Path
import tempfile
import unittest

from scripts.confluence.confluence_sync import (
    ConfluenceSyncEngine,
    ManagedPageRecord,
    SyncManifest,
    parse_frontmatter,
    render_markdown_to_storage_xhtml,
    storage_xhtml_to_markdown,
)


class TestConfluenceOdditiesAndDrift(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # ------------------------------------------------------------------
    # 1. Formatting Oddities & Edge Cases
    # ------------------------------------------------------------------

    def test_oddity_complex_table_with_formatting(self) -> None:
        """Test multi-column tables with bold, code, links, and special chars inside cells."""
        md = """# Architecture Standards

| Component | Target SLA | Required Signoff | API Spec |
| --- | --- | --- | --- |
| **Auth Service** | &le; 15 mins | `CISO & SecArch` | [Specs](https://api.example.com/v1) |
| **Data Vault** | &le; 1 hour | `DBA Lead` | [Vault Docs](https://vault.example.com) |
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn("<table><tbody>", xhtml)
        self.assertIn("<th>Component</th>", xhtml)
        self.assertIn("<strong>Auth Service</strong>", xhtml)
        self.assertIn("<code>CISO &amp; SecArch</code>", xhtml)

        # Reverse convert back to Markdown
        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("| Component | Target SLA | Required Signoff | API Spec |", extracted_md)
        self.assertIn("| **Auth Service** | &le; 15 mins | `CISO & SecArch` |", extracted_md)

    def test_oddity_expandable_details_block(self) -> None:
        """Test expandable details / summary accordion conversion."""
        md = """# FAQ Section

<details>
<summary>How do I rotate credentials?</summary>

Use the AWS CLI or HashiCorp Vault to trigger automated rotation.

</details>
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn('<ac:structured-macro ac:name="expand"', xhtml)
        self.assertIn('How do I rotate credentials?', xhtml)
        self.assertIn('Use the AWS CLI or HashiCorp Vault', xhtml)

        # Reverse convert back to Markdown
        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("<details>", extracted_md)
        self.assertIn("<summary>How do I rotate credentials?</summary>", extracted_md)
        self.assertIn("Use the AWS CLI or HashiCorp Vault", extracted_md)

    def test_oddity_all_alert_types(self) -> None:
        """Test all 5 GitHub-style alerts: NOTE, TIP, IMPORTANT, WARNING, CAUTION."""
        md = """# Alert Testing

> [!NOTE]
> Informational notice for developers.

> [!TIP]
> Use SSH signing keys for Git commits.

> [!IMPORTANT]
> Phishing-resistant MFA is strictly mandatory.

> [!WARNING]
> Do not disable TLS certificate validation.

> [!CAUTION]
> Hardcoded secrets in production trigger immediate account lockouts.
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn('ac:name="info"', xhtml)
        self.assertIn('ac:name="tip"', xhtml)
        self.assertIn('ac:name="warning"', xhtml)

        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("> [!NOTE]", extracted_md)
        self.assertIn("> [!TIP]", extracted_md)
        self.assertIn("> [!WARNING]", extracted_md)

    def test_oddity_code_blocks_with_special_chars_and_cdata(self) -> None:
        """Test code blocks containing XML entities (<, >, &, \", ') and varied languages."""
        md = """# Code Snippet Test

```xml
<configuration version="2.0">
    <property name="auth.enabled" value="true" />
    <filter expression="user.role == 'admin' && env != 'prod'" />
</configuration>
```

```python
def sanitize_input(val: str) -> str:
    # Handle & < > " '
    return val.replace("&", "&amp;").replace("<", "&lt;")
```
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn('language">xml', xhtml)
        self.assertIn('language">python', xhtml)
        self.assertIn("<![CDATA[", xhtml)

        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("```xml", extracted_md)
        self.assertIn("```python", extracted_md)
        self.assertIn("auth.enabled", extracted_md)
        self.assertIn("sanitize_input", extracted_md)

    def test_oddity_task_lists_and_checkboxes(self) -> None:
        """Test task list checkboxes: - [ ] and - [x]."""
        md = """# Onboarding Checklist

- [x] Configure Okta SSO and FIDO2 Passkey
- [ ] Set up GPG signing key on GitHub
- [ ] Complete Security Architecture training
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn("☑", xhtml)
        self.assertIn("☐", xhtml)
        self.assertIn("Configure Okta SSO", xhtml)

        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("- [x] Configure Okta SSO and FIDO2 Passkey", extracted_md)
        self.assertIn("- [ ] Set up GPG signing key on GitHub", extracted_md)

    def test_oddity_nested_and_mixed_formatting(self) -> None:
        """Test mixed inline formatting: bold within links, code within lists, underscores."""
        md = """# Mixed Formatting

- Run `kubectl get pods -n secure` to verify.
- See [**Cloud Architecture Blueprint**](https://wiki.example.com/cloud) for details.
- Configuration key: `AWS_DEFAULT_REGION`
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn("<code>kubectl get pods -n secure</code>", xhtml)
        self.assertIn('<a href="https://wiki.example.com/cloud"><strong>Cloud Architecture Blueprint</strong></a>', xhtml)

        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("`kubectl get pods -n secure`", extracted_md)
        self.assertIn("[**Cloud Architecture Blueprint**](https://wiki.example.com/cloud)", extracted_md)

    def test_oddity_unicode_and_emojis(self) -> None:
        """Test preservation of emojis, non-ASCII symbols, and mathematical notation."""
        md = """# Unicode and Emojis

🛡️ Security Shield | ⚡ Fast Performance | 🔒 Locked Vault

Mathematical boundary: &le; 15 mins &ge; 99.99% uptime.
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=None, include_toc=False)
        self.assertIn("🛡️", xhtml)
        self.assertIn("⚡", xhtml)

        extracted_md = storage_xhtml_to_markdown(xhtml)
        self.assertIn("🛡️", extracted_md)
        self.assertIn("⚡", extracted_md)

    # ------------------------------------------------------------------
    # 2. Bi-Directional Drift Detection & Reconciliation
    # ------------------------------------------------------------------

    def test_drift_detection_all_states(self) -> None:
        """Validate accurate categorization of IN_SYNC, LOCAL_MODIFIED, REMOTE_MODIFIED, and CONFLICT."""
        docs_dir = self.root / "docs" / "standards"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc1 = docs_dir / "doc1.md"
        doc1.write_text("---\ntitle: Doc 1\n---\n# Body 1\n", encoding="utf-8")

        state_file = self.root / "confluence_sync_state.json"
        engine = ConfluenceSyncEngine(
            workspace="koality-assured",
            space_key="SEC",
            state_file=state_file,
            source_root=self.root,
            dry_run=True,
        )

        # Baseline publish
        plan = engine.plan_publish()
        engine.execute_publish(plan=plan, scaffold_ia=False)

        # 1. Check in sync
        records = engine.check_drift()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].drift_status, "IN_SYNC")

        # 2. Check LOCAL_MODIFIED
        doc1.write_text("---\ntitle: Doc 1\n---\n# Body 1 with Local Edits\n", encoding="utf-8")
        records = engine.check_drift()
        self.assertEqual(records[0].drift_status, "LOCAL_MODIFIED")

        # Revert local to match published
        doc1.write_text("---\ntitle: Doc 1\n---\n# Body 1\n", encoding="utf-8")

        # 3. Check REMOTE_MODIFIED
        mock_remote = {
            records[0].page_id: {
                "version": {"number": 2},
                "body": {"storage": {"value": "<h1>Body 1 with Remote Edits</h1>"}},
            }
        }
        records = engine.check_drift(mock_remote_pages=mock_remote)
        self.assertEqual(records[0].drift_status, "REMOTE_MODIFIED")

        # 4. Check CONFLICT (both local and remote changed)
        doc1.write_text("---\ntitle: Doc 1\n---\n# Conflicting Local Edits\n", encoding="utf-8")
        records = engine.check_drift(mock_remote_pages=mock_remote)
        self.assertEqual(records[0].drift_status, "CONFLICT")

    def test_apply_reverse_patch_preserves_frontmatter(self) -> None:
        """Test applying a remote edit back to local source preserves all YAML frontmatter tags."""
        docs_dir = self.root / "docs" / "standards"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc = docs_dir / "auth-standard.md"
        original_content = """---
title: "Authentication Standard"
document_type: "standard"
owner: "seceng"
lifecycle: "active"
review_cadence: "annual"
framework_mapping: ["nist-csf", "soc-2"]
topics: ["auth", "mfa", "passkeys"]
---

# Authentication Standard

Original local markdown text.
"""
        doc.write_text(original_content, encoding="utf-8")

        state_file = self.root / "confluence_sync_state.json"
        engine = ConfluenceSyncEngine(
            workspace="koality-assured",
            space_key="SEC",
            state_file=state_file,
            source_root=self.root,
            dry_run=False,
        )

        plan = engine.plan_publish()
        engine.execute_publish(plan=plan, scaffold_ia=False)
        page_id = list(engine.manifest.pages.values())[0].page_id

        # Simulate remote Confluence Web UI edit
        mock_remote = {
            page_id: {
                "version": {"number": 2},
                "body": {
                    "storage": {
                        "value": "<h1>Authentication Standard</h1>\n<p>Updated remotely in Confluence Cloud UI.</p>\n<ac:structured-macro ac:name=\"info\" ac:schema-version=\"1\"><ac:rich-text-body><p>FIDO2 passkeys are mandatory.</p></ac:rich-text-body></ac:structured-macro>"
                    }
                },
            }
        }

        # Apply reverse patch
        res = engine.apply_reverse_patch(page_id=page_id, mock_remote_pages=mock_remote)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("new_version"), 2)

        # Inspect updated local file
        updated_text = doc.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(updated_text)

        self.assertEqual(meta.get("title"), "Authentication Standard")
        self.assertEqual(meta.get("document_type"), "standard")
        self.assertEqual(meta.get("owner"), "seceng")
        self.assertEqual(meta.get("last_published_version"), 2)
        self.assertIn("# Authentication Standard", body)
        self.assertIn("Updated remotely in Confluence Cloud UI.", body)
        self.assertIn("> [!NOTE]", body)
        self.assertIn("FIDO2 passkeys are mandatory.", body)

    def test_idempotent_round_trip(self) -> None:
        """Test that converting Markdown -> Storage XHTML -> Markdown is structurally stable and idempotent."""
        sample_md = """# Incident Response Protocol

Mandatory escalation procedures for SEV-0 and SEV-1 incidents.

> [!WARNING]
> Do not alter or reboot compromised instances.

## Escalation Matrix

| Severity | Response SLA | Target Containment |
| --- | --- | --- |
| SEV-0 | &le; 15 mins | &le; 4 hours |
| SEV-1 | &le; 1 hour | &le; 12 hours |

## Onboarding Checklist

- [x] Okta SSO Configured
- [ ] GPG Key Enrolled
"""
        xhtml_1 = render_markdown_to_storage_xhtml(sample_md, meta=None, include_toc=False)
        extracted_md_1 = storage_xhtml_to_markdown(xhtml_1)

        xhtml_2 = render_markdown_to_storage_xhtml(extracted_md_1, meta=None, include_toc=False)
        extracted_md_2 = storage_xhtml_to_markdown(xhtml_2)

        # The extracted Markdown from cycle 1 and cycle 2 must match exactly (idempotency)
        self.assertEqual(extracted_md_1, extracted_md_2)


if __name__ == "__main__":
    unittest.main()
