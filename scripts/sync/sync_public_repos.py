"""Multi-repo synchronization and sanitization/redaction engine for public exports.

tags: [sync, security, export]
routing_hints: [sync, redaction, multi-repo, export, sanitize, wiki-template]
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import datetime as dt
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys
from typing import Any, Callable

_SYNC = Path(__file__).resolve().parent
_LIB = Path(__file__).resolve().parents[1] / "_lib"
for _p in (_SYNC, _LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from paths import REPO_ROOT as DEFAULT_ROOT, resolve_repo_root
except ImportError:
    DEFAULT_ROOT = Path(__file__).resolve().parents[2]
    def resolve_repo_root(override: str | Path | None = None) -> Path:
        return Path(override).resolve() if override else DEFAULT_ROOT

from _harness_template import (  # noqa: E402
    HARNESS_TEMPLATE_MODE,
    WIKI_TEMPLATE_ALLOWED_DOT_DIRS,
    harness_template_dir_may_contain_kept,
    harness_template_post_copy_files,
    harness_template_prune_dest_leftovers,
    harness_template_sanitize_file_content,
    is_harness_template_rel_kept,
)



# Per-repo export filters for docs/standards. Agentic specs go only to agent-standards; general security
# requirements go only to security-standards. Name-based sets are explicit so the split is reviewable.
AGENT_STANDARDS_DOCS = frozenset({"context-management.md", "ai-development-security.md"})
NON_SECURITY_STANDARDS_DOCS = frozenset(
    {"README.md", "repository-beautification.md", "harness-template.md", "wiki-harness-template.md"}
)
# Product- or domain-integration standards are not general security requirements.
NON_SECURITY_STANDARDS_PREFIXES = ("confluence-", "slack-", "google-suite-", "us-law-")
_DOC_KIND_RE = re.compile(r"^doc_kind:\s*([A-Za-z0-9_-]+)\s*$", re.MULTILINE)
_MD_LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]*)([^)]*)\)")
_URL_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
COMPANION_TOOLING_NOTE = "> **Note:** This skill requires companion tooling not included in this catalog."


def _standards_doc_kind(p: Path) -> str | None:
    """Return the frontmatter ``doc_kind`` of a Markdown file, or None if absent/unreadable."""
    try:
        head = p.read_text(encoding="utf-8")[:2048]
    except (OSError, UnicodeDecodeError):
        return None
    if not head.startswith("---"):
        return None
    match = _DOC_KIND_RE.search(head)
    return match.group(1) if match else None


def _agent_standards_filter(p: Path) -> bool:
    return p.name in AGENT_STANDARDS_DOCS


def _security_standards_filter(p: Path) -> bool:
    name = p.name
    if name in AGENT_STANDARDS_DOCS or name in NON_SECURITY_STANDARDS_DOCS:
        return False
    if name.startswith(NON_SECURITY_STANDARDS_PREFIXES):
        return False
    return _standards_doc_kind(p) == "requirement"


DEFAULT_REPO_MAPPINGS: dict[str, Any] = {
    "agent-skills-and-tools": {
        "source_subpath": "ai-tooling/skills",
        "dest_subpath": "skills",
        "description": "Skills and tools export",
    },
    "agent-standards": {
        "source_subpath": "docs/standards",
        "dest_subpath": "standards",
        "description": "Agent standards and security policies export",
        "filter_func": _agent_standards_filter,
    },
    "security-standards": {
        "source_subpath": "docs/standards",
        "dest_subpath": "standards",
        "description": "General engineering and organizational security standards export",
        "filter_func": _security_standards_filter,
    },
    "industry-references": {
        "source_subpath": "references",
        "dest_subpath": "references",
        "description": "Industry standard references and machine-readable catalogs export",
    },
    "ai-research-and-benchmarks": {
        "subpaths": [
            {
                "source_subpath": "research",
                "dest_subpath": "research",
            },
            {
                "source_subpath": "supporting/benchmarks",
                "dest_subpath": "benchmarks/supporting",
                "optional": True,
            },
            {
                "source_subpath": "scripts/benchmarks",
                "dest_subpath": "harnesses/benchmarks",
                "optional": True,
            },
            {
                "source_subpath": "results/benchmarks",
                "dest_subpath": "reports",
                "optional": True,
            },
        ],
        "source_subpath": "research",
        "dest_subpath": "research",
        "description": "AI research and benchmarks export",
    },
    "ai-harness-core": {
        "source_subpath": ".",
        "dest_subpath": ".",
        "description": "Generic harness template export",
        "mode": HARNESS_TEMPLATE_MODE,
    },
}

EXCLUDED_NAMES: set[str] = {
    ".git",
    ".github",
    ".pytest_cache",
    "__pycache__",
    ".DS_Store",
    "Thumbs.db",
    ".coverage",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}

EXCLUDED_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".swp",
    ".swo",
    "~",
}


@dataclasses.dataclass
class RedactionRule:
    name: str
    description: str
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]


@dataclasses.dataclass
class RedactionAuditEntry:
    file: str
    line: int
    rule: str
    match_fingerprint: str
    match_length: int
    replacement: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "rule": self.rule,
            "match_fingerprint": self.match_fingerprint,
            "match_length": self.match_length,
            "replacement": self.replacement,
        }


def _mask_secret(val: str, prefix_len: int = 4, suffix_len: int = 4) -> str:
    """Mask a secret string preserving only a short prefix and suffix."""
    if len(val) <= prefix_len + suffix_len:
        return "*" * len(val)
    return val[:prefix_len] + "*" * (len(val) - prefix_len - suffix_len) + val[-suffix_len:]


def build_default_rules(custom_usernames: list[str] | None = None) -> list[RedactionRule]:
    """Construct the standard suite of sanitization and redaction rules."""
    rules: list[RedactionRule] = [
        # 1. API Keys & Credentials
        RedactionRule(
            name="openai_api_key",
            description="OpenAI API secret keys",
            # Skip sk-EXAMPLE_* fixtures so dest A2A secret-leak tests stay valid Python.
            pattern=re.compile(r"\bsk-(?!ant-)(?!EXAMPLE)(?:proj-|live-)?[a-zA-Z0-9_-]{20,}\b"),
            replacement="[REDACTED_OPENAI_KEY]",
        ),
        RedactionRule(
            name="anthropic_api_key",
            description="Anthropic API secret keys",
            # Skip sk-ant-EXAMPLE- fixtures so exported auth tests keep valid vectors.
            pattern=re.compile(r"\bsk-ant-(?!EXAMPLE-)[a-zA-Z0-9_-]{20,}\b"),
            replacement="[REDACTED_ANTHROPIC_KEY]",
        ),
        RedactionRule(
            name="github_token",
            description="GitHub Personal Access and OAuth Tokens",
            pattern=re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[a-zA-Z0-9_]{20,}\b"),
            replacement="[REDACTED_GITHUB_TOKEN]",
        ),
        RedactionRule(
            name="aws_access_key_id",
            description="AWS Access Key ID identifiers",
            pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            replacement="[REDACTED_AWS_KEY]",
        ),
        RedactionRule(
            name="aws_secret_key",
            description="AWS Secret Access Key assignments",
            pattern=re.compile(r"(?i)\b(aws_secret_access_key|aws_secret_key)\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?"),
            replacement=lambda m: f'{m.group(1)} = "[REDACTED_AWS_SECRET]"',
        ),
        RedactionRule(
            name="slack_token",
            description="Slack Bot and User tokens",
            pattern=re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]{10,}\b"),
            replacement="[REDACTED_SLACK_TOKEN]",
        ),
        RedactionRule(
            name="jwt_token",
            description="JSON Web Tokens (JWT)",
            pattern=re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
            replacement="[REDACTED_JWT_TOKEN]",
        ),
        RedactionRule(
            name="bearer_token",
            description="HTTP Bearer authentication tokens",
            pattern=re.compile(r"(?i)\bBearer\s+([A-Za-z0-9_\-\.]{25,})\b"),
            replacement="Bearer [REDACTED_BEARER_TOKEN]",
        ),
        RedactionRule(
            name="private_key_block",
            description="PEM / OpenSSH Private Key certificates and blocks",
            pattern=re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
            replacement="[REDACTED_PRIVATE_KEY_BLOCK]",
        ),
        RedactionRule(
            name="git_credential_url",
            description="Git remote URLs containing embedded basic auth credentials",
            pattern=re.compile(r"https?://(?:[^:\s@]+):(?:[^@\s]+)@([a-zA-Z0-9.-]+)"),
            replacement=lambda m: f"https://{m.group(1)}",
        ),

        # 2. Proprietary & Local File Paths
        RedactionRule(
            name="windows_user_home_path",
            description="Windows local user directory paths",
            pattern=re.compile(r"(?i)[a-zA-Z]:\\Users\\(?!developer\b)[a-zA-Z0-9_\-\.]+"),
            replacement="C:\\Users\\developer",
        ),
        RedactionRule(
            name="unix_user_home_path",
            description="Unix / macOS local user home directory paths",
            pattern=re.compile(r"/(?:Users|home)/(?!developer\b)[a-zA-Z0-9_\-\.]+"),
            replacement="/home/developer",
        ),
        RedactionRule(
            name="scratch_worktree_path",
            description="Internal scratch and agent worktree paths",
            # Lookbehinds sit immediately before scratch so parent-relative
            # ../scratch/worktrees/ docs are not swallowed by a leading slash.
            pattern=re.compile(
                r"(?:(?:[a-zA-Z]:)?(?:[/\\](?:(?!\.\.)[a-zA-Z0-9_\-\.]+))+[/\\])?"
                r"(?<!\.\./)(?<!\.\.\\)"
                r"scratch[/\\]worktrees[/\\](?!<)[a-zA-Z0-9_\-\./\\]+"
            ),
            replacement="[REDACTED_WORKTREE_PATH]",
        ),
        RedactionRule(
            name="gemini_appdata_path",
            description="Antigravity and Gemini app data paths",
            pattern=re.compile(r"(?i)(?:[a-zA-Z]:[/\\]Users[/\\][^/\\]+[/\\]|\~[/\\])?\.gemini[/\\]antigravity[a-zA-Z0-9_\-\\\/\.]*"),
            replacement="[REDACTED_APPDATA_PATH]",
        ),
        RedactionRule(
            name="internal_repo_root_abs_path",
            description="Absolute internal repo root directory paths",
            # Workspace roots may include one or more grouping directories between
            # a known source root (for example, Code) and the repository directory.
            # UNC roots also include a server/share prefix, with an optional extended-path marker.
            pattern=re.compile(
                r"(?i)(?:"
                r"(?:\\\\\?\\)?[a-zA-Z]:[\\/](?:Code|Projects|repos|dev)[\\/]"
                r"(?:[^\\/\r\n]+[\\/])*?ai-router(?:[\\/]|(?=$|[^\w-]))"
                r"|(?:\\\\\?\\UNC\\|\\\\)[^\\/\r\n]+\\[^\\/\r\n]+\\"
                r"(?:[^\\/\r\n]+\\)*?ai-router(?:\\|(?=$|[^\w-]))"
                r")"
            ),
            replacement="[REPO_ROOT]/",
        ),
        RedactionRule(
            name="google_drive_test_folder",
            description="Google Drive test folder ID and URL",
            pattern=re.compile(
                r"https?://drive\.google\.com/drive/(?:u/\d+/)?folders/[A-Za-z0-9_-]{10,}"
                r"|(?i:\bfolder[ _-]?id\b)\s*[:=]?\s*[\"'`]?[A-Za-z0-9_-]{25,}[\"'`]?"
            ),
            replacement="[REDACTED_GOOGLE_DRIVE_TEST_FOLDER]",
        ),

        # 3. Internal Identities & Domains
        RedactionRule(
            name="internal_git_identity",
            description="Git author or committer configuration lines with internal emails",
            pattern=re.compile(r"(?i)\b(author|committer|user\.email)\s*[:=]\s*['\"]?[a-zA-Z0-9_.+-]+@(?:internal\.corp|corp\.internal|local\.lan)['\"]?"),
            replacement=lambda m: f'{m.group(1)} = "developer@example.com"',
        ),
        RedactionRule(
            name="internal_email_domain",
            description="Internal corporate email addresses",
            pattern=re.compile(r"\b[a-zA-Z0-9_.+-]+@(?:internal\.corp|corp\.internal|local\.lan|corp\.example\.com|internal\.example\.com)\b"),
            replacement="[REDACTED_INTERNAL_EMAIL]",
        ),
    ]

    usernames = ["rob" + "er", "rob" + "ert"]
    if custom_usernames:
        usernames.extend(custom_usernames)

    for uname in set(usernames):
        if not uname:
            continue
        uname_esc = re.escape(uname)
        rules.append(
            RedactionRule(
                name=f"internal_username_{uname.lower()}",
                description=f"Internal username mention: {uname}",
                pattern=re.compile(rf"(?i)\b{uname_esc}\b"),
                replacement="developer",
            )
        )

    return rules


class RedactionEngine:
    """Engine responsible for inspecting text and performing rule-based redactions."""

    def __init__(self, rules: list[RedactionRule] | None = None, usernames: list[str] | None = None) -> None:
        self.rules: list[RedactionRule] = rules if rules is not None else build_default_rules(usernames)

    def redact_text(self, text: str, file_rel_path: str = "") -> tuple[str, list[RedactionAuditEntry]]:
        """Redact sensitive patterns from text and record audit logs."""
        audit_entries: list[RedactionAuditEntry] = []
        current_text = text

        for rule in self.rules:
            # Check for matches
            matches = list(rule.pattern.finditer(current_text))
            if not matches:
                continue

            # Process matches in reverse order to preserve string indices during replacement
            for match in reversed(matches):
                matched_str = match.group(0)
                start_pos = match.start()

                # Calculate 1-indexed line number in original text
                line_num = current_text.count("\n", 0, start_pos) + 1

                # Determine replacement string
                if callable(rule.replacement):
                    repl_str = rule.replacement(match)
                else:
                    repl_str = rule.replacement

                # Record audit log
                digest = hashlib.sha256(matched_str.encode("utf-8")).hexdigest()[:12]
                audit_entries.append(
                    RedactionAuditEntry(
                        file=file_rel_path,
                        line=line_num,
                        rule=rule.name,
                        match_fingerprint=f"sha256:{digest}",
                        match_length=len(matched_str),
                        replacement=repl_str if len(repl_str) <= 60 else repl_str[:50] + "...",
                    )
                )

            # Apply replacement across entire text avoiding template escape parsing issues
            if callable(rule.replacement):
                current_text = rule.pattern.sub(rule.replacement, current_text)
            else:
                repl = rule.replacement
                current_text = rule.pattern.sub(lambda _m, r=repl: r, current_text)

        # Sort audit entries by line number
        audit_entries.sort(key=lambda e: e.line)
        return current_text, audit_entries

    def find_violations(self, text: str, file_rel_path: str = "") -> list[str]:
        """Scan text and return violation error strings if sensitive patterns are present."""
        violations: list[str] = []
        for rule in self.rules:
            for match in rule.pattern.finditer(text):
                start_pos = match.start()
                line_num = text.count("\n", 0, start_pos) + 1
                matched_str = match.group(0)
                digest = hashlib.sha256(matched_str.encode("utf-8")).hexdigest()[:12]
                violations.append(
                    f"{file_rel_path}:{line_num} - Found sensitive pattern '{rule.name}' "
                    f"({rule.description}; length={len(matched_str)}; sha256:{digest})"
                )
        return violations


@dataclasses.dataclass
class RepoSyncResult:
    repo_name: str
    status: str  # "success", "failed", "skipped"
    source_dir: str
    dest_dir: str
    files_scanned: int = 0
    files_synced: int = 0
    files_modified: int = 0
    files_unchanged: int = 0
    redactions_count: int = 0
    audit_log: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    errors: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_name": self.repo_name,
            "status": self.status,
            "source_dir": self.source_dir,
            "dest_dir": self.dest_dir,
            "files_scanned": self.files_scanned,
            "files_synced": self.files_synced,
            "files_modified": self.files_modified,
            "files_unchanged": self.files_unchanged,
            "redactions_count": self.redactions_count,
            "audit_log": self.audit_log,
            "errors": self.errors,
        }


@dataclasses.dataclass
class SyncReport:
    timestamp_utc: str
    source_root: str
    dest_root: str
    dry_run: bool
    repos: dict[str, RepoSyncResult] = dataclasses.field(default_factory=dict)
    summary: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "source_root": self.source_root,
            "dest_root": self.dest_root,
            "dry_run": self.dry_run,
            "repos": {k: v.to_dict() for k, v in self.repos.items()},
            "summary": self.summary,
        }


class SyncEngine:
    """Multi-repository synchronization coordinator."""

    def __init__(
        self,
        source_root: Path,
        dest_root: Path,
        mappings: dict[str, dict[str, str]] | None = None,
        redactor: RedactionEngine | None = None,
        dry_run: bool = False,
    ) -> None:
        self.source_root = source_root.resolve()
        self.dest_root = dest_root.resolve()
        self.mappings = mappings if mappings is not None else DEFAULT_REPO_MAPPINGS
        self.redactor = redactor or RedactionEngine()
        self.dry_run = dry_run

    def _resolve_dest_path(self, repo_name: str, dest_subpath: str) -> Path:
        """Resolve the appropriate destination directory for a repository export.

        If dest_root base name matches repo_name, use dest_root / dest_subpath.
        Otherwise use dest_root / repo_name / dest_subpath.
        """
        if self.dest_root.name == repo_name or self.dest_root.name.startswith(f"{repo_name}-"):
            return self.dest_root / dest_subpath
        return self.dest_root / repo_name / dest_subpath

    def _walk_source_files(self, src_dir: Path, mapping: dict[str, Any]) -> list[Path]:
        """Collect source files for a mapping, applying wiki-template filters when set."""
        mode = mapping.get("mode", "subtree")
        collected: list[Path] = []
        dest_resolved = self.dest_root.resolve()

        for root, dirs, files in os.walk(src_dir):
            root_path = Path(root)
            try:
                src_resolved = src_dir.resolve()
                if dest_resolved == src_resolved or src_resolved in dest_resolved.parents:
                    if root_path.resolve() == dest_resolved or dest_resolved in root_path.resolve().parents:
                        dirs[:] = []
                        continue
            except OSError:
                pass

            rel_root = root_path.relative_to(src_dir).as_posix()
            if rel_root == ".":
                rel_root = ""

            pruned: list[str] = []
            for d in dirs:
                if mode == HARNESS_TEMPLATE_MODE and d in WIKI_TEMPLATE_ALLOWED_DOT_DIRS:
                    pass
                else:
                    if d in EXCLUDED_NAMES:
                        continue
                    if d.startswith("."):
                        continue
                if mode == HARNESS_TEMPLATE_MODE:
                    child_rel = f"{rel_root}/{d}" if rel_root else d
                    if not harness_template_dir_may_contain_kept(child_rel):
                        continue
                pruned.append(d)
            dirs[:] = pruned

            for f in files:
                if f in EXCLUDED_NAMES or any(f.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
                    continue
                src_file = root_path / f
                if mode == HARNESS_TEMPLATE_MODE:
                    rel = src_file.relative_to(src_dir).as_posix()
                    if not is_harness_template_rel_kept(rel):
                        continue
                filter_func = mapping.get("filter_func")
                if filter_func and not filter_func(src_file):
                    continue
                collected.append(src_file)
        return collected

    def _sync_text_payload(
        self,
        dest_file: Path,
        raw_text: str,
        display_rel: str,
        result: RepoSyncResult,
    ) -> None:

        if display_rel.lower().endswith(".md"):
            raw_text = self._reroot_markdown_links(raw_text, display_rel, result.repo_name)
            if (
                result.repo_name == "agent-skills-and-tools"
                and display_rel.endswith("SKILL.md")
                and "scripts/" in raw_text
                and COMPANION_TOOLING_NOTE not in raw_text
            ):
                raw_text = raw_text.rstrip("\n") + "\n\n" + COMPANION_TOOLING_NOTE + "\n"

        sanitized_text, audit_entries = self.redactor.redact_text(raw_text, display_rel)
        if audit_entries:
            result.redactions_count += len(audit_entries)
            for entry in audit_entries:
                result.audit_log.append(entry.to_dict())

        content_changed = True
        if dest_file.exists():
            try:
                existing_text = dest_file.read_text(encoding="utf-8")
                if existing_text == sanitized_text:
                    content_changed = False
            except Exception:
                content_changed = True

        if content_changed:
            result.files_modified += 1
            result.files_synced += 1
            if not self.dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(sanitized_text, encoding="utf-8")
        else:
            result.files_unchanged += 1
            result.files_synced += 1

    def _sync_one_file(
        self,
        src_file: Path,
        dest_file: Path,
        result: RepoSyncResult,
        mode: str | None = None,
    ) -> None:
        result.files_scanned += 1
        is_binary = False
        try:
            raw_text = src_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            is_binary = True

        if is_binary:
            content_changed = True
            if dest_file.exists():
                if src_file.read_bytes() == dest_file.read_bytes():
                    content_changed = False
            if content_changed:
                result.files_modified += 1
                result.files_synced += 1
                if not self.dry_run:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
            else:
                result.files_unchanged += 1
                result.files_synced += 1
            return

        display_rel = src_file.relative_to(self.source_root).as_posix()
        if mode == HARNESS_TEMPLATE_MODE:
            raw_text = harness_template_sanitize_file_content(display_rel, raw_text)
        self._sync_text_payload(dest_file, raw_text, display_rel, result)

    def sync_repo(self, repo_name: str) -> RepoSyncResult:
        """Synchronize a single repository export mapping."""
        if repo_name not in self.mappings:
            return RepoSyncResult(
                repo_name=repo_name,
                status="failed",
                source_dir="",
                dest_dir="",
                errors=[f"Unknown repository mapping: '{repo_name}'"],
            )

        mapping = self.mappings[repo_name]
        subpaths = mapping.get("subpaths")
        if not subpaths:
            subpaths = [{
                "source_subpath": mapping.get("source_subpath", ""),
                "dest_subpath": mapping.get("dest_subpath", ""),
            }]

        primary_src = self.source_root / subpaths[0]["source_subpath"]
        primary_dst = self._resolve_dest_path(repo_name, subpaths[0]["dest_subpath"])

        result = RepoSyncResult(
            repo_name=repo_name,
            status="success",
            source_dir=str(primary_src),
            dest_dir=str(primary_dst),
        )

        mode = mapping.get("mode")
        for sub in subpaths:
            src_sub = sub["source_subpath"]
            dst_sub = sub["dest_subpath"]
            src_dir = self.source_root / src_sub
            dst_dir = self._resolve_dest_path(repo_name, dst_sub)

            if not src_dir.exists():
                if not sub.get("optional"):
                    result.status = "failed"
                    result.errors.append(f"Source directory does not exist: {src_dir}")
                continue

            for src_file in sorted(self._walk_source_files(src_dir, mapping)):
                rel_to_src = src_file.relative_to(src_dir)
                dest_file = dst_dir / rel_to_src
                self._sync_one_file(src_file, dest_file, result, mode=mode)

        if mapping.get("mode") == HARNESS_TEMPLATE_MODE:
            if not self.dry_run:
                harness_template_prune_dest_leftovers(primary_dst)
            for rel, content in harness_template_post_copy_files(primary_dst, source_root=primary_src).items():
                dest_file = primary_dst / rel
                result.files_scanned += 1
                self._sync_text_payload(dest_file, content, rel, result)

        self._run_post_export_checks(primary_dst, result)
        if repo_name == "security-standards":
            self._update_security_standards_readme(self._resolve_dest_path(repo_name, ""), primary_dst)
        return result

    def _update_security_standards_readme(self, repo_root: Path, standards_dir: Path) -> None:
        """Refresh the standards count and catalog table in the mirror README from the exported files."""
        if self.dry_run or not repo_root.exists():
            return
        readme_path = repo_root / "README.md"
        if not readme_path.exists():
            return

        standards = sorted(f for f in standards_dir.glob("*.md") if f.name != "README.md")
        table = "| Standard Document | Purpose & Architectural Intent |\n| :--- | :--- |\n"
        for f in standards:
            text = f.read_text(encoding="utf-8")
            purpose_m = re.search(r"^purpose:\s*\[([^\]]+)\]", text, re.MULTILINE)
            purpose = purpose_m.group(1) if purpose_m else "Security Standard"
            rel = f.relative_to(repo_root).as_posix()
            table += f"| [{f.name}]({rel}) | {purpose.capitalize()}. |\n"

        count = len(standards)
        readme_text = readme_path.read_text(encoding="utf-8")
        readme_text = re.sub(r"\d+\s+normative standards", f"{count} normative standards", readme_text, flags=re.IGNORECASE)
        readme_text = re.sub(r"standards-\d+%20Normative", f"standards-{count}%20Normative", readme_text)

        # Replace the catalog section up to the next known section; leave the README untouched if either
        # marker is missing so a restructured README is never corrupted.
        section_start = "## Normative Standards Catalog"
        section_end = "## Validation & Testing"
        start_idx = readme_text.find(section_start)
        end_idx = readme_text.find(section_end)
        if start_idx != -1 and end_idx > start_idx:
            new_section = (
                f"{section_start}\n\nThe complete catalog comprises {count} normative standards.\n\n{table}\n---\n\n"
            )
            readme_text = readme_text[:start_idx] + new_section + readme_text[end_idx:]

        readme_path.write_text(readme_text, encoding="utf-8")

    def _export_dest_rel(self, repo_name: str, source_rel: str) -> str | None:
        """Map a source-root-relative path to its repo-root-relative exported path, or None if not exported."""
        mapping = self.mappings.get(repo_name)
        if not mapping or mapping.get("mode") == HARNESS_TEMPLATE_MODE:
            return None
        subpaths = mapping.get("subpaths") or [mapping]
        source_path = self.source_root / source_rel
        if not source_path.exists():
            return None
        best: tuple[int, str] | None = None
        for sub in subpaths:
            s_path = str(sub.get("source_subpath", "")).strip("/")
            d_path = str(sub.get("dest_subpath", "")).strip("/")
            if s_path in ("", "."):
                tail = source_rel
            elif source_rel == s_path:
                tail = ""
            elif source_rel.startswith(s_path + "/"):
                tail = source_rel[len(s_path) + 1:]
            else:
                continue
            dest = posixpath.normpath(posixpath.join(d_path or ".", tail)) if tail else (d_path or ".")
            if best is None or len(s_path) > best[0]:
                best = (len(s_path), dest)
        if best is None:
            return None
        if source_path.is_file():
            filter_func = mapping.get("filter_func")
            if filter_func and not filter_func(source_path):
                return None
            if source_path.name in EXCLUDED_NAMES or any(source_path.name.endswith(e) for e in EXCLUDED_EXTENSIONS):
                return None
        return best[1]

    def _reroot_markdown_links(self, text: str, display_rel: str, repo_name: str) -> str:
        """Re-root relative Markdown links for the exported layout.

        Links to exported files are rewritten relative to the exported location. Links to anything not
        exported degrade to their plain text (never to a URL, since the source repository is private).
        Fenced code blocks, absolute URLs, anchors, and mailto/other schemes are left untouched.
        """
        current_dest = self._export_dest_rel(repo_name, display_rel)
        if current_dest is None:
            return text
        current_dest_dir = posixpath.dirname(current_dest) or "."
        source_dir = posixpath.dirname(display_rel)

        def replace(m: re.Match[str]) -> str:
            bang, label, target, rest = m.group(1), m.group(2), m.group(3), m.group(4)
            if not target or target.startswith(("#", "//", "/", "<")) or _URL_SCHEME_RE.match(target):
                return m.group(0)
            path_part, hash_sep, fragment = target.partition("#")
            path_part = path_part.partition("?")[0]
            if not path_part:
                return m.group(0)
            resolved = posixpath.normpath(posixpath.join(source_dir, path_part))
            if resolved == ".." or resolved.startswith("../"):
                return label
            dest_target = self._export_dest_rel(repo_name, resolved)
            if dest_target is None:
                return label  # plain text for unexported targets
            new_target = posixpath.relpath(dest_target, current_dest_dir)
            if path_part.endswith("/") and not new_target.endswith("/"):
                new_target += "/"
            return f"{bang}[{label}]({new_target}{hash_sep}{fragment}{rest})"

        out: list[str] = []
        in_fence = False
        fence_marker = ""
        for line in text.splitlines(keepends=True):
            stripped = line.lstrip()
            if stripped.startswith(("```", "~~~")):
                marker = stripped[:3]
                if not in_fence:
                    in_fence, fence_marker = True, marker
                elif marker == fence_marker:
                    in_fence = False
                out.append(line)
                continue
            out.append(line if in_fence else _MD_LINK_RE.sub(replace, line))
        return "".join(out)

    def _run_post_export_checks(self, dst_dir: Path, result: RepoSyncResult) -> None:
        """Fail the repo export when an exported Markdown file contains a dead relative link."""
        if not dst_dir.exists() or self.dry_run:
            return
        if result.repo_name == "ai-harness-core":
            return

        for f in sorted(dst_dir.rglob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            in_fence = False
            for line in text.splitlines():
                if line.lstrip().startswith(("```", "~~~")):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                for match in _MD_LINK_RE.finditer(line):
                    target = match.group(3)
                    if not target or target.startswith(("#", "<")) or _URL_SCHEME_RE.match(target):
                        continue
                    path_part = target.partition("#")[0].partition("?")[0]
                    if not path_part:
                        continue
                    if not (f.parent / path_part).exists():
                        result.errors.append(f"Dead link in {f.relative_to(dst_dir).as_posix()}: {target}")
                        result.status = "failed"

    def sync_all(self, repo_filter: str | None = None) -> SyncReport:
        """Run synchronization across selected or all repositories."""
        now_utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        report = SyncReport(
            timestamp_utc=now_utc,
            source_root=str(self.source_root),
            dest_root=str(self.dest_root),
            dry_run=self.dry_run,
        )

        target_repos = [repo_filter] if repo_filter else list(self.mappings.keys())
        total_scanned = 0
        total_synced = 0
        total_modified = 0
        total_unchanged = 0
        total_redactions = 0
        total_errors = 0
        all_ok = True

        for repo in target_repos:
            repo_res = self.sync_repo(repo)
            report.repos[repo] = repo_res
            total_scanned += repo_res.files_scanned
            total_synced += repo_res.files_synced
            total_modified += repo_res.files_modified
            total_unchanged += repo_res.files_unchanged
            total_redactions += repo_res.redactions_count
            total_errors += len(repo_res.errors)
            if repo_res.status != "success":
                all_ok = False

        report.summary = {
            "total_repos": len(target_repos),
            "total_files_scanned": total_scanned,
            "total_files_synced": total_synced,
            "total_files_modified": total_modified,
            "total_files_unchanged": total_unchanged,
            "total_redactions": total_redactions,
            "total_errors": total_errors,
            "success": all_ok and total_errors == 0,
        }

        return report

    def validate_sources(self, repo_filter: str | None = None) -> tuple[bool, list[str]]:
        """Validate that source directories are healthy and report any unredacted items."""
        violations: list[str] = []
        target_repos = [repo_filter] if repo_filter else list(self.mappings.keys())

        for repo in target_repos:
            if repo not in self.mappings:
                violations.append(f"Unknown repository: '{repo}'")
                continue
            mapping = self.mappings[repo]
            subpaths = mapping.get("subpaths")
            if not subpaths:
                subpaths = [{"source_subpath": mapping["source_subpath"], "dest_subpath": mapping["dest_subpath"]}]

            for sub in subpaths:
                src_dir = self.source_root / sub["source_subpath"]
                if not src_dir.exists():
                    if not sub.get("optional"):
                        violations.append(f"Source directory missing for {repo}: {src_dir}")
                    continue

                for p in self._walk_source_files(src_dir, mapping):
                    rel = p.relative_to(self.source_root).as_posix()
                    try:
                        text = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    file_violations = self.redactor.find_violations(text, rel)
                    violations.extend(file_violations)

        return len(violations) == 0, violations


INTERNAL_ONLY_DOMAINS: set[str] = {
    "change-history",
    "scratch",
    "results",
    "projects",
    "actionable",
    "scripts/sync",
    "scripts/change-history",
    "scripts/projects",
    "scripts/repos",
    "scripts/cost-layers",
    "scripts/docs",
    "scripts/github",
    "scripts/google",
    "scripts/llm",
    "scripts/cloud",
    "scripts/confluence",
    "scripts/slack",
    "scripts/auth0",
    "scripts/qmd",
    "scripts/references",
    "scripts/research",
    "scripts/results",
    "scripts/routing",
    "scripts/ai-tooling",
    "scripts/cli",
    "scripts/daemon",
    "scripts/onboarding",
    "scripts/tests",
    "scripts/windows-security",
    "scripts/wiki",
    "scripts/_lib",
    "ai-tooling/memory",
    "ai-tooling/agents",
    "ai-tooling/a2a",
    "supporting/agent-factory",
    "supporting/kyverno",
    "supporting/powershell",
    "supporting/github",
    "supporting/tabler",
    "supporting/foundation",
    "supporting/cloudflare",
    "supporting/noir",
    "supporting/mermaid",
    "supporting/diagramming",
    "supporting/slack",
    "supporting/auth0",
    "supporting/google",
    "supporting/confluence",
    "supporting/qmd",
    "supporting/headroom",
    "supporting/ast-grep",
    "supporting/terraform",
    "supporting/aws",
    "supporting/discovery",
    "supporting/wiki",
    "supporting/local-llms",
    "supporting/bifrost",
}


def check_downstream_source_coverage(
    source_root: Path,
    mappings: dict[str, Any] | None = None,
) -> tuple[bool, list[str], list[str]]:
    """Audit source directories in ai-router to ensure every domain directory is mapped or declared internal."""
    if mappings is None:
        mappings = DEFAULT_REPO_MAPPINGS

    mapped_sources: set[str] = set()
    for mapping in mappings.values():
        if mapping.get("mode") == HARNESS_TEMPLATE_MODE:
            continue
        subpaths = mapping.get("subpaths")
        if subpaths:
            for sub in subpaths:
                mapped_sources.add(sub["source_subpath"].replace("\\", "/").rstrip("/"))
        elif "source_subpath" in mapping:
            mapped_sources.add(mapping["source_subpath"].replace("\\", "/").rstrip("/"))

    covered: list[str] = []
    unmapped: list[str] = []

    audit_roots = [
        ("ai-tooling/skills", source_root / "ai-tooling" / "skills"),
        ("docs/standards", source_root / "docs" / "standards"),
        ("references", source_root / "references"),
        ("research", source_root / "research"),
        ("supporting", source_root / "supporting"),
        ("scripts", source_root / "scripts"),
    ]

    for prefix, root_dir in audit_roots:
        if not root_dir.exists():
            continue
        if prefix in mapped_sources:
            covered.append(prefix)
            continue

        for child in sorted(root_dir.iterdir()):
            if not child.is_dir() or child.name.startswith(".") or child.name == "__pycache__":
                continue
            rel_path = child.relative_to(source_root).as_posix()
            if rel_path in INTERNAL_ONLY_DOMAINS or any(rel_path.startswith(d + "/") for d in INTERNAL_ONLY_DOMAINS):
                continue
            if (
                rel_path in mapped_sources
                or any(rel_path.startswith(m + "/") for m in mapped_sources)
                or any(m.startswith(rel_path) for m in mapped_sources)
                or prefix in mapped_sources
            ):
                covered.append(rel_path)
            else:
                unmapped.append(rel_path)

    return len(unmapped) == 0, covered, unmapped


def format_text_report(report: SyncReport) -> str:
    """Format human-readable sync and audit summary."""
    lines: list[str] = [
        "=" * 70,
        f"Multi-Repo Synchronization & Redaction Report",
        f"Timestamp: {report.timestamp_utc}",
        f"Source:    {report.source_root}",
        f"Dest:      {report.dest_root}",
        f"Mode:      {'DRY-RUN (Simulated)' if report.dry_run else 'LIVE (Wrote to disk)'}",
        "=" * 70,
        "",
        "Repository Summaries:",
        "-" * 70,
    ]

    for name, res in report.repos.items():
        status_tag = f"[{res.status.upper()}]"
        lines.append(
            f"{status_tag:<10} {name:<28} Scanned: {res.files_scanned:>3} | "
            f"Synced: {res.files_synced:>3} (Mod: {res.files_modified:>2}, Same: {res.files_unchanged:>2}) | "
            f"Redactions: {res.redactions_count:>3}"
        )
        if res.errors:
            for err in res.errors:
                lines.append(f"   ! ERROR: {err}")

    lines.append("-" * 70)
    lines.append(
        f"Total Repos: {report.summary.get('total_repos', 0)} | "
        f"Files Scanned: {report.summary.get('total_files_scanned', 0)} | "
        f"Files Synced: {report.summary.get('total_files_synced', 0)} | "
        f"Redactions Applied: {report.summary.get('total_redactions', 0)} | "
        f"Errors: {report.summary.get('total_errors', 0)}"
    )

    # Redaction Audit Logs
    all_audits = []
    for res in report.repos.values():
        all_audits.extend(res.audit_log)

    if all_audits:
        lines.extend([
            "",
            "=" * 70,
            f"Redaction Audit Log ({len(all_audits)} events):",
            "-" * 70,
        ])
        for entry in all_audits[:30]:
            lines.append(
                f"  - {entry['file']}:{entry['line']} [{entry['rule']}]\n"
                f"      Match:       {entry['match_fingerprint']} (length={entry['match_length']})\n"
                f"      Replacement: {entry['replacement']}"
            )
        if len(all_audits) > 30:
            lines.append(f"  ... and {len(all_audits) - 30} more redaction events.")
    else:
        lines.extend([
            "",
            "No sensitive patterns detected or redacted.",
        ])

    lines.append("=" * 70)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Source repository root directory (defaults to current git repo root)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Destination directory for exported repositories",
    )
    parser.add_argument(
        "--repo",
        type=str,
        choices=list(DEFAULT_REPO_MAPPINGS.keys()),
        default=None,
        help="Specific repository name to synchronize",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate synchronization and redaction without writing to destination",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON sync report and audit logs",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Source-cleanliness linter: scan source for secrets and proprietary leaks. Export leak control is --dry-run (redaction on copy).",
    )
    parser.add_argument(
        "--check-coverage",
        action="store_true",
        help="Audit source domains to ensure all areas are mapped to downstream repos or declared internal-only.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help="Optional file path to save JSON report output",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: exit 1 if any files would be modified/created/deleted",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 if any redactions occur or validation warnings arise",
    )

    args = parser.parse_args(argv)

    source_root = resolve_repo_root(args.source)
    dest_root = args.dest.resolve() if args.dest else (source_root / "scratch" / "exports")

    redactor = RedactionEngine()
    engine = SyncEngine(
        source_root=source_root,
        dest_root=dest_root,
        redactor=redactor,
        dry_run=args.dry_run or args.check,
    )

    if args.check_coverage or args.validate:
        coverage_ok = True
        validate_ok = True

        if args.check_coverage:
            is_ok, covered, unmapped = check_downstream_source_coverage(source_root)
            coverage_ok = is_ok
            if args.json:
                out = {
                    "check_coverage": True,
                    "ok": is_ok,
                    "covered_count": len(covered),
                    "unmapped_count": len(unmapped),
                    "covered": covered,
                    "unmapped": unmapped,
                }
                print(json.dumps(out, indent=2))
            else:
                if is_ok:
                    print(f"OK: All {len(covered)} source domains are mapped downstream or declared internal.")
                else:
                    print(f"COVERAGE FAILED: Found {len(unmapped)} unmapped source domain(s):")
                    for u in unmapped:
                        print(f"  ! Unmapped: {u}")

        if args.validate:
            is_clean, violations = engine.validate_sources(args.repo)
            validate_ok = is_clean
            if args.json:
                out = {
                    "validate": True,
                    "clean": is_clean,
                    "violation_count": len(violations),
                    "violations": violations,
                }
                print(json.dumps(out, indent=2))
            else:
                if is_clean:
                    print("OK: All source repositories validated clean with zero sensitive leaks.")
                else:
                    print(f"VALIDATION FAILED: Found {len(violations)} sensitive pattern(s):")
                    for v in violations:
                        print(f"  ! {v}")

        return 0 if (coverage_ok and validate_ok) else 1

    if not args.dest and not args.dry_run:
        # Default destination required if not dry run
        print("Note: No --dest specified. Defaulting destination to scratch/exports/ under repo root.", file=sys.stderr)

    report = engine.sync_all(args.repo)

    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        args.report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_text_report(report))

    if args.check:
        mods = report.summary.get("total_files_modified", 0)
        synced = report.summary.get("total_files_synced", 0)
        unchanged = report.summary.get("total_files_unchanged", 0)
        created = synced - unchanged - mods
        if mods > 0 or created > 0:
            return 1
            
    if args.strict and report.summary.get("total_redactions", 0) > 0:
        return 1

    return 0 if report.summary.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
