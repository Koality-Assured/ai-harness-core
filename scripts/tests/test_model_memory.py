"""Unit tests for scripts/ai-tooling/model_memory.py.

tags: [tests, ai-tooling, memory]
routing_hints: [tests, model-memory, model-capability-memory]

Run: python -m unittest scripts.tests.test_model_memory -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "ai-tooling"))
sys.path.insert(0, str(_SCRIPTS / "_lib"))

from model_memory import (  # noqa: E402
    MODEL_FAMILIES,
    canonicalize_category,
    check_record,
    main,
    propose_promote,
    scan_forbidden,
    search_records,
    validate_tree,
)

MINI_AREAS = """\
areas:
  - id: docs
    purpose: Standards
    default_agent: documentation-ops
    load: via qmd
    write_back: Durable standards
  - id: scratch
    purpose: Temporary
    default_agent: router-maintenance
    load: minimally
    write_back: Never
  - id: ai-tooling
    purpose: Enablement
    default_agent: ai-tooling-ops
    load: when changing enablement
    write_back: New skill or memory
"""

SUCCESS_RECORD = """\
---
category: success
family: gpt
---

# qmd hybrid query on GPT

Proven capability: `qmd query` returns ranked hits for this family.

How: `qmd search --format json --min-score 0.5 -n 5 "capability"`.

Evidence: command output class was a non-empty hit list. Link user memory when host PATH mattered.
"""

UNAVAILABLE_RECORD = """\
---
category: unavailable
family: claude
---

# ast-grep outline missing on Claude host

Unavailable capability: `ast-grep outline` is not installed on this family host.

Why: command not found. Recovery: install via workstation onboarding, then retry outline-first reads.
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _repo() -> tempfile.TemporaryDirectory[str]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    _write(root / "routing" / "areas.yaml", MINI_AREAS)
    model = root / "ai-tooling" / "memory" / "model"
    (model / "gpt").mkdir(parents=True)
    (model / "claude").mkdir(parents=True)
    (model / "cursor").mkdir(parents=True)
    (model / "gemini").mkdir(parents=True)
    _write(model / "AGENTS.md", "# Model memory AGENTS\n")
    _write(model / "gpt" / ".gitkeep", "")
    _write(model / "gpt" / "qmd-hybrid-query.md", SUCCESS_RECORD)
    _write(model / "claude" / "ast-grep-outline-missing.md", UNAVAILABLE_RECORD)
    _write(
        root / "ai-tooling" / "memory" / "user" / "example" / "workstation.md",
        "# decoy user memory with capability keyword\n",
    )
    _write(
        root / "docs" / "standards" / "capability.md",
        "# decoy docs page with capability keyword\n",
    )
    _write(root / "docs" / "standards" / "target.md", "# Promotion target\n")
    return tmp


class CategoryHelpersTests(unittest.TestCase):
    def test_canonicalize_success_and_unavailable(self) -> None:
        self.assertEqual(canonicalize_category("success"), "success")
        self.assertEqual(canonicalize_category("Successful capability execution"), "success")
        self.assertEqual(canonicalize_category("unavailable"), "unavailable")
        self.assertEqual(canonicalize_category("unavailable/failed capability/why/recovery"), "unavailable")
        self.assertIsNone(canonicalize_category("session-log"))

    def test_scan_forbidden_secret_path_picker(self) -> None:
        self.assertIn("secret-like token", scan_forbidden("token [REDACTED_OPENAI_KEY]"))
        self.assertIn("personal path", scan_forbidden("see /home/developer/.cursor/argv.json"))
        self.assertIn("host picker identifier", scan_forbidden("picker_id: composer-xyz"))
        self.assertEqual(scan_forbidden("qmd search returns hits"), [])


class ModelMemoryRepoTests(unittest.TestCase):
    def test_search_finds_family_record_not_decoys(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            payload = search_records(root, "gpt", "qmd capability")
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["count"], 1)
            hit = payload["records"][0]
            self.assertEqual(hit["family"], "gpt")
            self.assertEqual(hit["category"], "success")
            self.assertIn("qmd-hybrid-query.md", hit["path"])
            decoy_paths = {h["path"] for h in payload["records"]}
            self.assertFalse(any("memory/user" in p for p in decoy_paths))
            self.assertFalse(any("docs/standards" in p for p in decoy_paths))

    def test_search_unknown_family_raises(self) -> None:
        with _repo() as tmp:
            with self.assertRaises(ValueError):
                search_records(Path(tmp), "bison", "capability")

    def test_validate_passes_two_category_markdown(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            report = validate_tree(root)
            self.assertTrue(report["ok"], report["errors"])
            self.assertGreaterEqual(report["records"], 2)
            self.assertIn("gpt", report["families"])
            self.assertIn("claude", report["families"])

    def test_validate_rejects_unknown_family_and_missing_category(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            _write(root / "ai-tooling" / "memory" / "model" / "bison" / "x.md", "# no category\n")
            _write(
                root / "ai-tooling" / "memory" / "model" / "gpt" / "session-log.md",
                "---\ncategory: chronicle\n---\n# log\n",
            )
            report = validate_tree(root)
            self.assertFalse(report["ok"])
            joined = " ".join(report["errors"])
            self.assertIn("unknown model family", joined)
            self.assertIn("unknown category", joined)

    def test_validate_rejects_secret_and_non_markdown(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            _write(
                root / "ai-tooling" / "memory" / "model" / "cursor" / "leaky.md",
                "---\ncategory: success\n---\n# leak\nsk-proj-abc123def456ghi789jkl0\n",
            )
            _write(root / "ai-tooling" / "memory" / "model" / "gemini" / "notes.txt", "not markdown\n")
            report = validate_tree(root)
            self.assertFalse(report["ok"])
            joined = " ".join(report["errors"])
            self.assertIn("secret-like token", joined)
            self.assertIn("must be markdown", joined)

    def test_validate_absent_tree_is_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_tree(Path(tmp))
            self.assertTrue(report["ok"])
            self.assertEqual(report["records"], 0)
            self.assertTrue(report["warnings"])

    def test_promote_dry_run_does_not_write(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            record = root / "ai-tooling" / "memory" / "model" / "gpt" / "qmd-hybrid-query.md"
            target = root / "docs" / "standards" / "target.md"
            before = target.read_text(encoding="utf-8")
            payload = propose_promote(
                root,
                str(record),
                "docs/standards/target.md",
                dry_run=True,
            )
            self.assertTrue(payload["ok"], payload["errors"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["wrote"])
            self.assertEqual(payload["proposal"]["owning_area"], "docs")
            self.assertEqual(payload["proposal"]["owner_agent"], "documentation-ops")
            self.assertEqual(target.read_text(encoding="utf-8"), before)
            extra = list(root.rglob("*.md"))
            self.assertFalse(payload["wrote"])
            del extra

    def test_promote_rejects_missing_record_and_scratch_target(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            missing = propose_promote(
                root,
                "ai-tooling/memory/model/gpt/missing.md",
                "docs/standards/target.md",
                dry_run=True,
            )
            self.assertFalse(missing["ok"])
            self.assertTrue(any("does not exist" in e for e in missing["errors"]))

            record = "ai-tooling/memory/model/gpt/qmd-hybrid-query.md"
            scratch = propose_promote(
                root,
                record,
                "scratch/promoted.md",
                dry_run=True,
            )
            self.assertFalse(scratch["ok"])
            self.assertTrue(any("not an owning source area" in e for e in scratch["errors"]))

            user_mem = propose_promote(
                root,
                record,
                "ai-tooling/memory/user/example/workstation.md",
                dry_run=True,
            )
            self.assertFalse(user_mem["ok"])
            self.assertTrue(any("user or agent" in e for e in user_mem["errors"]))

    def test_check_record_rejects_user_memory_path(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            user_path = root / "ai-tooling" / "memory" / "user" / "example" / "workstation.md"
            errs = check_record(user_path, root)
            self.assertTrue(any("not under ai-tooling/memory/model" in e for e in errs))


class ModelMemoryCliTests(unittest.TestCase):
    def test_help(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = main(["--help"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("search", out)
        self.assertIn("promote", out)
        self.assertIn("validate", out)

    def test_search_json_cli(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(
                    [
                        "search",
                        "--model",
                        "gpt",
                        "--query",
                        "capability",
                        "--json",
                        "--repo-root",
                        str(root),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["records"][0]["category"], "success")

    def test_search_rejects_bad_family(self) -> None:
        err = io.StringIO()
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = main(["search", "--model", "bison", "--query", "x", "--json"])
        self.assertEqual(rc, 2)

    def test_validate_and_promote_cli(self) -> None:
        with _repo() as tmp:
            root = Path(tmp)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["validate", "--json", "--repo-root", str(root)])
            self.assertEqual(rc, 0)
            report = json.loads(buf.getvalue())
            self.assertTrue(report["ok"])

            buf = io.StringIO()
            target = root / "docs" / "standards" / "target.md"
            before = target.read_text(encoding="utf-8")
            with redirect_stdout(buf):
                rc = main(
                    [
                        "promote",
                        "--record",
                        "ai-tooling/memory/model/gpt/qmd-hybrid-query.md",
                        "--target",
                        "docs/standards/target.md",
                        "--dry-run",
                        "--json",
                        "--repo-root",
                        str(root),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["wrote"])
            self.assertTrue(payload["dry_run"])
            self.assertEqual(target.read_text(encoding="utf-8"), before)

    def test_families_contract(self) -> None:
        self.assertEqual(MODEL_FAMILIES, ("cursor", "gpt", "claude", "gemini"))


if __name__ == "__main__":
    unittest.main()
