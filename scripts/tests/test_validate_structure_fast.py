"""Unit tests for fast structural validator.

tags: [tests, docs, validation]
routing_hints: [tests, validate_structure_fast, markdown]

Run: python -m unittest scripts.tests.test_validate_structure_fast -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "docs"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from validate_structure_fast import (  # noqa: E402
    extract_headings_and_h1,
    extract_links_from_text,
    main,
    parse_yaml_frontmatter,
    slugify,
    validate_all_structure,
    validate_file_frontmatter,
    validate_file_h1,
    validate_relative_links,
)


class ValidateStructureFastTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("`Heading` with [Link](url) & Symbols!"), "heading-with-link-symbols")
        self.assertEqual(slugify("  Multiple   Spaces  -- Test  "), "multiple-spaces-test")

    def test_extract_headings_and_h1(self) -> None:
        doc = """---
doc_kind: requirement
canonical_id: test-doc
purpose: Unit test
---

# Title One

Some intro text.

```python
# Not an H1
def foo():
    pass
```

## Section One

More text.

### Nested Subsection
"""
        h1s, slugs = extract_headings_and_h1(doc)
        self.assertEqual(len(h1s), 1)
        self.assertEqual(h1s[0][1], "Title One")
        self.assertIn("title-one", slugs)
        self.assertIn("section-one", slugs)
        self.assertIn("nested-subsection", slugs)
        self.assertNotIn("not-an-h1", slugs)

    def test_multiple_h1_detection(self) -> None:
        doc = "# First Title\n\nText\n\n# Second Title\n"
        h1s, _ = extract_headings_and_h1(doc)
        self.assertEqual(len(h1s), 2)
        errs = validate_file_h1("test.md", h1s)
        self.assertEqual(len(errs), 1)
        self.assertIn("multiple", errs[0])

    def test_missing_h1_detection(self) -> None:
        doc = "## Only H2\n\nText\n"
        h1s, _ = extract_headings_and_h1(doc)
        self.assertEqual(len(h1s), 0)
        errs = validate_file_h1("test.md", h1s)
        self.assertEqual(len(errs), 1)
        self.assertIn("missing", errs[0])

    def test_frontmatter_parsing_and_validation(self) -> None:
        valid_fm = """---
doc_kind: requirement
canonical_id: req-001
purpose: Validate frontmatter
---

# Req 001
"""
        fm, err, _ = parse_yaml_frontmatter(valid_fm)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm.get("doc_kind"), "requirement")
        errs = validate_file_frontmatter(Path("docs/req.md"), "docs/req.md", valid_fm, fm, err)
        self.assertEqual(errs, [])

        missing_purpose = """---
doc_kind: requirement
canonical_id: req-001
---

# Req 001
"""
        fm, err, _ = parse_yaml_frontmatter(missing_purpose)
        errs = validate_file_frontmatter(Path("docs/req.md"), "docs/req.md", missing_purpose, fm, err)
        self.assertTrue(any("missing required tag 'purpose'" in e for e in errs))

    def test_link_and_anchor_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            target = tmp / "target.md"
            target.write_text("# Target Title\n\n## Sub Section\n", encoding="utf-8")

            source = tmp / "source.md"
            source.write_text(
                "# Source Title\n\n"
                "[Valid Link](./target.md#sub-section)\n"
                "[Broken Link](./missing.md)\n"
                "[Broken Anchor](./target.md#non-existent)\n"
                "[External Link](https://example.com)\n",
                encoding="utf-8",
            )

            links = extract_links_from_text(source.read_text(encoding="utf-8"))
            headings_cache = {}
            errs = validate_relative_links(source, "source.md", links, headings_cache, tmp)

            self.assertEqual(len(errs), 2)
            self.assertTrue(any("missing.md" in e for e in errs))
            self.assertTrue(any("non-existent" in e for e in errs))

    def test_cli_execution(self) -> None:
        import io
        from contextlib import redirect_stdout

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            doc = tmp / "sample.md"
            doc.write_text("# Sample Title\n\nSample content.\n", encoding="utf-8")

            f = io.StringIO()
            with redirect_stdout(f):
                rc = main(["--path", str(doc), "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(f.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["file_count"], 1)


if __name__ == "__main__":
    unittest.main()
