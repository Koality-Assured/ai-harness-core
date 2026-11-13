"""Resolve local repo paths to GitHub https blob/tree URLs on main.

tags: [github]
routing_hints: [blob, main, path, url]

Maps paths under the repo to
``https://github.com/<owner>/<repo>/{blob|tree}/main/...`` using
``git remote get-url origin`` (HTTPS or SSH, github.com only). Never prints
``file://`` or local drive paths.

Accepts positional PATH and/or repeatable ``--path``.

Example::

  python scripts/github/resolve_github_path.py AGENTS.md --dry-run
  python scripts/github/resolve_github_path.py --path docs/ --path scripts/ --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from github_paths import (  # noqa: E402
    DEFAULT_REF,
    GithubPathError,
    discover_github_repo,
    github_https_url,
    validate_ref,
)
from paths import resolve_repo_root  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "positional_paths",
        nargs="*",
        metavar="PATH",
        help="Repo-relative or absolute path under the repo",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="flag_paths",
        default=None,
        help="Repo-relative or absolute path under the repo (repeatable)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (default: cwd via git rev-parse)",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"Git ref for URLs (default: {DEFAULT_REF}; non-main needs --allow-ref)",
    )
    parser.add_argument(
        "--allow-ref",
        action="store_true",
        help="Allow --ref other than main (assemblers must not pass this)",
    )
    parser.add_argument(
        "--kind",
        choices=("auto", "blob", "tree"),
        default="auto",
        help="URL kind (default: auto — dirs use tree, files use blob)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON array of {path, url} objects",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved URLs only (read-only; no side effects)",
    )
    args = parser.parse_args(argv)
    root = resolve_repo_root(args.repo_root)

    paths: list[str] = list(args.positional_paths or [])
    if args.flag_paths:
        paths.extend(args.flag_paths)
    if not paths:
        print("error: provide PATH and/or --path", file=sys.stderr)
        return 2

    try:
        validate_ref(args.ref, allow_non_main=args.allow_ref)
        owner_repo = discover_github_repo(root)
    except GithubPathError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    owner, repo = owner_repo
    print(f"origin: https://github.com/{owner}/{repo} (ref={args.ref})", file=sys.stderr)

    results: list[dict[str, str]] = []
    for raw in paths:
        try:
            url = github_https_url(
                raw,
                root=root,
                kind=args.kind,
                ref=args.ref,
                owner_repo=owner_repo,
                allow_non_main_ref=args.allow_ref,
            )
        except GithubPathError as exc:
            print(f"error: {raw}: {exc}", file=sys.stderr)
            return 2
        if not url.startswith("https://github.com/"):
            print(f"error: refused non-https result for {raw}", file=sys.stderr)
            return 2
        results.append({"path": raw, "url": url})

    if args.dry_run:
        print("dry-run: resolved URLs (no writes)", file=sys.stderr)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(item["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
