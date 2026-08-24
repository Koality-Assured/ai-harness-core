"""Stdlib unit tests for href allow-list and GitHub path helpers.

tags: [tests, security, github]
routing_hints: [tests, href, github-paths]

Run: python -m unittest scripts.tests.test_pretty_docs_security -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))

from github_paths import (  # noqa: E402
    GithubPathError,
    github_https_url,
    parse_github_origin,
    rewrite_repo_hrefs,
    validate_ref,
)
from md_to_html import format_inline  # noqa: E402
from safe_href import is_safe_href, neutralize_href  # noqa: E402


class SafeHrefTests(unittest.TestCase):
    def test_allow_https_mailto_hash_relative(self) -> None:
        self.assertTrue(is_safe_href("https://example.com/x"))
        self.assertTrue(is_safe_href("mailto:a@b.c"))
        self.assertTrue(is_safe_href("#main"))
        self.assertTrue(is_safe_href("./a.html"))
        self.assertTrue(is_safe_href("../b/c.md"))
        self.assertTrue(is_safe_href("foo/bar.html"))

    def test_reject_dangerous(self) -> None:
        for bad in (
            "javascript:alert(1)",
            "data:text/html,x",
            "vbscript:msg",
            "file:///etc/passwd",
            "//evil.example/x",
            "/abs/root",
            "ftp://x",
            "has space.html",
        ):
            self.assertFalse(is_safe_href(bad), bad)
            self.assertEqual(neutralize_href(bad), "#")

    def test_format_inline_drops_js(self) -> None:
        out = format_inline("[x](javascript:alert(1))")
        self.assertNotIn("javascript:", out)
        self.assertNotIn("<a ", out)


class GithubPathsTests(unittest.TestCase):
    def test_parse_origin(self) -> None:
        self.assertEqual(
            parse_github_origin("https://github.com/Koality-Assured/ai-router.git"),
            ("Koality-Assured", "ai-router"),
        )
        self.assertEqual(
            parse_github_origin("git@github.com:Koality-Assured/ai-router.git"),
            ("Koality-Assured", "ai-router"),
        )
        with self.assertRaises(GithubPathError):
            parse_github_origin("https://gitlab.com/x/y")

    def test_validate_ref(self) -> None:
        self.assertEqual(validate_ref("main"), "main")
        with self.assertRaises(GithubPathError):
            validate_ref('main"')
        with self.assertRaises(GithubPathError):
            validate_ref("feat branch")
        with self.assertRaises(GithubPathError):
            validate_ref("other")
        self.assertEqual(validate_ref("other", allow_non_main=True), "other")

    def test_outside_root(self) -> None:
        root = Path(__file__).resolve().parents[2]
        with self.assertRaises(GithubPathError):
            github_https_url(r"C:\Windows\System32", root=root, owner_repo=("o", "r"))
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "x.md"
            outside.write_text("x", encoding="utf-8")
            with self.assertRaises(GithubPathError):
                github_https_url(outside, root=root, owner_repo=("o", "r"))

    def test_rewrite_neutralizes_and_skips_code(self) -> None:
        root = Path(__file__).resolve().parents[2]
        from_file = root / "results" / "reports" / "executive" / "t" / "2026-08-21" / "index.html"
        html = (
            '<a href="javascript:alert(1)">bad</a>'
            '<a href="//evil.example/x">proto</a>'
            '<pre><a href="../escape.md">in pre</a></pre>'
            '<a href="https://cdn.example/x.css">cdn</a>'
            '<code>[link](../x.md)</code>'
        )
        out = rewrite_repo_hrefs(
            html,
            root=root,
            from_file=from_file,
            owner_repo=("Koality-Assured", "ai-router"),
        )
        self.assertIn('href="#"', out)
        self.assertIn("cdn.example", out)
        self.assertIn("<pre><a href=\"../escape.md\">in pre</a></pre>", out)
        self.assertIn("<code>[link](../x.md)</code>", out)

    def test_rewrite_outside_becomes_hash(self) -> None:
        root = Path(__file__).resolve().parents[2]
        from_file = root / "AGENTS.md"
        # Many ../ to leave the repo
        html = '<a href="../../../../../../../../etc/passwd">x</a>'
        out = rewrite_repo_hrefs(
            html,
            root=root,
            from_file=from_file,
            owner_repo=("Koality-Assured", "ai-router"),
        )
        self.assertIn('href="#"', out)
        self.assertNotIn("etc/passwd", out)

    def test_md_fence_untouched(self) -> None:
        root = Path(__file__).resolve().parents[2]
        from_file = root / "AGENTS.md"
        md = "See [ok](./README.md)\n\n```\n[sample](../outside.md)\n```\n"
        out = rewrite_repo_hrefs(
            md,
            root=root,
            from_file=from_file,
            owner_repo=("Koality-Assured", "ai-router"),
        )
        self.assertIn("blob/main/README.md", out)
        self.assertIn("[sample](../outside.md)", out)


if __name__ == "__main__":
    unittest.main()
