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
    HARNESS_TEMPLATE_ALLOWED_DOT_DIRS,
    HARNESS_TEMPLATE_MODE,
    harness_template_dir_may_contain_kept,
    harness_template_post_copy_files,
    harness_template_prune_dest_leftovers,
    harness_template_sanitize_file_content,
    is_harness_template_rel_kept,
    WIKI_TEMPLATE_ALLOWED_DOT_DIRS,
    HARNESS_TEMPLATE_MODE,
    is_harness_template_rel_kept,
    harness_template_dir_may_contain_kept,
    harness_template_post_copy_files,
    harness_template_prune_dest_leftovers,
    harness_template_sanitize_file_content,
)


DEFAULT_REPO_MAPPINGS: dict[str, dict[str, str]] = {
    "agent-skills-and-tools": {
        "source_subpath": "ai-tooling/skills",
        "dest_subpath": "skills",
        "description": "Skills and tools export",
    },
    "agent-standards": {
        "source_subpath": "docs/standards",
        "dest_subpath": "standards",
        "description": "Agent standards and security policies export",
    },
    "security-standards": {
        "source_subpath": "docs/standards",
        "dest_subpath": "standards",
        "description": "General engineering and organizational security standards export",
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
            pattern=re.compile(r"\bsk-ant-[a-zA-Z0-9_-]{20,}\b"),
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
            pattern=re.compile(r"(?i)[a-zA-Z]:\\Users\\[a-zA-Z0-9_\-\.]+"),
            replacement="C:\\Users\\developer",
        ),
        RedactionRule(
            name="unix_user_home_path",
            description="Unix / macOS local user home directory paths",
            pattern=re.compile(r"/(?:Users|home)/[a-zA-Z0-9_\-\.]+"),
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
            pattern=re.compile(r"(?i)[a-zA-Z]:[\\/](?:Code|Projects|repos|dev)[\\/]ai-router[\\/]"),
            replacement="[REPO_ROOT]/",
        ),
        RedactionRule(
            name="google_drive_test_folder",
            description="Google Drive test folder ID and URL",
            pattern=re.compile(r"https?://drive\.google\.com/drive/folders/1noGxOG_[a-zA-Z0-9_-]+|1noGxOG_[a-zA-Z0-9_-]+"),
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

    usernames = ["developer", "developer"]
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
        if self.dest_root.name == repo_name:
            return self.dest_root / dest_subpath
        return self.dest_root / repo_name / dest_subpath

    def _walk_source_files(self, src_dir: Path, mapping: dict[str, str]) -> list[Path]:
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
                if d in EXCLUDED_NAMES:
                    continue
                if d.startswith("."):
                    if not (mode == HARNESS_TEMPLATE_MODE and d in WIKI_TEMPLATE_ALLOWED_DOT_DIRS):
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
                collected.append(src_file)
        return collected

    def _sync_text_payload(
        self,
        dest_file: Path,
        raw_text: str,
        display_rel: str,
        result: RepoSyncResult,
    ) -> None:
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

        return result

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
                    try:
                        text = p.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    rel = p.relative_to(self.source_root).as_posix()
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
    "scripts/qmd",
    "scripts/references",
    "scripts/research",
    "scripts/results",
    "scripts/routing",
    "scripts/ai-tooling",
    "scripts/tests",
    "scripts/_lib",
    "ai-tooling/memory",
    "ai-tooling/agents",
    "ai-tooling/a2a",
    "supporting/powershell",
    "supporting/github",
    "supporting/tabler",
    "supporting/foundation",
    "supporting/cloudflare",
    "supporting/noir",
    "supporting/mermaid",
    "supporting/slack",
    "supporting/google",
    "supporting/confluence",
    "supporting/qmd",
    "supporting/headroom",
    "supporting/ast-grep",
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
        "--strict",
        action="store_true",
        help="Fail with exit code 1 if any redactions occur or validation warnings arise",
    )

    args = parser.parse_args(argv)

    source_root = resolve_repo_root(args.source)
    dest_root = args.dest.resolve() if args.dest else (source_root / "scratch" / "exports")

    if args.check_coverage:
        is_ok, covered, unmapped = check_downstream_source_coverage(source_root)
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
        return 0 if is_ok else 1

    redactor = RedactionEngine()
    engine = SyncEngine(
        source_root=source_root,
        dest_root=dest_root,
        redactor=redactor,
        dry_run=args.dry_run,
    )

    if args.validate:
        is_clean, violations = engine.validate_sources(args.repo)
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
        return 0 if is_clean else 1

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

    if args.strict and report.summary.get("total_redactions", 0) > 0:
        return 1

    return 0 if report.summary.get("success", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
