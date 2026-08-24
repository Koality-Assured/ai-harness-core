"""Shared href/src allow-list for generated report HTML and GitHub rewrites.

Not indexed (``scripts/_lib/``). Allow: ``https:``, ``mailto:``, ``#``, and
in-repo-style relatives (``./``, ``../``, bare ``foo/bar``). Reject
``javascript:``, ``data:``, ``vbscript:``, ``file:``, protocol-relative ``//``,
and whitespace. Unsafe values neutralize to ``#`` (never pass through).
"""

from __future__ import annotations

import re

SAFE_ABS_SCHEMES = frozenset({"https", "mailto"})
DANGEROUS_PREFIXES = ("javascript:", "data:", "vbscript:", "file:")


def is_safe_href(href: str) -> bool:
    """Return True if href may appear in generated HTML before/after rewrite."""
    if not href or re.search(r"\s", href):
        return False
    h = href.strip()
    lower = h.lower()
    if lower.startswith(DANGEROUS_PREFIXES):
        return False
    # Protocol-relative
    if h.startswith("//"):
        return False
    if lower.startswith(("http://", "https://")):
        return True
    if lower.startswith("mailto:"):
        return True
    if h.startswith("#"):
        return True
    # Absolute path from site root — not used for local artifact opens; reject
    # to avoid /… and //… confusion. Prefer relative + GitHub rewrite.
    if h.startswith("/"):
        return False
    # Other URI schemes (ftp:, etc.)
    if re.match(r"^[a-z][a-z0-9+.-]*:", lower):
        return False
    # Relative: ./ ../ or bare path
    return True


def neutralize_href(href: str) -> str:
    """Return href if safe, else ``#`` (never pass dangerous schemes through)."""
    if is_safe_href(href):
        return href.strip()
    return "#"
