"""Adapter for ast-grep outline and pattern search."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from ..config import AstGrepAdapterConfig, HarnessConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import AstGrepAdapterConfig, HarnessConfig


class AstGrepError(RuntimeError):
    """Base error for ast-grep operations."""


@dataclass
class AstGrepMatch:
    """Represents a structural pattern match from ast-grep."""

    file: str
    text: str
    line: int
    column: int
    end_line: int
    end_column: int
    language: str | None = None
    meta_variables: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert match to dictionary."""
        return asdict(self)


@dataclass
class AstGrepSymbol:
    """Represents an outlined code symbol (function, class, struct, etc.)."""

    name: str
    kind: str
    line: int
    column: int = 1
    context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert symbol to dictionary."""
        return asdict(self)


class AstGrepAdapter:
    """Adapter for locating and running the ast-grep CLI with structured output."""

    def __init__(
        self,
        config: AstGrepAdapterConfig | HarnessConfig | None = None,
        repo_root: Path | str | None = None,
        binary: str | Path | None = None,
    ) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.adapters.ast_grep
            self.repo_root = Path(repo_root).resolve() if repo_root else config.repo_root
        elif isinstance(config, AstGrepAdapterConfig):
            self.config = config
            self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        else:
            self.config = AstGrepAdapterConfig()
            self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()

        self._custom_binary = Path(binary) if binary else None

    def resolve_binary(self) -> Path:
        """Resolve the ast-grep executable path."""
        if self._custom_binary:
            if self._custom_binary.is_file():
                return self._custom_binary
            raise AstGrepError(f"Specified ast-grep binary does not exist: {self._custom_binary}")

        override = os.environ.get("AST_GREP", "").strip()
        if override:
            p = Path(override)
            if p.is_file():
                return p
            raise AstGrepError(f"AST_GREP is set but not a file: {override}")

        which = shutil.which("ast-grep")
        if which:
            return Path(which)

        exe_dir = Path(sys.executable).resolve().parent
        candidates: list[Path] = []
        if sys.platform == "win32":
            candidates.extend([
                exe_dir / "Scripts" / "ast-grep.exe",
                exe_dir / "ast-grep.exe",
            ])
        else:
            candidates.extend([
                exe_dir / "ast-grep",
                exe_dir / "bin" / "ast-grep",
            ])

        for cand in candidates:
            if cand.is_file():
                return cand

        sg = shutil.which("sg")
        if sg:
            return Path(sg)

        raise AstGrepError(
            "ast-grep CLI not found; install with: python -m pip install ast-grep-cli or npm install -g @ast-grep/cli"
        )

    def is_available(self) -> bool:
        """Check if ast-grep binary can be resolved."""
        try:
            self.resolve_binary()
            return True
        except AstGrepError:
            return False

    def _run(
        self,
        args: list[str],
        cwd: Path | None = None,
        stdin: str | None = None,
        timeout: int | None = None,
        check: bool = True,
    ) -> Any:
        """Execute ast-grep with args and parse JSON response."""
        exe = self.resolve_binary()
        cmd = [str(exe), *args]
        to = timeout or self.config.timeout_sec

        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd or self.repo_root,
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=to,
            )
        except subprocess.TimeoutExpired as exc:
            raise AstGrepError(f"ast-grep timed out after {to}s: {' '.join(cmd[:6])}") from exc
        except OSError as exc:
            raise AstGrepError(f"Failed to run ast-grep '{exe}': {exc}") from exc

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if check and proc.returncode != 0:
            detail = stderr[-800:] or stdout[-800:] or f"exit code {proc.returncode}"
            raise AstGrepError(f"ast-grep failed ({proc.returncode}): {detail}")

        if not stdout:
            return []

        payload = stdout
        start_arr = payload.find("[")
        start_obj = payload.find("{")
        starts = [i for i in (start_arr, start_obj) if i != -1]
        if starts:
            payload = payload[min(starts) :]

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            if proc.returncode != 0:
                detail = stderr[-800:] or stdout[-800:] or f"exit code {proc.returncode}"
                raise AstGrepError(f"ast-grep failed ({proc.returncode}): {detail}") from exc
            raise AstGrepError(f"ast-grep JSON parse failed: {exc}; head={stdout[:300]!r}") from exc

    def find_pattern(
        self,
        pattern: str,
        language: str | None = None,
        paths: list[str | Path] | None = None,
        rewrite: str | None = None,
    ) -> list[AstGrepMatch]:
        """Search for a structural code pattern."""
        args = ["run", "--pattern", pattern, "--json=compact"]
        if language:
            args.extend(["--lang", language])
        if rewrite:
            args.extend(["--rewrite", rewrite])

        if paths:
            for p in paths:
                args.append(str(p))

        raw_output = self._run(args)
        raw_list = raw_output if isinstance(raw_output, list) else [raw_output] if raw_output else []

        matches: list[AstGrepMatch] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            range_info = item.get("range", {})
            start = range_info.get("start", {})
            end = range_info.get("end", {})
            meta = item.get("metaVariables", {}).get("single", {})

            matches.append(
                AstGrepMatch(
                    file=str(item.get("file", "")),
                    text=str(item.get("text", "")),
                    line=int(start.get("line", item.get("lines", 0))),
                    column=int(start.get("column", 0)),
                    end_line=int(end.get("line", 0)),
                    end_column=int(end.get("column", 0)),
                    language=item.get("language") or language,
                    meta_variables=meta,
                )
            )
        return matches

    def rewrite(
        self,
        pattern: str,
        replacement: str,
        language: str | None = None,
        paths: list[str | Path] | None = None,
        update_all: bool = False,
    ) -> list[AstGrepMatch]:
        """Perform a structural pattern rewrite, optionally writing changes in-place with update_all."""
        args = ["run", "--pattern", pattern, "--rewrite", replacement, "--json=compact"]
        if update_all:
            args.append("--update-all")
        if language:
            args.extend(["--lang", language])
        if paths:
            for p in paths:
                args.append(str(p))

        raw_output = self._run(args)
        raw_list = raw_output if isinstance(raw_output, list) else [raw_output] if raw_output else []

        matches: list[AstGrepMatch] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            range_info = item.get("range", {})
            start = range_info.get("start", {})
            end = range_info.get("end", {})
            meta = item.get("metaVariables", {}).get("single", {})

            matches.append(
                AstGrepMatch(
                    file=str(item.get("file", "")),
                    text=str(item.get("text", "")),
                    line=int(start.get("line", item.get("lines", 0))),
                    column=int(start.get("column", 0)),
                    end_line=int(end.get("line", 0)),
                    end_column=int(end.get("column", 0)),
                    language=item.get("language") or language,
                    meta_variables=meta,
                )
            )
        return matches

    def outline(self, path: str | Path, language: str | None = None) -> list[AstGrepSymbol]:
        """Extract high-level outline symbols from a source file using native ast-grep outline."""
        target_path = Path(path)
        if not target_path.is_absolute():
            target_path = self.repo_root / target_path

        if not target_path.is_file():
            raise AstGrepError(f"File not found for outline: {target_path}")

        lang = language
        if not lang:
            ext = target_path.suffix.lower()
            ext_map = {
                ".py": "python",
                ".ts": "typescript",
                ".tsx": "tsx",
                ".js": "javascript",
                ".jsx": "jsx",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".rs": "rust",
                ".go": "go",
                ".c": "c",
                ".cpp": "cpp",
                ".h": "c",
                ".hpp": "cpp",
                ".java": "java",
                ".cs": "csharp",
                ".rb": "ruby",
                ".php": "php",
                ".html": "html",
                ".css": "css",
            }
            lang = ext_map.get(ext, "python")

        symbols: list[AstGrepSymbol] = []

        # Try native ast-grep outline subcommand first
        try:
            raw_output = self._run(
                ["outline", str(target_path), "-l", lang, "--json=compact"],
                check=False,
            )
            raw_list = raw_output if isinstance(raw_output, list) else [raw_output] if raw_output else []
            for file_entry in raw_list:
                if not isinstance(file_entry, dict):
                    continue
                for item in file_entry.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    symbol_type = str(item.get("symbolType") or item.get("astKind") or "symbol")
                    range_info = item.get("range", {})
                    start = range_info.get("start", {})
                    # Convert 0-indexed Tree-sitter line to 1-indexed editor line
                    line_no = int(start.get("line", 0)) + 1
                    col_no = int(start.get("column", 0)) + 1
                    sig = item.get("signature") or name
                    symbols.append(
                        AstGrepSymbol(
                            name=name,
                            kind=symbol_type,
                            line=line_no,
                            column=col_no,
                            context=sig,
                        )
                    )
            if symbols:
                symbols.sort(key=lambda s: s.line)
                return symbols
        except Exception:
            pass

        # Fallback to pattern-based matching if native outline was unavailable or empty
        patterns = []
        if lang == "python":
            patterns = [
                ("def $NAME($$$ARGS):", "function"),
                ("async def $NAME($$$ARGS):", "async_function"),
                ("class $NAME:", "class"),
                ("class $NAME($$$BASES):", "class"),
            ]
        elif lang in {"typescript", "javascript", "tsx", "jsx"}:
            patterns = [
                ("function $NAME($$$ARGS) { $$$BODY }", "function"),
                ("async function $NAME($$$ARGS) { $$$BODY }", "async_function"),
                ("class $NAME { $$$BODY }", "class"),
                ("const $NAME = ($$$ARGS) => { $$$BODY }", "arrow_function"),
                ("interface $NAME { $$$BODY }", "interface"),
                ("type $NAME = $$$DEF", "type_alias"),
            ]
        else:
            patterns = [
                ("function $NAME($$$ARGS)", "function"),
                ("class $NAME", "class"),
            ]

        for pat, kind in patterns:
            try:
                matches = self.find_pattern(pattern=pat, language=lang, paths=[target_path])
                for m in matches:
                    name = m.meta_variables.get("NAME", {}).get("text", "")
                    if not name:
                        tokens = m.text.strip().split()
                        if len(tokens) >= 2:
                            name = tokens[1].split("(")[0].split(":")[0].strip()
                        else:
                            name = m.text.strip()[:30]
                    symbols.append(
                        AstGrepSymbol(
                            name=name,
                            kind=kind,
                            line=m.line + 1,
                            column=m.column + 1,
                            context=m.text.splitlines()[0] if m.text else None,
                        )
                    )
            except Exception:
                continue

        symbols.sort(key=lambda s: s.line)
        return symbols
