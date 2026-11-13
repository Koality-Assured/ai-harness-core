"""Default workspace coding tools for harness chat.

tags: [harness, cli, workspace_tools, tools, coding]
routing_hints: [workspace_tools, read_file, list_dir, grep_search, edit_file, write_file, run_command, ask_question]
"""

from __future__ import annotations

import difflib
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from cli.interactive_choice import handle_ask_question
from cli.tool_registry import ToolRegistry

MAX_COMMAND_OUTPUT_CHARS = 100_000
MAX_READ_LINES = 2_000
MAX_READ_CHARS = 100_000
MAX_UNBOUNDED_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def resolve_workspace_path(path_str: str, root_str: str) -> Path:
    """Resolve a relative or absolute path against workspace root and verify containment.

    Raises:
        ValueError: Path escapes workspace root (if resolved path is outside root).
    """
    root = Path(root_str).resolve()
    raw = Path(path_str) if path_str else Path(".")
    target = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"Path escapes workspace root: {path_str}") from None
    return target


def handle_read_file(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Read file contents within workspace, optionally bounded by line numbers."""
    path_arg = arguments.get("path")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise ValueError("path must be a non-empty string")

    target = resolve_workspace_path(path_arg, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path_arg}")
    if not target.is_file():
        raise ValueError(f"Path is not a regular file: {path_arg}")

    start_line_arg = arguments.get("start_line")
    end_line_arg = arguments.get("end_line")

    if start_line_arg is not None:
        try:
            start_line_arg = int(start_line_arg)
        except (ValueError, TypeError):
            start_line_arg = 1
    if end_line_arg is not None:
        try:
            end_line_arg = int(end_line_arg)
        except (ValueError, TypeError):
            end_line_arg = None

    file_size = target.stat().st_size
    if file_size > MAX_UNBOUNDED_FILE_SIZE and start_line_arg is None and end_line_arg is None:
        raise ValueError(
            f"File exceeds 10MB limit ({file_size} bytes); specify start_line and end_line to slice"
        )

    try:
        with open(target, "rb") as f:
            chunk = f.read(8192)
            if b"\0" in chunk:
                raise ValueError(f"Binary file detected: {path_arg}")
        content = target.read_text(encoding="utf-8")
        if "\0" in content:
            raise ValueError(f"Binary file detected: {path_arg}")
    except UnicodeDecodeError:
        raise ValueError(f"Binary file detected (non-UTF8): {path_arg}")

    lines = content.splitlines()
    total_lines = len(lines)

    start = max(1, start_line_arg) if start_line_arg is not None else 1
    end = min(total_lines, end_line_arg) if end_line_arg is not None else total_lines

    formatted_lines: list[str] = []
    if total_lines > 0 and start <= end:
        for idx in range(start, end + 1):
            if len(formatted_lines) >= MAX_READ_LINES:
                formatted_lines.append(f"[Output truncated: exceeded {MAX_READ_LINES} lines]")
                break
            formatted_lines.append(f"{idx}: {lines[idx - 1]}")

    formatted_content = "\n".join(formatted_lines)
    if len(formatted_content) > MAX_READ_CHARS:
        formatted_content = (
            formatted_content[:MAX_READ_CHARS]
            + f"\n[Output truncated: exceeded {MAX_READ_CHARS} characters]"
        )

    return {
        "content": formatted_content,
        "path": path_arg,
        "total_lines": total_lines,
        "start_line": start,
        "end_line": end,
    }


def handle_list_dir(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """List entries with [DIR] / [FILE] indicators up to a given depth."""
    path_arg = arguments.get("path", ".")
    try:
        depth = min(max(1, int(arguments.get("depth", 1))), 10)
    except (ValueError, TypeError):
        depth = 1
    include_hidden = bool(arguments.get("include_hidden", False))

    root = Path(workspace_root).resolve()
    target = resolve_workspace_path(path_arg, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path_arg}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path_arg}")

    entries: list[str] = []
    visited_dirs: set[Path] = {target.resolve()}

    def _traverse(current_dir: Path, current_depth: int) -> None:
        try:
            items = sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except (PermissionError, OSError):
            return
        for item in items:
            if len(entries) >= 1000:
                break
            name = item.name
            if not include_hidden and name.startswith("."):
                continue

            try:
                resolved_item = item.resolve()
                resolved_item.relative_to(root)
            except (ValueError, RuntimeError):
                continue

            rel = item.relative_to(target).as_posix()
            if item.is_dir():
                entries.append(f"[DIR]  {rel}")
                if current_depth < depth:
                    if resolved_item not in visited_dirs:
                        visited_dirs.add(resolved_item)
                        _traverse(item, current_depth + 1)
            else:
                entries.append(f"[FILE] {rel}")

    _traverse(target, 1)
    if len(entries) >= 1000:
        entries.append("[Output truncated: reached 1000 entries limit]")
    output = "\n".join(entries)
    return {
        "entries": entries,
        "output": output,
        "count": len(entries),
        "path": path_arg,
    }


def handle_grep_search(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Regex or substring search over files in workspace."""
    pattern_str = arguments.get("pattern")
    if not isinstance(pattern_str, str) or not pattern_str:
        raise ValueError("pattern must be a non-empty string")

    path_arg = arguments.get("path", ".")
    glob_filter = arguments.get("glob")

    target = resolve_workspace_path(path_arg, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {path_arg}")

    try:
        regex = re.compile(pattern_str)
    except re.error:
        regex = re.compile(re.escape(pattern_str))

    root_path = Path(workspace_root).resolve()
    matches: list[dict[str, Any]] = []
    formatted_matches: list[str] = []

    files_to_check: list[Path] = []
    if target.is_file():
        files_to_check.append(target)
    else:
        visited_dirs: set[Path] = {target.resolve()}
        for root, dirs, files in os.walk(target):
            valid_dirs: list[str] = []
            for d in dirs:
                if d.startswith("."):
                    continue
                dpath = Path(root) / d
                try:
                    resolved_d = dpath.resolve()
                    resolved_d.relative_to(root_path)
                except (ValueError, RuntimeError):
                    continue
                if resolved_d in visited_dirs:
                    continue
                visited_dirs.add(resolved_d)
                valid_dirs.append(d)
            dirs[:] = valid_dirs

            for f in sorted(files):
                if f.startswith("."):
                    continue
                file_p = Path(root) / f
                try:
                    resolved_f = file_p.resolve()
                    resolved_f.relative_to(root_path)
                except (ValueError, RuntimeError):
                    continue
                if glob_filter:
                    rel_p = file_p.relative_to(target).as_posix()
                    if not fnmatch.fnmatch(f, glob_filter) and not fnmatch.fnmatch(rel_p, glob_filter):
                        continue
                files_to_check.append(file_p)

    for fpath in files_to_check:
        try:
            with open(fpath, "rb") as bf:
                chunk = bf.read(8192)
                if b"\0" in chunk:
                    continue
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel_display = fpath.relative_to(root_path).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                formatted = f"{rel_display}:{line_no}: {line}"
                formatted_matches.append(formatted)
                matches.append({
                    "file": rel_display,
                    "line": line_no,
                    "content": line,
                })
                if len(formatted_matches) >= 1000:
                    break
        if len(formatted_matches) >= 1000:
            break

    output = "\n".join(formatted_matches)
    return {
        "matches": matches,
        "formatted": formatted_matches,
        "output": output,
        "count": len(matches),
    }


def handle_edit_file(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Single contiguous replacement in file returning unified diff summary."""
    path_arg = arguments.get("path")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise ValueError("path must be a non-empty string")

    target_content = arguments.get("target_content")
    if not isinstance(target_content, str):
        raise ValueError("target_content must be a string")

    replacement_content = arguments.get("replacement_content")
    if not isinstance(replacement_content, str):
        raise ValueError("replacement_content must be a string")

    target = resolve_workspace_path(path_arg, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path_arg}")
    if not target.is_file():
        raise ValueError(f"Path is not a regular file: {path_arg}")

    try:
        with open(target, "r", encoding="utf-8", newline="") as f:
            orig_text = f.read()
    except UnicodeDecodeError:
        raise ValueError(f"Cannot edit binary file: {path_arg}")

    has_crlf = "\r\n" in orig_text

    # Match target text regardless of caller's newline style while preserving file's newline style
    if has_crlf:
        norm_target = target_content.replace("\r\n", "\n").replace("\n", "\r\n")
        norm_replacement = replacement_content.replace("\r\n", "\n").replace("\n", "\r\n")
    else:
        norm_target = target_content.replace("\r\n", "\n")
        norm_replacement = replacement_content.replace("\r\n", "\n")

    count = orig_text.count(norm_target)
    if count == 0 and target_content in orig_text:
        norm_target = target_content
        norm_replacement = replacement_content
        count = orig_text.count(norm_target)

    if count == 0:
        raise ValueError(f"Target content not found in {path_arg}")
    if count > 1:
        raise ValueError(f"Target content matched {count} times in {path_arg}; must match exactly once")

    new_text = orig_text.replace(norm_target, norm_replacement, 1)
    with open(target, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    diff_lines = list(difflib.unified_diff(
        orig_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{path_arg}",
        tofile=f"b/{path_arg}",
    ))
    diff_text = "".join(diff_lines)

    return {
        "path": path_arg,
        "diff": diff_text,
        "message": f"Successfully updated {path_arg}",
    }


def handle_write_file(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Write or append to a file, creating parent directories as needed."""
    path_arg = arguments.get("path")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise ValueError("path must be a non-empty string")

    content = arguments.get("content")
    if not isinstance(content, str):
        raise ValueError("content must be a string")

    overwrite = bool(arguments.get("overwrite", False))
    append = bool(arguments.get("append", False))

    if overwrite and append:
        raise ValueError("Cannot specify both overwrite=True and append=True")

    target = resolve_workspace_path(path_arg, workspace_root)

    if target.exists() and not overwrite and not append:
        raise FileExistsError(
            f"File already exists: {path_arg}. Set overwrite=True to replace or append=True to append."
        )

    target.parent.mkdir(parents=True, exist_ok=True)

    if append and target.exists():
        with open(target, "a", encoding="utf-8", newline="") as f:
            f.write(content)
        action = "appended"
    else:
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        action = "written"

    bytes_written = len(content.encode("utf-8"))
    return {
        "path": path_arg,
        "action": action,
        "bytes_written": bytes_written,
        "message": f"Successfully {action} {bytes_written} bytes to {path_arg}",
    }


def _scrub_environment() -> dict[str, str]:
    sensitive_substrings = (
        "KEY",
        "TOKEN",
        "SECRET",
        "PASSW",
        "AUTH",
        "CREDENTIAL",
        "BEARER",
        "URL",
        "URI",
        "DSN",
        "CONNECTION",
    )
    clean: dict[str, str] = {}
    for k, v in os.environ.items():
        k_upper = k.upper()
        if any(sub in k_upper for sub in sensitive_substrings):
            continue
        clean[k] = v
    return clean


def handle_run_command(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Execute shell command with scrubbed environment and bounded output."""
    command = arguments.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("command must be a non-empty string")

    try:
        timeout_seconds = min(max(1, int(arguments.get("timeout_seconds", 60))), 300)
    except (ValueError, TypeError):
        timeout_seconds = 60

    cwd = str(Path(workspace_root).resolve())
    clean_env = _scrub_environment()

    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        env=clean_env,
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        stdout = stdout or ""
        stderr = stderr or ""
        exit_code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = -1
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                proc.kill()
        else:
            proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=2.0)
            stdout = stdout or ""
            stderr = stderr or ""
        except Exception:
            stdout, stderr = "", ""

    if len(stdout) > MAX_COMMAND_OUTPUT_CHARS:
        stdout = stdout[:MAX_COMMAND_OUTPUT_CHARS] + "\n[Output truncated: stdout exceeded 100000 characters]"
    if len(stderr) > MAX_COMMAND_OUTPUT_CHARS:
        stderr = stderr[:MAX_COMMAND_OUTPUT_CHARS] + "\n[Output truncated: stderr exceeded 100000 characters]"

    combined = stdout + (f"\nSTDERR:\n{stderr}" if stderr else "")

    result: dict[str, Any] = {
        "command": command,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "output": combined.strip(),
        "timed_out": timed_out,
    }
    if timed_out:
        result["error"] = f"Command timed out after {timeout_seconds} seconds"

    return result


_qmd_adapters: dict[str, Any] = {}


def _get_qmd_adapter(workspace_root: str) -> Any:
    """Return a cached QMDAdapter instance for the given workspace root."""
    canonical_root = str(Path(workspace_root).resolve())
    if canonical_root in _qmd_adapters:
        return _qmd_adapters[canonical_root]

    if "harness" not in sys.modules:
        root_path = Path(canonical_root)
        harness_init = root_path / ".harness" / "__init__.py"
        if not harness_init.is_file():
            for parent in root_path.parents:
                cand = parent / ".harness" / "__init__.py"
                if cand.is_file():
                    harness_init = cand
                    break
        if harness_init.is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "harness", harness_init, submodule_search_locations=[str(harness_init.parent)]
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["harness"] = mod
                spec.loader.exec_module(mod)

    try:
        from harness.adapters import QMDAdapter
        from harness.config import QMDAdapterConfig

        adapter = QMDAdapter(QMDAdapterConfig(), repo_root=Path(canonical_root))
        _qmd_adapters[canonical_root] = adapter
        return adapter
    except Exception:
        return None


def handle_qmd_search(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Execute BM25 keyword search across indexed markdown collections via QMDAdapter."""
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    collection = arguments.get("collection")
    limit = int(arguments.get("limit", 5))
    min_score = float(arguments.get("min_score", 0.4))

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {"error": "QMDAdapter is unavailable in this workspace", "query": query, "count": 0, "hits": []}

    try:
        hits = adapter.search(query.strip(), collection=collection, limit=limit, min_score=min_score)
        return {
            "query": query,
            "mode": "bm25",
            "count": len(hits),
            "hits": [
                {
                    "docid": h.docid,
                    "score": h.score,
                    "file": h.file,
                    "line": h.line,
                    "title": h.title,
                    "snippet": h.snippet,
                }
                for h in hits
            ],
        }
    except Exception as exc:
        return {"error": str(exc), "query": query, "count": 0, "hits": []}


def handle_qmd_vsearch(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Execute vector similarity search across indexed markdown collections via QMDAdapter."""
    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    collection = arguments.get("collection")
    limit = int(arguments.get("limit", 5))
    min_score = float(arguments.get("min_score", 0.35))

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {"error": "QMDAdapter is unavailable in this workspace", "query": query, "count": 0, "hits": []}

    try:
        hits = adapter.vsearch(query.strip(), collection=collection, limit=limit, min_score=min_score)
        return {
            "query": query,
            "mode": "vector",
            "count": len(hits),
            "hits": [
                {
                    "docid": h.docid,
                    "score": h.score,
                    "file": h.file,
                    "line": h.line,
                    "title": h.title,
                    "snippet": h.snippet,
                }
                for h in hits
            ],
        }
    except Exception as exc:
        return {"error": str(exc), "query": query, "count": 0, "hits": []}


def handle_qmd_query(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Execute structured or hybrid semantic query via QMDAdapter."""
    prompt = arguments.get("prompt")
    intent = arguments.get("intent")
    lex = arguments.get("lex")
    vec = arguments.get("vec")
    hyde = arguments.get("hyde")
    limit = int(arguments.get("limit", 5))
    min_score = float(arguments.get("min_score", 0.4))
    rerank = bool(arguments.get("rerank", False))

    if not any([prompt, intent, lex, vec, hyde]):
        raise ValueError("Must provide prompt or at least one of (intent, lex, vec, hyde)")

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {"error": "QMDAdapter is unavailable in this workspace", "count": 0, "hits": []}

    try:
        hits = adapter.query(
            prompt=prompt,
            intent=intent,
            lex=lex,
            vec=vec,
            hyde=hyde,
            limit=limit,
            min_score=min_score,
            rerank=rerank,
        )
        return {
            "mode": "hybrid" if prompt else "structured",
            "count": len(hits),
            "hits": [
                {
                    "docid": h.docid,
                    "score": h.score,
                    "file": h.file,
                    "line": h.line,
                    "title": h.title,
                    "snippet": h.snippet,
                }
                for h in hits
            ],
        }
    except Exception as exc:
        return {"error": str(exc), "count": 0, "hits": []}


def handle_qmd_get(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Retrieve full or line-bounded document content by docid or URI via QMDAdapter."""
    target = arguments.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("target must be a non-empty string (docid or file path)")

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {"error": "QMDAdapter is unavailable in this workspace", "target": target}

    try:
        content = adapter.get(target.strip())
        return {"target": target, "content": content}
    except Exception as exc:
        return {"error": str(exc), "target": target}


def handle_qmd_multi_get(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Batch-retrieve multiple documents by docids or glob patterns via QMDAdapter."""
    raw_targets = arguments.get("targets")
    if not raw_targets:
        raise ValueError("targets must be provided as a string or list of strings")

    targets = [t.strip() for t in raw_targets] if isinstance(raw_targets, list) else [str(raw_targets).strip()]
    max_lines = arguments.get("max_lines")
    max_bytes = arguments.get("max_bytes")
    output_format = arguments.get("output_format", "md")

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {"error": "QMDAdapter is unavailable in this workspace", "targets": targets}

    try:
        content = adapter.multi_get(
            targets,
            max_lines=int(max_lines) if max_lines is not None else None,
            max_bytes=int(max_bytes) if max_bytes is not None else None,
            output_format=output_format,
        )
        return {"targets": targets, "format": output_format, "content": content}
    except Exception as exc:
        return {"error": str(exc), "targets": targets}


_ast_grep_adapters: dict[str, Any] = {}


def _get_ast_grep_adapter(workspace_root: str) -> Any | None:
    """Lazily instantiate and cache an AstGrepAdapter for workspace_root."""
    canonical_root = str(Path(workspace_root).resolve())
    if canonical_root in _ast_grep_adapters:
        return _ast_grep_adapters[canonical_root]

    if "harness" not in sys.modules:
        root_path = Path(canonical_root)
        harness_init = root_path / ".harness" / "__init__.py"
        if not harness_init.is_file():
            for parent in root_path.parents:
                cand = parent / ".harness" / "__init__.py"
                if cand.is_file():
                    harness_init = cand
                    break
        if harness_init.is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "harness", harness_init, submodule_search_locations=[str(harness_init.parent)]
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules["harness"] = mod
                spec.loader.exec_module(mod)

    try:
        from harness.adapters import AstGrepAdapter
        from harness.config import AstGrepAdapterConfig

        adapter = AstGrepAdapter(AstGrepAdapterConfig(), repo_root=Path(canonical_root))
        _ast_grep_adapters[canonical_root] = adapter
        return adapter
    except Exception:
        return None


def handle_ast_outline(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Extract structural symbol outline (classes, functions, methods) from a source file via AstGrepAdapter."""
    path_arg = arguments.get("path")
    if not isinstance(path_arg, str) or not path_arg.strip():
        raise ValueError("path must be a non-empty string")

    language = arguments.get("language")
    if language is not None and not isinstance(language, str):
        language = None

    target = resolve_workspace_path(path_arg, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path_arg}")
    if not target.is_file():
        raise ValueError(f"Path is not a regular file: {path_arg}")

    adapter = _get_ast_grep_adapter(workspace_root)
    if adapter is None:
        return {"error": "AstGrepAdapter is unavailable in this workspace", "path": path_arg, "count": 0, "symbols": []}
    if not adapter.is_available():
        return {"error": "ast-grep CLI binary not found or unavailable on host", "path": path_arg, "count": 0, "symbols": []}

    try:
        symbols = adapter.outline(target, language=language)
        return {
            "path": path_arg,
            "count": len(symbols),
            "symbols": [
                {
                    "name": s.name,
                    "kind": s.kind,
                    "line": s.line,
                    "column": s.column,
                    "context": s.context,
                }
                for s in symbols
            ],
        }
    except Exception as exc:
        return {"error": str(exc), "path": path_arg, "count": 0, "symbols": []}


def handle_qmd_status(arguments: dict[str, Any], workspace_root: str) -> dict[str, Any]:
    """Inspect QMD index status, collections, and database metrics."""
    root_path = Path(workspace_root).resolve()
    user_home = Path.home()
    local_app_data = os.environ.get("LOCALAPPDATA") or str(user_home / "AppData" / "Local")
    xdg_cache = os.environ.get("XDG_CACHE_HOME") or str(user_home / ".cache")
    db_candidates = [
        root_path / ".qmd" / "index.sqlite",
        Path(xdg_cache) / "qmd" / "index.sqlite",
        user_home / ".cache" / "qmd" / "index.sqlite",
        Path(local_app_data) / "qmd" / "index.sqlite",
    ]
    db_info = {"exists": False, "path": "", "size_bytes": 0}
    for cand in db_candidates:
        if cand.is_file():
            db_info = {"exists": True, "path": str(cand), "size_bytes": cand.stat().st_size}
            break

    adapter = _get_qmd_adapter(workspace_root)
    if adapter is None:
        return {
            "available": False,
            "status": "unavailable",
            "collection_count": 0,
            "collections": [],
            "database": db_info,
            "error": "QMDAdapter is unavailable in this workspace",
        }

    try:
        colls = adapter.list_collections()
        avail = adapter.is_available()
        return {
            "available": avail,
            "status": "healthy" if (avail and colls) else "uninitialized",
            "collection_count": len(colls),
            "collections": colls,
            "database": db_info,
        }
    except Exception as exc:
        return {
            "available": False,
            "status": "error",
            "collection_count": 0,
            "collections": [],
            "database": db_info,
            "error": str(exc),
        }


READ_FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to file to read (relative to workspace root)",
        },
        "start_line": {
            "type": "integer",
            "minimum": 1,
            "description": "Optional 1-indexed start line (inclusive)",
        },
        "end_line": {
            "type": "integer",
            "minimum": 1,
            "description": "Optional 1-indexed end line (inclusive)",
        },
    },
    "required": ["path"],
}

LIST_DIR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Directory path relative to workspace root (default: '.')",
        },
        "depth": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Maximum directory depth to recurse (default: 1, max: 10)",
        },
        "include_hidden": {
            "type": "boolean",
            "description": "Include hidden files and directories starting with '.' (default: False)",
        },
    },
}

GREP_SEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Regex or substring pattern to search for",
        },
        "path": {
            "type": "string",
            "description": "Subdirectory or file path to search within (default: '.')",
        },
        "glob": {
            "type": "string",
            "description": "Optional file glob filter (e.g. '*.py')",
        },
    },
    "required": ["pattern"],
}

EDIT_FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to file to edit (relative to workspace root)",
        },
        "target_content": {
            "type": "string",
            "description": "Exact text chunk to replace (must match uniquely)",
        },
        "replacement_content": {
            "type": "string",
            "description": "Replacement text chunk",
        },
    },
    "required": ["path", "target_content", "replacement_content"],
}

WRITE_FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Path to file to write (relative to workspace root)",
        },
        "content": {
            "type": "string",
            "description": "Content to write",
        },
        "overwrite": {
            "type": "boolean",
            "description": "Overwrite existing file if true (default: False)",
        },
        "append": {
            "type": "boolean",
            "description": "Append to existing file if true (default: False)",
        },
    },
    "required": ["path", "content"],
}

RUN_COMMAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Shell command to execute",
        },
        "timeout_seconds": {
            "type": "integer",
            "minimum": 1,
            "maximum": 300,
            "description": "Timeout in seconds (default: 60, max: 300)",
        },
    },
    "required": ["command"],
}

ASK_QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "Question to prompt the user with",
        },
        "options": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Selectable options list",
        },
        "is_multi_select": {
            "type": "boolean",
            "description": "Allow selecting multiple choices",
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "is_multi_select": {"type": "boolean"},
                },
                "required": ["question", "options"],
            },
            "description": "Optional batch of questions",
        },
    },
}


QMD_SEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "BM25 keyword search string (e.g. 'worktree isolation', 'headroom compression')",
        },
        "collection": {
            "type": "string",
            "description": "Optional collection filter (e.g. 'docs', 'ai-tooling', 'supporting', 'routing', 'research')",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "description": "Maximum number of results to return (default: 5)",
        },
        "min_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Minimum similarity score threshold (default: 0.4)",
        },
    },
    "required": ["query"],
}

QMD_VSEARCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Vector semantic search query (conceptual or paraphrased search)",
        },
        "collection": {
            "type": "string",
            "description": "Optional collection filter",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "description": "Maximum results to return (default: 5)",
        },
        "min_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Minimum similarity score threshold (default: 0.35)",
        },
    },
    "required": ["query"],
}

QMD_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Natural language query for hybrid expansion search",
        },
        "intent": {
            "type": "string",
            "description": "Intent description line for typed query document",
        },
        "lex": {
            "type": "string",
            "description": "Exact lexical tokens for typed query document",
        },
        "vec": {
            "type": "string",
            "description": "Semantic concepts for typed query document",
        },
        "hyde": {
            "type": "string",
            "description": "Hypothetical document snippet for typed query document",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "description": "Maximum results (default: 5)",
        },
        "min_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Minimum similarity score (default: 0.4)",
        },
        "rerank": {
            "type": "boolean",
            "description": "Enable LLM reranking (default: False for fast response)",
        },
    },
}

QMD_GET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target": {
            "type": "string",
            "description": "Docid (e.g. '#368c47') or file path (e.g. 'supporting/qmd/query-pattern.md')",
        },
    },
    "required": ["target"],
}

QMD_MULTI_GET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "targets": {
            "type": "string",
            "description": "Comma-separated list of docids, file paths, or glob patterns to batch fetch (e.g. 'doc1,doc2' or 'supporting/qmd/*.md')",
        },
        "max_lines": {
            "type": "integer",
            "minimum": 1,
            "description": "Maximum lines per file to retrieve",
        },
        "max_bytes": {
            "type": "integer",
            "minimum": 1,
            "description": "Maximum bytes per file",
        },
        "output_format": {
            "type": "string",
            "description": "Output format: md (default) or json",
        },
    },
    "required": ["targets"],
}


AST_OUTLINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Relative workspace file path to extract code symbol outline from (e.g. 'scripts/cli/harness.py')",
        },
        "language": {
            "type": "string",
            "description": "Optional programming language identifier (e.g. 'python', 'javascript', 'typescript', 'go', 'rust')",
        },
    },
    "required": ["path"],
}

QMD_STATUS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
}


def build_workspace_tool_registry(
    workspace_root: str,
    is_interactive: bool = True,
    input_fn: Callable[[str], str] | None = None,
) -> ToolRegistry:
    """Build and populate a ToolRegistry with default workspace coding tools."""
    registry = ToolRegistry()

    registry.register(
        "read_file",
        "Read file contents within the workspace, optionally bounded by line numbers.",
        READ_FILE_SCHEMA,
        lambda args: handle_read_file(args, workspace_root),
    )
    registry.register(
        "list_dir",
        "List files and directories within the workspace up to a maximum recursion depth.",
        LIST_DIR_SCHEMA,
        lambda args: handle_list_dir(args, workspace_root),
    )
    registry.register(
        "grep_search",
        "Search file contents in the workspace using regex or substring matching. Note: For discovering Markdown documentation across repository areas (docs, skills, supporting, research, etc.), prefer qmd_search or qmd_vsearch.",
        GREP_SEARCH_SCHEMA,
        lambda args: handle_grep_search(args, workspace_root),
    )
    registry.register(
        "edit_file",
        "Perform a single contiguous text replacement in a workspace file.",
        EDIT_FILE_SCHEMA,
        lambda args: handle_edit_file(args, workspace_root),
    )
    registry.register(
        "write_file",
        "Create or update a workspace file with specified content.",
        WRITE_FILE_SCHEMA,
        lambda args: handle_write_file(args, workspace_root),
    )
    registry.register(
        "run_command",
        "Execute a shell command with scrubbed environment and bounded output.",
        RUN_COMMAND_SCHEMA,
        lambda args: handle_run_command(args, workspace_root),
    )
    registry.register(
        "ask_question",
        "Prompt the user with an interactive multiple-choice question.",
        ASK_QUESTION_SCHEMA,
        lambda args: handle_ask_question(args, input_fn=input_fn or input, is_interactive=is_interactive),
    )
    registry.register(
        "qmd_search",
        "Search indexed Markdown documentation using BM25 keyword search across collections (docs, skills, supporting, routing, research). Automatically queries against the clean, synced origin/main index snapshot.",
        QMD_SEARCH_SCHEMA,
        lambda args: handle_qmd_search(args, workspace_root),
    )
    registry.register(
        "qmd_vsearch",
        "Search indexed Markdown documentation using vector semantic similarity (embeddings). Ideal for conceptual or paraphrased searches.",
        QMD_VSEARCH_SCHEMA,
        lambda args: handle_qmd_vsearch(args, workspace_root),
    )
    registry.register(
        "qmd_query",
        "Execute hybrid semantic query with auto-expansion, or structured query document (intent:, lex:, vec:, hyde:).",
        QMD_QUERY_SCHEMA,
        lambda args: handle_qmd_query(args, workspace_root),
    )
    registry.register(
        "qmd_get",
        "Retrieve document content by docid (#docid) or file path.",
        QMD_GET_SCHEMA,
        lambda args: handle_qmd_get(args, workspace_root),
    )
    registry.register(
        "qmd_multi_get",
        "Batch-retrieve multiple documents simultaneously by docids or glob patterns (~5x faster than sequential fetches).",
        QMD_MULTI_GET_SCHEMA,
        lambda args: handle_qmd_multi_get(args, workspace_root),
    )
    registry.register(
        "ast_outline",
        "Extract code symbol outline (classes, functions, methods, line numbers) from a source file using ast-grep. Always prefer this over dumping full files to preserve context window.",
        AST_OUTLINE_SCHEMA,
        lambda args: handle_ast_outline(args, workspace_root),
    )
    registry.register(
        "qmd_status",
        "Inspect local QMD index health, collections, and database freshness.",
        QMD_STATUS_SCHEMA,
        lambda args: handle_qmd_status(args, workspace_root),
    )

    return registry
