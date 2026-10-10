"""Automated repository beautification, branding, and hardening audit tool.

Scans the local ecosystem or organization repositories to verify compliance with
Koality-Assured branding standards: vector SVG logo and banner in assets/,
centered README hero with live auto-updating badges, LICENSE, and pyproject.toml
flat-layout setuptools hardening.

tags: [repos, audit, branding, beautification, linter, hardening]
routing_hints: [audit-beautification, repo-audit, beautify-audit, check-branding]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_REPOS = Path(__file__).resolve().parent
_LIB = Path(__file__).resolve().parents[1] / "_lib"
for _p in (_REPOS, _LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from beautify_repo import (
    DEFAULT_ORG,
    beautify_repository,
    validate_svg_xml,
)
from paths import resolve_repo_root


@dataclass
class RepoAuditResult:
    """Audit report for an individual repository."""

    repo_name: str
    repo_path: str
    compliant: bool
    has_logo: bool
    logo_valid_xml: bool
    has_banner: bool
    banner_valid_xml: bool
    has_readme: bool
    has_readme_hero: bool
    has_live_badges: bool
    has_license: bool
    is_python: bool
    pyproject_hardened: bool
    violations: list[str] = field(default_factory=list)
    remediated: bool = False


def audit_repository(repo_dir: Path) -> RepoAuditResult:
    """Audit a single repository directory for branding, asset, and hardening compliance."""
    repo_name = repo_dir.name
    violations: list[str] = []

    # 1. Logo
    logo_path = repo_dir / "assets" / f"{repo_name}-logo.svg"
    has_logo = logo_path.exists()
    logo_valid = False
    if not has_logo:
        violations.append("missing_logo_svg")
    else:
        try:
            logo_valid = validate_svg_xml(logo_path.read_text(encoding="utf-8"))
            if not logo_valid:
                violations.append("invalid_logo_svg_xml")
        except (OSError, UnicodeDecodeError):
            violations.append("unreadable_logo_svg")

    # 2. Banner
    banner_path = repo_dir / "assets" / f"{repo_name}-banner.svg"
    has_banner = banner_path.exists()
    banner_valid = False
    if not has_banner:
        violations.append("missing_banner_svg")
    else:
        try:
            banner_valid = validate_svg_xml(banner_path.read_text(encoding="utf-8"))
            if not banner_valid:
                violations.append("invalid_banner_svg_xml")
        except (OSError, UnicodeDecodeError):
            violations.append("unreadable_banner_svg")

    # 3. README Hero & Badges
    readme_path = repo_dir / "README.md"
    has_readme = readme_path.exists()
    has_hero = False
    has_badges = False
    if not has_readme:
        violations.append("missing_readme_md")
    else:
        readme_content = readme_path.read_text(encoding="utf-8")
        has_hero = ('<div align="center">' in readme_content) or (f"{repo_name}-banner.svg" in readme_content)
        has_badges = ("img.shields.io" in readme_content) or ("/actions/workflows/" in readme_content)
        if not has_hero:
            violations.append("missing_readme_hero")
        if not has_badges:
            violations.append("missing_live_badges")

    # 4. LICENSE
    license_path = repo_dir / "LICENSE"
    has_license = license_path.exists()
    if not has_license:
        violations.append("missing_license")

    # 5. Python flat-layout hardening
    pyproject_path = repo_dir / "pyproject.toml"
    is_python = pyproject_path.exists() or (repo_dir / "setup.py").exists() or list(repo_dir.glob("**/*.py")) != []
    pyproject_hardened = True
    if pyproject_path.exists():
        pyproject_content = pyproject_path.read_text(encoding="utf-8")
        if "[tool.setuptools]" not in pyproject_content:
            pyproject_hardened = False
            violations.append("pyproject_missing_setuptools_hardening")

    compliant = len(violations) == 0

    return RepoAuditResult(
        repo_name=repo_name,
        repo_path=str(repo_dir.resolve()),
        compliant=compliant,
        has_logo=has_logo,
        logo_valid_xml=logo_valid,
        has_banner=has_banner,
        banner_valid_xml=banner_valid,
        has_readme=has_readme,
        has_readme_hero=has_hero,
        has_live_badges=has_badges,
        has_license=has_license,
        is_python=is_python,
        pyproject_hardened=pyproject_hardened,
        violations=violations,
    )


def audit_ecosystem(
    scan_dir: Path,
    repo_names: list[str] | None = None,
    fix: bool = False,
    dry_run: bool = False,
    org: str = DEFAULT_ORG,
) -> dict[str, Any]:
    """Audit all Git repositories within scan_dir, with optional automated remediation."""
    if not scan_dir.exists() or not scan_dir.is_dir():
        raise FileNotFoundError(f"Scan directory not found: {scan_dir}")

    candidates: list[Path] = []
    if repo_names:
        for rname in repo_names:
            candidate = scan_dir / rname
            if candidate.is_dir() and (candidate / ".git").exists():
                candidates.append(candidate)
            elif (scan_dir.name == rname) and (scan_dir / ".git").exists():
                candidates.append(scan_dir)
    else:
        for child in sorted(scan_dir.iterdir()):
            # Check if directory is a git repository and not an internal worktree archive
            if child.is_dir() and (child / ".git").exists():
                # Skip worktrees ending with date/hash slugs unless requested
                if "-worktrees" in child.name:
                    continue
                candidates.append(child)

    results: list[RepoAuditResult] = []
    remediated_count = 0

    for repo_path in candidates:
        audit_res = audit_repository(repo_path)

        if not audit_res.compliant and fix:
            try:
                beautify_repository(
                    repo_dir=repo_path,
                    org=org,
                    dry_run=dry_run,
                    update_readme=True,
                )
                audit_res.remediated = True
                remediated_count += 1
            except (OSError, ValueError, RuntimeError) as exc:
                audit_res.violations.append(f"fix_failed: {exc}")

        results.append(audit_res)

    total_audited = len(results)
    compliant_count = sum(1 for r in results if r.compliant or r.remediated)
    non_compliant_count = total_audited - compliant_count

    return {
        "scan_dir": str(scan_dir.resolve()),
        "total_audited": total_audited,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "remediated_count": remediated_count,
        "dry_run": dry_run,
        "results": [asdict(r) for r in results],
    }


def resolve_ecosystem_dir(override: Path | None = None) -> Path:
    """Resolve the root ecosystem directory (e.g. c:\\Code\\KA) even from inside a worktree."""
    if override:
        return override.resolve()
    root = resolve_repo_root()
    curr = root
    while curr.parent != curr:
        if curr.name == "ai-router":
            return curr.parent
        curr = curr.parent
    return root.parent


def main() -> int:
    """CLI entrypoint for repository branding and hardening audit."""
    parser = argparse.ArgumentParser(
        description="Audit repositories for branding, asset, and hardening compliance."
    )
    parser.add_argument(
        "--scan-dir",
        type=Path,
        default=None,
        help="Directory containing repositories (defaults to parent of ai-router).",
    )
    parser.add_argument(
        "--repos",
        type=str,
        default=None,
        help="Comma-separated repository names to audit.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically remediate non-compliant repositories via beautify_repository.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report intended remediation actions without modifying files.",
    )
    parser.add_argument(
        "--org",
        type=str,
        default=DEFAULT_ORG,
        help=f"GitHub organization (defaults to {DEFAULT_ORG}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON summary report.",
    )

    args = parser.parse_args()

    scan_dir = resolve_ecosystem_dir(args.scan_dir)

    repo_names = [r.strip() for r in args.repos.split(",") if r.strip()] if args.repos else None

    report = audit_ecosystem(
        scan_dir=scan_dir,
        repo_names=repo_names,
        fix=args.fix,
        dry_run=args.dry_run,
        org=args.org,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=== Repository Branding & Hardening Audit ===")
        print(f"Scan Path: {report['scan_dir']}")
        print(f"Total Repositories: {report['total_audited']}")
        print(f"Compliant: {report['compliant_count']}")
        print(f"Non-Compliant: {report['non_compliant_count']}")
        if args.fix:
            print(f"Remediated: {report['remediated_count']}")
        print("\nRepository Breakdown:")

        for r in report["results"]:
            status_symbol = "PASS" if (r["compliant"] or r["remediated"]) else "FAIL"
            fix_suffix = " (Remediated)" if r["remediated"] else ""
            print(f"  [{status_symbol}] {r['repo_name']}{fix_suffix}")
            if r["violations"] and not r["remediated"]:
                for v in r["violations"]:
                    print(f"      - {v}")

    return 0 if report["non_compliant_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
