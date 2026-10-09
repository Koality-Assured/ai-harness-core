"""Adapter for QMD search, query, and get commands."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

try:
    from ..config import HarnessConfig, QMDAdapterConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import HarnessConfig, QMDAdapterConfig

CHARS_PER_TOKEN = 4.0


class QMDError(RuntimeError):
    """Base error for QMD adapter operations."""


@dataclass
class QMDHit:
    """Represents a search or query hit returned by QMD."""

    docid: str | None
    score: float
    file: str
    line: int | None = None
    title: str | None = None
    context: str | None = None
    snippet: str | None = None
    snippet_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert hit to dictionary."""
        return asdict(self)


class QMDAdapter:
    """Adapter for executing QMD CLI operations with structured JSON outputs."""

    def __init__(
        self,
        config: QMDAdapterConfig | HarnessConfig | None = None,
        repo_root: Path | str | None = None,
        binary: str | Path | None = None,
    ) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.adapters.qmd
            self.repo_root = Path(repo_root).resolve() if repo_root else config.repo_root
        elif isinstance(config, QMDAdapterConfig):
            self.config = config
            self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        else:
            self.config = QMDAdapterConfig()
            self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()

        self._custom_binary = str(binary) if binary else None

    def _run_git(self, args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.config.timeout_sec,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise QMDError(f"Git command failed while preparing the QMD source: {exc}") from exc

    def _git_output(self, args: list[str], *, cwd: Path, description: str) -> str:
        proc = self._run_git(args, cwd=cwd)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "Git command failed").strip()
            raise QMDError(f"{description}: {detail}")
        return proc.stdout.strip()

    def _primary_repo_root(self) -> Path:
        checkout = Path(self._git_output(
            ["rev-parse", "--show-toplevel"], cwd=self.repo_root, description="cannot resolve the repository checkout"
        )).resolve()
        common_text = self._git_output(
            ["rev-parse", "--git-common-dir"], cwd=checkout, description="cannot resolve the shared Git directory"
        )
        common = Path(common_text)
        if not common.is_absolute():
            common = checkout / common
        return common.resolve().parent

    @staticmethod
    def _worktree_records(output: str) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        record: dict[str, str] = {}
        for line in output.splitlines():
            if not line:
                if record:
                    records.append(record)
                    record = {}
            elif line.startswith("worktree "):
                record["path"] = line[9:]
            elif line.startswith("branch "):
                record["branch"] = line[7:]
            elif line == "detached":
                record["detached"] = "true"
        if record:
            records.append(record)
        return records

    def _dedicated_qmd_source(self, primary_root: Path) -> Path:
        selector_proc = self._run_git(
            ["config", "--local", "--get-all", "harness.qmd.source-worktree"], cwd=primary_root
        )
        if selector_proc.returncode == 1:
            selector = self.config.source_worktree
        elif selector_proc.returncode != 0:
            detail = (selector_proc.stderr or selector_proc.stdout or "could not read the shared selector").strip()
            raise QMDError(f"could not read repository-common QMD source selector: {detail}")
        else:
            values = selector_proc.stdout.splitlines()
            if len(values) != 1:
                raise QMDError(
                    "repository-common QMD source selector is ambiguous; configure exactly one "
                    "harness.qmd.source-worktree value"
                )
            selector = values[0].strip()

        if not re.fullmatch(r"scratch/qmd-main(?:-[A-Za-z0-9][A-Za-z0-9_-]{0,63})?", selector):
            raise QMDError(
                "invalid QMD source selector; choose scratch/qmd-main or a safe unique suffix in "
                "harness.qmd.source-worktree or config/harness.config.json"
            )
        repo_root = primary_root.resolve()
        source = (repo_root / selector).resolve()
        try:
            resolved_relative = source.relative_to(repo_root)
        except ValueError as exc:
            raise QMDError(f"QMD source_worktree escapes the repository root: {selector}") from exc
        expected_relative = Path(*selector.split("/"))
        if os.path.normcase(str(resolved_relative)) != os.path.normcase(str(expected_relative)):
            raise QMDError(f"QMD source_worktree must not resolve through a symlink: {selector}")

        output = self._git_output(
            ["worktree", "list", "--porcelain"], cwd=primary_root, description="cannot inspect registered Git worktrees"
        )
        candidates: list[dict[str, str]] = []
        for record in self._worktree_records(output):
            raw_path = record.get("path")
            if not raw_path:
                continue
            path = Path(raw_path).resolve()
            if os.path.normcase(str(path)) == os.path.normcase(str(source)):
                candidates.append(record)

        if len(candidates) != 1:
            detail = "not found" if not candidates else "ambiguous"
            raise QMDError(
                f"selected detached QMD source {detail}: {selector}; register this exact path as a detached "
                f"worktree. Other snapshots are preserved. QMD never falls back to {self.repo_root}."
            )
        record = candidates[0]
        if not source.is_dir() or "branch" in record or record.get("detached") != "true":
            raise QMDError(f"dedicated QMD source must be a registered detached worktree: {source}")
        if not (source / ".qmd" / "index.yml").is_file():
            raise QMDError(f"dedicated QMD source has no tracked .qmd/index.yml: {source}")
        symbolic = self._run_git(["symbolic-ref", "--quiet", "HEAD"], cwd=source)
        if symbolic.returncode == 0:
            raise QMDError(f"dedicated QMD source is attached to a branch: {source}")
        if symbolic.returncode != 1:
            detail = (symbolic.stderr or symbolic.stdout or "could not verify detached HEAD").strip()
            raise QMDError(f"could not verify dedicated QMD source {source}: {detail}")
        return source

    @contextmanager
    def _source_lock(self, primary_root: Path) -> Iterator[None]:
        lock_key = hashlib.sha256(os.path.normcase(str(primary_root.resolve())).encode("utf-8")).hexdigest()[:20]
        lock_path = Path(tempfile.gettempdir()) / f"codex-qmd-source-{lock_key}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            if os.name == "nt":
                import msvcrt

                while True:
                    try:
                        handle.seek(0)
                        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                        break
                    except OSError:
                        time.sleep(0.1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @contextmanager
    def _fresh_main_source(self) -> Iterator[Path]:
        primary_root = self._primary_repo_root()
        with self._source_lock(primary_root):
            source = self._dedicated_qmd_source(primary_root)
            status = self._run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=source)
            if status.returncode != 0:
                detail = (status.stderr or status.stdout or "git status failed").strip()
                raise QMDError(f"cannot verify dedicated QMD source status: {detail}")
            if status.stdout.strip():
                raise QMDError(
                    f"dedicated QMD source has tracked or untracked changes; preserving it: {source}"
                )

            branch = self.config.source_branch
            ref_check = self._run_git(["check-ref-format", "--branch", branch], cwd=primary_root)
            if ref_check.returncode != 0:
                raise QMDError(f"invalid QMD source branch: {branch!r}")

            temporary_ref = f"refs/codex/qmd-refresh/{uuid.uuid4().hex}"
            fetched_oid: str | None = None
            try:
                fetch = self._run_git(
                    [
                        "fetch", "--no-tags", "--no-write-fetch-head", "origin",
                        f"+refs/heads/{branch}:{temporary_ref}",
                    ],
                    cwd=primary_root,
                )
                if fetch.returncode != 0:
                    detail = (fetch.stderr or fetch.stdout or "git fetch failed").strip()
                    raise QMDError(f"could not fetch origin/{branch} for QMD: {detail}")
                fetched_oid = self._git_output(
                    ["rev-parse", "--verify", f"{temporary_ref}^{{commit}}"],
                    cwd=primary_root,
                    description=f"could not resolve fetched origin/{branch} commit",
                )

                head_oid = self._git_output(
                    ["rev-parse", "--verify", "HEAD^{commit}"], cwd=source,
                    description="could not resolve dedicated QMD source HEAD",
                )
                ancestry = self._run_git(["merge-base", "--is-ancestor", head_oid, fetched_oid], cwd=source)
                if ancestry.returncode == 1:
                    raise QMDError(
                        f"dedicated QMD source diverged from origin/{branch}; preserving it: {source}"
                    )
                if ancestry.returncode != 0:
                    detail = (ancestry.stderr or ancestry.stdout or "ancestry check failed").strip()
                    raise QMDError(f"could not verify dedicated QMD source ancestry: {detail}")
                if head_oid != fetched_oid:
                    merge = self._run_git(["merge", "--ff-only", fetched_oid], cwd=source)
                    if merge.returncode != 0:
                        detail = (merge.stderr or merge.stdout or "fast-forward failed").strip()
                        raise QMDError(f"could not fast-forward dedicated QMD source: {detail}")

                after_sync = self._run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=source)
                if after_sync.returncode != 0 or after_sync.stdout.strip():
                    raise QMDError(f"dedicated QMD source is not clean after fast-forward; preserving it: {source}")
                yield source
            finally:
                if fetched_oid is None:
                    probe = self._run_git(
                        ["rev-parse", "--verify", f"{temporary_ref}^{{commit}}"], cwd=primary_root
                    )
                    candidate = (probe.stdout or "").strip()
                    if probe.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?", candidate):
                        fetched_oid = candidate
                if fetched_oid is not None:
                    removed = self._run_git(["update-ref", "-d", temporary_ref, fetched_oid], cwd=primary_root)
                    if removed.returncode != 0:
                        detail = (removed.stderr or removed.stdout or "could not remove temporary QMD ref").strip()
                        if sys.exc_info()[0] is None:
                            raise QMDError(f"could not remove temporary QMD ref {temporary_ref}: {detail}")

    def _run_qmd(
        self, args: list[str], *, cwd: Path, timeout: int | None = None
    ) -> tuple[int, str, str]:
        bin_args = self.resolve_binary()
        command = [*bin_args, *args]
        to = timeout or self.config.timeout_sec
        try:
            proc = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=to,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            raise QMDError(f"QMD command timed out after {to}s: {' '.join(command)}") from exc
        except OSError as exc:
            raise QMDError(f"Failed to execute QMD CLI: {exc}") from exc

    def resolve_binary(self) -> list[str]:
        """Resolve the QMD executable argv list."""
        if self._custom_binary:
            return [self._custom_binary]

        env_override = os.environ.get("QMD_BIN", "").strip()
        if env_override:
            return [env_override]

        cmd_name = self.config.command
        if sys.platform == "win32":
            shim = shutil.which(f"{cmd_name}.cmd") or shutil.which(f"{cmd_name}.exe") or shutil.which(cmd_name)
        else:
            shim = shutil.which(cmd_name)

        if not shim:
            raise QMDError(f"QMD executable '{cmd_name}' not found on PATH.")

        shim_path = Path(shim)
        node = shim_path.parent / "node.exe"
        cli = shim_path.parent / "node_modules" / "@tobilu" / "qmd" / "bin" / "qmd"
        if sys.platform == "win32" and node.is_file() and cli.is_file():
            return [str(node), str(cli)]

        return [shim]

    def is_available(self) -> bool:
        """Check if QMD CLI is executable and available."""
        try:
            self.resolve_binary()
            return True
        except QMDError:
            return False

    def _run(self, args: list[str], timeout: int | None = None) -> tuple[int, str, str]:
        """Refresh the registered detached main snapshot, then run QMD there."""
        with self._fresh_main_source() as source:
            code, stdout, stderr = self._run_qmd(["update"], cwd=source, timeout=timeout)
            if code != 0:
                raise QMDError(f"QMD index refresh failed ({code}): {(stderr or stdout).strip()}")
            status = self._run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=source)
            if status.returncode != 0 or status.stdout.strip():
                raise QMDError(f"QMD index refresh changed tracked or untracked source data; preserving {source}")
            return self._run_qmd(args, cwd=source, timeout=timeout)

    @staticmethod
    def _parse_json(stdout: str) -> Any:
        """Extract and parse JSON array or object from stdout."""
        text = stdout.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start_arr = text.find("[")
            start_obj = text.find("{")
            starts = [i for i in (start_arr, start_obj) if i != -1]
            if not starts:
                raise QMDError(f"QMD output did not contain valid JSON: {text[:400]!r}")
            start = min(starts)
            try:
                return json.loads(text[start:])
            except json.JSONDecodeError as exc:
                raise QMDError(f"Failed to parse QMD JSON: {exc}; raw head={text[:400]!r}") from exc

    @staticmethod
    def _normalize_file_uri(file_uri: str) -> str:
        path = (file_uri or "").strip()
        if path.startswith("qmd://"):
            path = path[len("qmd://") :]
        return path.replace("\\", "/")

    def _build_hits(self, raw_items: list[dict[str, Any]]) -> list[QMDHit]:
        hits: list[QMDHit] = []
        for item in raw_items:
            file_path = self._normalize_file_uri(str(item.get("file", "")))
            snippet = item.get("snippet")
            snip_tokens = max(1, int(round(len(snippet) / CHARS_PER_TOKEN))) if snippet else 0
            hits.append(
                QMDHit(
                    docid=item.get("docid"),
                    score=float(item.get("score", 0.0)),
                    file=file_path,
                    line=item.get("line"),
                    title=item.get("title"),
                    context=item.get("context"),
                    snippet=snippet,
                    snippet_tokens=snip_tokens,
                )
            )
        return hits

    def search(
        self,
        query: str,
        collection: str | None = None,
        min_score: float | None = None,
        limit: int | None = None,
    ) -> list[QMDHit]:
        """Perform fast BM25 lexical search."""
        score_val = min_score if min_score is not None else self.config.default_min_score
        n_val = limit if limit is not None else self.config.default_limit

        args = ["search", "--format", "json", "--min-score", str(score_val), "-n", str(n_val)]
        if collection:
            args.extend(["-c", collection])
        args.append(query)

        code, stdout, stderr = self._run(args)
        if code != 0:
            raise QMDError(f"QMD search failed ({code}): {(stderr or stdout).strip()}")

        data = self._parse_json(stdout)
        raw_hits = data if isinstance(data, list) else data.get("results") or data.get("hits") or []
        return self._build_hits(raw_hits)

    def query(
        self,
        lex: str | None = None,
        vec: str | None = None,
        prompt: str | None = None,
        min_score: float | None = None,
        limit: int | None = None,
        rerank: bool = False,
    ) -> list[QMDHit]:
        """Perform structured or hybrid semantic query."""
        score_val = min_score if min_score is not None else self.config.default_min_score
        n_val = limit if limit is not None else self.config.default_limit

        args = ["query", "--format", "json", "--min-score", str(score_val), "-n", str(n_val)]
        if not rerank:
            args.append("--no-rerank")

        if lex or vec:
            qdoc = f"lex: {lex or ''}\nvec: {vec or ''}"
            args.append(qdoc)
        elif prompt:
            args.append(prompt)
        else:
            raise ValueError("Must provide either (lex, vec) or prompt string to query()")

        code, stdout, stderr = self._run(args)
        if code != 0:
            raise QMDError(f"QMD query failed ({code}): {(stderr or stdout).strip()}")

        data = self._parse_json(stdout)
        raw_hits = data if isinstance(data, list) else data.get("results") or data.get("hits") or []
        return self._build_hits(raw_hits)

    def get(self, docid_or_uri: str) -> str:
        """Fetch raw document content by docid or URI."""
        args = ["get", docid_or_uri]
        code, stdout, stderr = self._run(args)
        if code != 0:
            raise QMDError(f"QMD get failed ({code}): {(stderr or stdout).strip()}")
        return stdout

    def list_collections(self) -> list[str]:
        """List registered QMD collections."""
        code, stdout, stderr = self._run(["collection", "list"])
        if code != 0:
            raise QMDError(f"QMD collection list failed ({code}): {(stderr or stdout).strip()}")
        names: list[str] = []
        for line in stdout.splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+)\s+\(qmd://", line.strip())
            if m:
                names.append(m.group(1))
        return names

    def list_files(self, collection: str) -> list[str]:
        """List indexed files in a collection."""
        code, stdout, stderr = self._run(["ls", collection])
        if code != 0:
            raise QMDError(f"QMD ls failed ({code}): {(stderr or stdout).strip()}")
        files: list[str] = []
        for line in stdout.splitlines():
            if "qmd://" in line:
                uri = line[line.index("qmd://") :].strip()
                files.append(self._normalize_file_uri(uri))
        return files
