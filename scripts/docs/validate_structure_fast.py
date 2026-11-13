"""Fast structural validator for Markdown documents in ai-router.

tags: [docs, validation, lint]
routing_hints: [validate, structure, frontmatter, links, markdown]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import yaml

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from paths import REPO_ROOT as ROOT  # noqa: E402

DEFAULT_EXCLUDES = frozenset({
    "scratch",
    "node_modules",
    ".git",
    "results",
    "change-history",
})

DOC_KINDS_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "requirement": ("canonical_id", "purpose"),
    "security": ("canonical_id", "purpose"),
    "reinforcement": ("canonical_id", "purpose"),
    "process": ("canonical_id", "purpose"),
    "reference": ("canonical_id", "topics"),
    "routing_map": ("canonical_id", "generator"),
    "research": ("canonical_id",),
    "supporting": ("canonical_id",),
}

SKILL_REQUIRED_FIELDS = ("name", "description", "owner_agent", "rank", "isolation")
AGENT_REQUIRED_FIELDS = ("name", "description")

FENCE_PATTERN = re.compile(r"^(?:\x60{3,}|~{3,})")
LINK_PATTERN = re.compile(r"\[(?:[^\]\\]|\\.)*\]\((<[^>]+>|[^)\s]+)(?:[ \t]+[\"'][^\"']*[\"'])?\)")
REF_LINK_PATTERN = re.compile(r"^\s*\[(?:[^\]\\]|\\.)*\]:\s*(<[^>]+>|\S+)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "ftp://", "ftps://", "//", "javascript:", "data:")


def slugify(text: str) -> str:
    """Convert heading text to GitHub-compatible markdown anchor slug."""
    s = text.strip().lower()
    # Strip inline markdown formatting like links, code, bold, italics
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[`*_{}\[\]()]", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def extract_headings_and_h1(
    text: str,
) -> tuple[list[tuple[int, str]], set[str]]:
    """Extract (line_no, h1_text) list for H1s and all heading anchor slugs in document."""
    h1s: list[tuple[int, str]] = []
    slugs: set[str] = set()
    in_fence = False
    fence_char = ""
    fence_len = 0

    lines = text.splitlines()
    start_idx = 0
    # Skip YAML frontmatter if present
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start_idx = i + 1
                break

    for idx, line in enumerate(lines[start_idx:], start_idx + 1):
        stripped = line.strip()
        m_fence = FENCE_PATTERN.match(stripped)
        if m_fence:
            c = m_fence.group(0)[0]
            l = len(m_fence.group(0))
            if not in_fence:
                in_fence = True
                fence_char = c
                fence_len = l
            elif c == fence_char and l >= fence_len:
                in_fence = False
            continue

        if in_fence:
            continue

        m_head = HEADING_PATTERN.match(stripped)
        if m_head:
            level = len(m_head.group(1))
            heading_text = m_head.group(2).strip()
            # Register both cleaned slug and raw slugify
            slugs.add(slugify(heading_text))
            slugs.add(slugify(re.sub(r"[^\w\s-]", "", heading_text)))
            if level == 1:
                h1s.append((idx, heading_text))

    return h1s, slugs


def parse_yaml_frontmatter(text: str) -> tuple[dict[str, Any] | None, str | None, str]:
    """Return (frontmatter_dict, parse_error, body).

    If no frontmatter is present, returns (None, None, text).
    If frontmatter is unclosed or invalid YAML, returns (None, error_msg, text).
    """
    if not text.startswith("---"):
        return None, None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unclosed YAML frontmatter (missing closing ---)", text
    raw = text[3:end]
    body = text[end + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    try:
        data = yaml.safe_load(raw)
        if data is None:
            return {}, None, body
        if not isinstance(data, dict):
            return None, "frontmatter content must be a YAML mapping/dictionary", body
        return data, None, body
    except yaml.YAMLError as exc:
        return None, f"invalid YAML frontmatter: {exc}", body


def validate_file_frontmatter(
    path: Path,
    rel_path: str,
    text: str,
    fm: dict[str, Any] | None,
    fm_error: str | None,
) -> list[str]:
    """Validate YAML frontmatter correctness and required fields per doc_kind."""
    errors: list[str] = []

    if fm_error:
        errors.append(f"{rel_path}: {fm_error}")
        return errors

    # Check docs/ requirements
    parts = Path(rel_path).parts
    if parts and parts[0] == "docs" and path.name not in ("README.md", "AGENTS.md"):
        if fm is None:
            errors.append(f"{rel_path}: missing required YAML frontmatter in docs/")
            return errors
        if "doc_kind" not in fm:
            errors.append(f"{rel_path}: missing 'doc_kind' in frontmatter")
        if "canonical_id" not in fm:
            errors.append(f"{rel_path}: missing 'canonical_id' in frontmatter")

    if fm is None:
        return errors

    doc_kind = fm.get("doc_kind")
    if doc_kind:
        req_fields = DOC_KINDS_REQUIRED_FIELDS.get(str(doc_kind))
        if req_fields:
            for field in req_fields:
                if field not in fm or fm[field] is None or (isinstance(fm[field], str) and not fm[field].strip()):
                    errors.append(f"{rel_path}: doc_kind '{doc_kind}' missing required tag '{field}'")
    else:
        # Check SKILL.md and AGENT.md
        if path.name == "SKILL.md" and "ai-tooling" in parts and "skills" in parts:
            for field in SKILL_REQUIRED_FIELDS:
                if field not in fm or fm[field] is None:
                    errors.append(f"{rel_path}: SKILL.md frontmatter missing required field '{field}'")
        elif path.name == "AGENT.md" and "ai-tooling" in parts and "agents" in parts:
            for field in AGENT_REQUIRED_FIELDS:
                if field not in fm or fm[field] is None:
                    errors.append(f"{rel_path}: AGENT.md frontmatter missing required field '{field}'")

    return errors


def validate_file_h1(rel_path: str, h1s: list[tuple[int, str]]) -> list[str]:
    """Ensure exactly one top-level H1 heading exists outside code blocks."""
    errors: list[str] = []
    if len(h1s) == 0:
        errors.append(f"{rel_path}: missing top-level H1 heading")
    elif len(h1s) > 1:
        lines_str = ", ".join(f"L{line_no} ({title!r})" for line_no, title in h1s)
        errors.append(f"{rel_path}: multiple ({len(h1s)}) H1 headings found: {lines_str}")
    return errors


def extract_links_from_text(text: str) -> list[tuple[int, str]]:
    """Extract (line_number, href) for all markdown links, ignoring code blocks."""
    links: list[tuple[int, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    lines = text.splitlines()
    start_idx = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start_idx = i + 1
                break

    for idx, line in enumerate(lines[start_idx:], start_idx + 1):
        stripped = line.strip()
        m_fence = FENCE_PATTERN.match(stripped)
        if m_fence:
            c = m_fence.group(0)[0]
            l = len(m_fence.group(0))
            if not in_fence:
                in_fence = True
                fence_char = c
                fence_len = l
            elif c == fence_char and l >= fence_len:
                in_fence = False
            continue

        if in_fence:
            continue

        # Extract inline links
        for m in LINK_PATTERN.finditer(line):
            href = m.group(1).strip()
            if href.startswith("<") and href.endswith(">"):
                href = href[1:-1].strip()
            links.append((idx, href))

        # Extract reference links
        for m in REF_LINK_PATTERN.finditer(line):
            href = m.group(1).strip()
            if href.startswith("<") and href.endswith(">"):
                href = href[1:-1].strip()
            links.append((idx, href))

    return links


def validate_relative_links(
    path: Path,
    rel_path: str,
    links: list[tuple[int, str]],
    headings_cache: dict[Path, set[str]],
    repo_root: Path,
) -> list[str]:
    """Validate relative link targets and heading anchors."""
    errors: list[str] = []

    for line_no, href in links:
        if not href or any(href.lower().startswith(scheme) for scheme in EXTERNAL_SCHEMES):
            continue

        # Strip query params
        href_clean = href.split("?")[0]
        path_part, sep, anchor = href_clean.partition("#")
        path_part = path_part.strip()
        anchor = anchor.strip()

        target_file: Path | None = None

        if not path_part:
            # Same-file anchor link
            target_file = path.resolve()
        else:
            unquoted_path = urllib.parse.unquote(path_part)
            if unquoted_path.startswith("/"):
                candidate = (repo_root / unquoted_path.lstrip("/")).resolve()
            else:
                candidate = (path.parent / unquoted_path).resolve()

            if candidate.is_file():
                target_file = candidate
            elif candidate.is_dir():
                target_file = candidate
            else:
                errors.append(
                    f"{rel_path}:L{line_no}: broken relative link '{href}' (target not found: '{unquoted_path}')"
                )
                continue

        # Check anchor if target is a markdown file
        if anchor and target_file and target_file.is_file() and target_file.suffix == ".md":
            if target_file not in headings_cache:
                try:
                    t = target_file.read_text(encoding="utf-8-sig")
                    _, slugs = extract_headings_and_h1(t)
                    headings_cache[target_file] = slugs
                except OSError:
                    headings_cache[target_file] = set()

            known_slugs = headings_cache.get(target_file, set())
            unquoted_anchor = urllib.parse.unquote(anchor).lower()
            clean_anchor = slugify(unquoted_anchor)
            if unquoted_anchor not in known_slugs and clean_anchor not in known_slugs:
                errors.append(
                    f"{rel_path}:L{line_no}: broken anchor in link '{href}' "
                    f"(anchor '#{anchor}' not found in {target_file.name})"
                )

    return errors


def discover_markdown_files(
    target: Path,
    repo_root: Path,
    excludes: frozenset[str] = DEFAULT_EXCLUDES,
) -> list[Path]:
    """Recursively discover markdown files avoiding excluded directories."""
    target = target.resolve()
    if target.is_file():
        return [target] if target.suffix == ".md" else []

    found: list[Path] = []
    for root, dirs, files in os.walk(target):
        # Prune excluded directories in-place for maximum speed
        dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                found.append(Path(root) / f)

    return sorted(found)


def validate_all_structure(
    files: list[Path],
    repo_root: Path,
    check_links: bool = False,
) -> tuple[list[str], list[str]]:
    """Validate all files for frontmatter, single H1, and optionally relative links."""
    errors: list[str] = []
    warnings: list[str] = []

    headings_cache: dict[Path, set[str]] = {}
    file_data: list[tuple[Path, str, str, dict[str, Any] | None, str | None, list[tuple[int, str]], list[tuple[int, str]]]] = []

    # First pass: read files, extract frontmatter, headings, links
    for path in files:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            errors.append(f"{path.as_posix()}: failed to read file: {exc}")
            continue

        try:
            rel_path = path.relative_to(repo_root).as_posix()
        except ValueError:
            rel_path = path.as_posix()

        fm, fm_error, _ = parse_yaml_frontmatter(text)
        h1s, slugs = extract_headings_and_h1(text)
        headings_cache[path.resolve()] = slugs

        links = extract_links_from_text(text) if check_links else []
        file_data.append((path, rel_path, text, fm, fm_error, h1s, links))

    # Second pass: validate rules
    for path, rel_path, text, fm, fm_error, h1s, links in file_data:
        # 1. Frontmatter
        fm_errs = validate_file_frontmatter(path, rel_path, text, fm, fm_error)
        errors.extend(fm_errs)

        # 2. H1
        h1_errs = validate_file_h1(rel_path, h1s)
        errors.extend(h1_errs)

        # 3. Relative links
        if check_links:
            link_errs = validate_relative_links(path, rel_path, links, headings_cache, repo_root)
            errors.extend(link_errs)

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        metavar="PATH",
        help="Path to specific directory or markdown file to validate",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all repository markdown files (skipping scratch/, results/, etc.)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Validate relative markdown links and heading anchors",
    )
    parser.add_argument(
        "--repo-root",
        metavar="DIR",
        help="Override repository root path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Accepted for consistency; validator never mutates files",
    )

    args = parser.parse_args(argv)

    if not args.path and not args.all:
        parser.error("Pass --all or --path <dir/file>")

    repo_root = Path(args.repo_root).resolve() if args.repo_root else ROOT

    if args.path:
        target_path = Path(args.path)
        if not target_path.is_absolute():
            target_path = (repo_root / target_path).resolve()
        else:
            target_path = target_path.resolve()
        if not target_path.exists():
            parser.error(f"Target path does not exist: {target_path}")
    else:
        target_path = repo_root

    t0 = time.perf_counter()
    files = discover_markdown_files(target_path, repo_root=repo_root)
    errors, warnings = validate_all_structure(files, repo_root=repo_root, check_links=args.check_links)
    duration_ms = (time.perf_counter() - t0) * 1000

    payload = {
        "ok": len(errors) == 0,
        "file_count": len(files),
        "duration_ms": round(duration_ms, 2),
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    elif errors:
        print(f"FAIL ({len(errors)} error{'s' if len(errors) != 1 else ''} in {len(files)} files, {duration_ms:.1f}ms):")
        for e in errors:
            print(f"  - {e}")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print(f"OK ({len(files)} files checked in {duration_ms:.1f}ms)")
        for w in warnings:
            print(f"  ! {w}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
