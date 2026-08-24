"""Adapter for QMD search, query, and get commands."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
        """Execute QMD command and return (returncode, stdout, stderr)."""
        bin_args = self.resolve_binary()
        cmd = [*bin_args, *args]
        to = timeout or self.config.timeout_sec

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=to,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            raise QMDError(f"QMD command timed out after {to}s: {' '.join(cmd)}") from exc
        except OSError as exc:
            raise QMDError(f"Failed to execute QMD CLI: {exc}") from exc

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
