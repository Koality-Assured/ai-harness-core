"""Unit and integration tests for Confluence knowledge-space sync and bi-directional drift reconciliation.

tags: [tests, confluence, sync, drift, storage-format]
routing_hints: [tests, confluence-sync, confluence-drift]

Run: python -m unittest scripts/tests/test_confluence_sync.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.confluence.confluence_sync import (
    ConfluenceSyncEngine,
    ManagedPageRecord,
    SyncManifest,
    generate_synthetic_corpus,
    parse_frontmatter,
    render_markdown_to_storage_xhtml,
    storage_xhtml_to_markdown,
)


class TestConfluenceSync(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parse_frontmatter(self) -> None:
        sample = """---
title: "Data Protection Policy"
document_type: "policy"
owner: "secops"
framework_mapping: ["cis-controls", "nist-csf"]
last_published_version: 2
---

# Policy Overview

Protect data at rest and in transit.
"""
        meta, body = parse_frontmatter(sample)
        self.assertEqual(meta.get("title"), "Data Protection Policy")
        self.assertEqual(meta.get("document_type"), "policy")
        self.assertEqual(meta.get("owner"), "secops")
        self.assertEqual(meta.get("framework_mapping"), ["cis-controls", "nist-csf"])
        self.assertEqual(meta.get("last_published_version"), 2)
        self.assertIn("# Policy Overview", body)

    def test_render_markdown_to_storage_xhtml(self) -> None:
        meta = {
            "title": "Cloud Security Standard",
            "document_type": "standard",
            "owner": "secengineering",
            "lifecycle": "active",
            "review_cadence": "annual",
            "framework_mapping": ["nist-csf"],
        }
        md = """# Cloud Security Standard

Guidelines for cloud configurations.

> [!NOTE]
> Review IAM policies regularly.

## Core Controls

1. Enforce MFA across all console logins.
2. Encrypt all volumes.

```python
def check_mfa(user):
    return user.has_mfa()
```

| Resource | Encrypted |
|---|---|
| S3 | Yes |
| EBS | Yes |
"""
        xhtml = render_markdown_to_storage_xhtml(md, meta=meta, include_toc=True)

        # Check metadata panel
        self.assertIn('<ac:structured-macro ac:name="panel"', xhtml)
        self.assertIn("Cloud Security Standard", xhtml)
        self.assertIn("ACTIVE", xhtml)

        # Check TOC macro
        self.assertIn('<ac:structured-macro ac:name="toc"', xhtml)

        # Check alert / note macro
        self.assertIn('<ac:structured-macro ac:name="info"', xhtml)
        self.assertIn("Review IAM policies regularly.", xhtml)

        # Check code macro
        self.assertIn('<ac:structured-macro ac:name="code"', xhtml)
        self.assertIn('language">python', xhtml)
        self.assertIn("check_mfa", xhtml)

        # Check table
        self.assertIn("<table><tbody><tr><th>Resource</th><th>Encrypted</th></tr>", xhtml)

    def test_storage_xhtml_to_markdown_reverse_conversion(self) -> None:
        original_md = """# Container Security

Guidelines for container deployment.

> [!NOTE]
> Run images as unprivileged users.

```bash
docker run --read-only secure-app:latest
```"""
        xhtml = render_markdown_to_storage_xhtml(original_md, meta=None, include_toc=False)
        extracted_md = storage_xhtml_to_markdown(xhtml)

        self.assertIn("# Container Security", extracted_md)
        self.assertIn("> [!NOTE]", extracted_md)
        self.assertIn("Run images as unprivileged users.", extracted_md)
        self.assertIn("```bash", extracted_md)
        self.assertIn("docker run --read-only secure-app:latest", extracted_md)

    def test_sync_engine_plan_and_dry_run_publish(self) -> None:
        docs_dir = self.root / "docs" / "standards"
        docs_dir.mkdir(parents=True, exist_ok=True)
        sample_doc = docs_dir / "sample-sec.md"
        sample_doc.write_text(
            """---
title: "Sample Security Standard"
document_type: "standard"
owner: "secops"
lifecycle: "active"
parent_path: "Documentation/Standards"
---

# Sample Standard Content

Requirements for testing.
""",
            encoding="utf-8",
        )

        state_file = self.root / "results" / "confluence_sync_state.json"
        engine = ConfluenceSyncEngine(
            workspace="koality-assured",
            space_key="SEC",
            state_file=state_file,
            source_root=self.root,
            dry_run=True,
        )

        plan = engine.plan_publish()
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["action"], "CREATE")
        self.assertEqual(plan[0]["title"], "Sample Security Standard")
        self.assertEqual(plan[0]["parent_path"], "Documentation/Standards")

        res = engine.execute_publish(plan)
        self.assertEqual(res["created"], 1)
        self.assertEqual(res["errors"], 0)

    def test_bidirectional_drift_detection_and_reverse_reconciliation(self) -> None:
        docs_dir = self.root / "docs" / "standards"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_file = docs_dir / "appsec-standard.md"
        doc_file.write_text(
            """---
title: "AppSec Standard"
document_type: "standard"
owner: "appsec"
lifecycle: "active"
parent_path: "Documentation/Standards"
---

# Application Security Standard

Version 1 content.
""",
            encoding="utf-8",
        )

        state_file = self.root / "results" / "confluence_sync_state.json"
        engine = ConfluenceSyncEngine(
            workspace="koality-assured",
            space_key="SEC",
            state_file=state_file,
            source_root=self.root,
            dry_run=False,
        )

        # 1. Initial Publish
        plan = engine.plan_publish()
        pub_res = engine.execute_publish(plan)
        self.assertEqual(pub_res["created"], 1)

        # Get assigned page ID
        rel_key = "docs/standards/appsec-standard.md"
        self.assertIn(rel_key, engine.manifest.pages)
        page_id = engine.manifest.pages[rel_key].page_id

        # 2. Check drift when nothing has changed -> IN_SYNC
        mock_in_sync = {
            page_id: {
                "id": page_id,
                "version": {"number": 1},
                "body": {
                    "storage": {
                        "value": plan[0]["rendered_body"],
                    }
                },
            }
        }
        drift_recs = engine.check_drift(mock_remote_pages=mock_in_sync)
        self.assertEqual(len(drift_recs), 1)
        self.assertEqual(drift_recs[0].drift_status, "IN_SYNC")

        # 3. Simulate remote edit on Confluence Cloud (bump version to 2 and change text)
        updated_remote_xhtml = """<h1>Application Security Standard</h1><p>Version 2 content updated in Confluence UI.</p>"""
        mock_remote_edit = {
            page_id: {
                "id": page_id,
                "version": {"number": 2},
                "body": {
                    "storage": {
                        "value": updated_remote_xhtml,
                    }
                },
            }
        }

        drift_recs = engine.check_drift(mock_remote_pages=mock_remote_edit)
        self.assertEqual(len(drift_recs), 1)
        self.assertEqual(drift_recs[0].drift_status, "REMOTE_MODIFIED")

        # 4. Generate reverse diff
        diff_text, local_body, remote_md = engine.generate_reverse_diff(
            page_id=page_id,
            mock_remote_pages=mock_remote_edit,
        )
        self.assertIn("Version 1 content", diff_text)
        self.assertIn("Version 2 content updated in Confluence UI", diff_text)

        # 5. Apply reverse patch back into local Wiki source
        patch_res = engine.apply_reverse_patch(
            page_id=page_id,
            mock_remote_pages=mock_remote_edit,
        )
        self.assertTrue(patch_res["ok"])
        self.assertEqual(patch_res["new_version"], 2)

        # Verify local file updated
        updated_local_content = doc_file.read_text(encoding="utf-8")
        self.assertIn("Version 2 content updated in Confluence UI", updated_local_content)
        self.assertIn("last_published_version: 2", updated_local_content)

    def test_conflict_detection_when_both_local_and_remote_modified(self) -> None:
        docs_dir = self.root / "docs" / "standards"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_file = docs_dir / "conflict-doc.md"
        doc_file.write_text(
            """---
title: "Conflict Test Standard"
document_type: "standard"
---

# Base Version
""",
            encoding="utf-8",
        )

        state_file = self.root / "results" / "confluence_sync_state.json"
        engine = ConfluenceSyncEngine(
            workspace="koality-assured",
            space_key="SEC",
            state_file=state_file,
            source_root=self.root,
            dry_run=False,
        )

        engine.execute_publish(engine.plan_publish())
        rel_key = "docs/standards/conflict-doc.md"
        page_id = engine.manifest.pages[rel_key].page_id

        # Modify local file
        doc_file.write_text(
            """---
title: "Conflict Test Standard"
document_type: "standard"
---

# Local Edit Version
""",
            encoding="utf-8",
        )

        # Simulate remote edit
        mock_remote_conflict = {
            page_id: {
                "id": page_id,
                "version": {"number": 2},
                "body": {
                    "storage": {
                        "value": "<h1>Remote Edit Version</h1>",
                    }
                },
            }
        }

        drift_recs = engine.check_drift(mock_remote_pages=mock_remote_conflict)
        self.assertEqual(len(drift_recs), 1)
        self.assertEqual(drift_recs[0].drift_status, "CONFLICT")

    def test_synthetic_corpus_generator(self) -> None:
        synth_dir = self.root / "synthetic_test_docs"
        files = generate_synthetic_corpus(synth_dir)
        self.assertEqual(len(files), 3)
        for f in files:
            self.assertTrue(f.exists())
            content = f.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(content)
            self.assertTrue(bool(meta.get("title")))
            self.assertTrue(len(body) > 20)


if __name__ == "__main__":
    unittest.main()
