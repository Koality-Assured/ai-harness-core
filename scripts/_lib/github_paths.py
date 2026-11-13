"""Map repo paths to https://github.com/<owner>/<repo>/{blob|tree}/main/... URLs.

Not indexed (``scripts/_lib/``). Used by github-ops helpers and results assemblers.
Never returns ``file://`` or local filesystem paths — only https GitHub URLs.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from safe_href import is_safe_href

# re-export for callers that imported from this module
__all__ = [
    "DEFAULT_REF",
    "GithubPathError",
    "discover_github_repo",
    "github_https_url",
    "parse_github_origin",
    "rewrite_repo_hrefs",
    "validate_ref",
]

DEFAULT_REF = "main"
GITHUB_HTTPS_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
GITHUB_SSH_RE = re.compile(
    r"^(?:ssh://)?git@github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
# Only <a href> and <img src> (quoted attributes)
A_HREF_RE = re.compile(
    r"""(?P<prefix><a\b(?P<pre>[^>]*?)\bhref\s*=\s*)(?P<q>["'])(?P<url>[^"']+)(?P=q)""",
    re.IGNORECASE,
)
IMG_SRC_RE = re.compile(
    r"""(?P<prefix><img\b(?P<pre>[^>]*?)\bsrc\s*=\s*)(?P<q>["'])(?P<url>[^"']+)(?P=q)""",
    re.IGNORECASE,
)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_BLOCK_RE = re.compile(r"(?is)<(pre|code)\b[^>]*>.*?</\1>")
MD_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
REF_SAFE_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")


class GithubPathError(ValueError):
    """Path or remote could not be resolved to a GitHub https URL."""


def validate_ref(ref: str, *, allow_non_main: bool = False) -> str:
    """Validate git ref for URL embedding. Default artifacts use ``main`` only."""
    if not ref or not REF_SAFE_RE.fullmatch(ref):
        raise GithubPathError(
            f"ref refused (quotes/whitespace/unsafe chars): {ref!r}"
        )
    if ref != DEFAULT_REF and not allow_non_main:
        raise GithubPathError(
            f"ref must be {DEFAULT_REF!r} unless --allow-ref is set (got {ref!r})"
        )
    return ref


def parse_github_origin(remote_url: str) -> tuple[str, str]:
    """Return (owner, repo) from an origin URL (HTTPS or SSH). github.com only."""
    url = (remote_url or "").strip()
    if not url:
        raise GithubPathError("empty git remote URL")
    for pattern in (GITHUB_HTTPS_RE, GITHUB_SSH_RE):
        match = pattern.match(url)
        if match:
            owner, repo = match.group(1), match.group(2)
            if repo.endswith(".git"):
                repo = repo[:-4]
            return owner, repo
    raise GithubPathError(
        f"origin is not a github.com remote (got {url!r}); "
        "expected https://github.com/owner/repo or git@github.com:owner/repo.git"
    )


def discover_github_repo(root: Path) -> tuple[str, str]:
    """Read ``git remote get-url origin`` under root → (owner, repo)."""
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GithubPathError(f"failed to read git remote: {exc}") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise GithubPathError(f"git remote get-url origin failed: {err or proc.returncode}")
    return parse_github_origin((proc.stdout or "").strip())


def _to_repo_relative(path: str | Path, root: Path) -> Path:
    """Resolve path to a POSIX-relative Path under root; reject escapes."""
    root = root.resolve()
    raw = Path(str(path).replace("\\", "/"))
    if raw.is_absolute() or (len(str(path)) >= 2 and str(path)[1] == ":"):
        candidate = Path(path).resolve()
    else:
        candidate = (root / Path(*Path(str(path).replace("\\", "/")).parts)).resolve()
    try:
        rel = candidate.relative_to(root)
    except ValueError as exc:
        raise GithubPathError(
            f"path is outside repo root ({root}): {path}"
        ) from exc
    return rel


def github_https_url(
    path: str | Path,
    *,
    root: Path,
    kind: str = "auto",
    ref: str = DEFAULT_REF,
    owner_repo: tuple[str, str] | None = None,
    allow_non_main_ref: bool = False,
) -> str:
    """Build a GitHub https URL for a path under the repo.

    ``kind``: ``auto`` (dir→tree, else blob), ``blob``, or ``tree``.
    Always returns ``https://github.com/...`` — never a local path.
    """
    ref = validate_ref(ref, allow_non_main=allow_non_main_ref)
    root = root.resolve()
    rel = _to_repo_relative(path, root)
    if owner_repo is None:
        owner, repo = discover_github_repo(root)
    else:
        owner, repo = owner_repo

    abs_path = (root / rel).resolve()
    if kind == "auto":
        use_tree = abs_path.is_dir()
    elif kind == "tree":
        use_tree = True
    elif kind == "blob":
        use_tree = False
    else:
        raise GithubPathError(f"kind must be auto|blob|tree (got {kind!r})")

    mode = "tree" if use_tree else "blob"
    encoded_ref = quote(ref, safe="")
    encoded = "/".join(quote(part, safe="") for part in rel.parts)
    if not encoded:
        return f"https://github.com/{owner}/{repo}/tree/{encoded_ref}"
    url = f"https://github.com/{owner}/{repo}/{mode}/{encoded_ref}/{encoded}"
    if not url.startswith("https://github.com/"):
        raise GithubPathError("internal error: non-https GitHub URL")
    if url.lower().startswith("file:") or re.match(r"^[a-zA-Z]:\\", url):
        raise GithubPathError("refusing local filesystem URL")
    return url


def _leave_alone(href: str) -> bool:
    """True for https/mailto/# that should not be rewritten."""
    h = href.strip()
    if not h or h.startswith("#"):
        return True
    lower = h.lower()
    return lower.startswith(("http://", "https://", "mailto:"))


def _rewrite_one_href(
    href: str,
    *,
    root: Path,
    from_file: Path,
    owner_repo: tuple[str, str],
    ref: str,
) -> str:
    raw = href.strip()
    if _leave_alone(raw):
        return raw
    # Dangerous / disallowed schemes and protocol-relative → neutralize
    if not is_safe_href(raw):
        return "#"

    fragment = ""
    path_part = raw
    if "#" in raw:
        path_part, _, frag = raw.partition("#")
        fragment = f"#{frag}"
    if not path_part:
        return raw

    base_dir = from_file.parent
    candidate = (base_dir / path_part).resolve()
    try:
        url = github_https_url(
            candidate,
            root=root,
            kind="auto",
            ref=ref,
            owner_repo=owner_repo,
            allow_non_main_ref=(ref != DEFAULT_REF),
        )
    except GithubPathError:
        return "#"
    return url + fragment


def _mask_segments(
    text: str,
    pattern: re.Pattern[str],
    *,
    held: list[str],
    prefix: str,
) -> str:
    def repl(match: re.Match[str]) -> str:
        held.append(match.group(0))
        return f"\x00{prefix}{len(held) - 1}\x00"

    return pattern.sub(repl, text)


def _unmask(text: str, held: list[str], prefix: str) -> str:
    # Restore in reverse so indices stay stable
    for i in range(len(held) - 1, -1, -1):
        text = text.replace(f"\x00{prefix}{i}\x00", held[i])
    return text


def rewrite_repo_hrefs(
    html_or_md: str,
    *,
    root: Path,
    from_file: Path,
    ref: str = DEFAULT_REF,
    owner_repo: tuple[str, str] | None = None,
    allow_non_main_ref: bool = False,
) -> str:
    """Rewrite ``<a href>`` / ``<img src>`` and Markdown links inside the repo.

    Skips contents of ``<pre>``/``<code>`` and fenced Markdown code blocks.
    Leaves ``http(s):``, ``mailto:``, ``#`` alone. Neutralizes dangerous schemes
    and outside-repo relatives to ``#`` (never leaves ``../`` escapes).
    """
    ref = validate_ref(ref, allow_non_main=allow_non_main_ref)
    root = root.resolve()
    from_file = Path(from_file).resolve()
    if owner_repo is None:
        owner_repo = discover_github_repo(root)

    held: list[str] = []
    prefix = "HOLD"
    text = _mask_segments(html_or_md, CODE_BLOCK_RE, held=held, prefix=prefix)
    text = _mask_segments(text, MD_FENCE_RE, held=held, prefix=prefix)

    def attr_sub(match: re.Match[str]) -> str:
        url = match.group("url")
        new = _rewrite_one_href(
            url, root=root, from_file=from_file, owner_repo=owner_repo, ref=ref
        )
        return f'{match.group("prefix")}{match.group("q")}{new}{match.group("q")}'

    def md_sub(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2).strip()
        new = _rewrite_one_href(
            url, root=root, from_file=from_file, owner_repo=owner_repo, ref=ref
        )
        return f"[{label}]({new})"

    text = A_HREF_RE.sub(attr_sub, text)
    text = IMG_SRC_RE.sub(attr_sub, text)
    text = MD_LINK_RE.sub(md_sub, text)
    return _unmask(text, held, prefix)
