"""Bounded stdio MCP client support for ACP-provided tool servers.

tags: [harness, cli, mcp, acp, stdio, tools]
routing_hints: [harness, mcp, acp, tool-registry, subprocess]
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli.tool_registry import ToolOutcome, ToolRegistry

MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"
SUPPORTED_LEGACY_VERSIONS = {
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
}
MCP_CLIENT_INFO = {"name": "Harness", "version": "0.15.0"}
MCP_META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
MCP_META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
MCP_META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"

MCP_MAX_SERVERS = 32
MCP_MAX_ARGS = 128
MCP_MAX_ARG_LENGTH = 8192
MCP_MAX_ENV_VARS = 128
MCP_MAX_ENV_VALUE_LENGTH = 32768
MCP_MAX_ENV_TOTAL_LENGTH = 131072
MCP_MAX_STDIO_MESSAGE_BYTES = 1_048_576
MCP_MAX_PENDING_MESSAGES = 128
MCP_MAX_TOOLS_PER_SERVER = 256
MCP_MAX_TOOLS_TOTAL = 512
MCP_MAX_SCHEMA_BYTES = 131072
MCP_DISCOVERY_TIMEOUT_SEC = 2.0
MCP_REQUEST_TIMEOUT_SEC = 10.0
MCP_SHUTDOWN_GRACE_SEC = 0.5
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TOOL_ALIAS_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
_STOP = object()


class MCPStdioError(RuntimeError):
    """An MCP stdio server or message did not meet the supported profile."""


class MCPRequestCancelled(MCPStdioError):
    """An in-flight MCP call was cancelled by its ACP session."""


class _JSONRPCError(MCPStdioError):
    def __init__(self, code: Any, message: Any, data: Any = None) -> None:
        super().__init__(str(message)[:500] if message is not None else "MCP request failed")
        self.code = code
        self.data = data


class _RequestTimeout(MCPStdioError):
    pass


def validate_mcp_servers(value: Any) -> list[dict[str, Any]]:
    """Validate the ACP stdio configuration subset before spawning processes."""
    if not isinstance(value, list) or len(value) > MCP_MAX_SERVERS:
        raise ValueError(f"mcpServers must be an array of at most {MCP_MAX_SERVERS} entries")
    validated: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"mcpServers[{index}] must be an object")
        name = raw.get("name")
        command = raw.get("command")
        args = raw.get("args", [])
        env = raw.get("env", [])
        transport = raw.get("type")
        if transport not in (None, "stdio"):
            raise ValueError("only ACP stdio MCP servers are supported")
        if not isinstance(name, str) or not name.strip() or len(name) > 128:
            raise ValueError(f"mcpServers[{index}].name must be a non-empty string of at most 128 characters")
        if (
            not isinstance(command, str)
            or not command
            or "\0" in command
            or len(command) > 4096
            or not os.path.isabs(command)
        ):
            raise ValueError(f"mcpServers[{index}].command must be an absolute executable path")
        if not isinstance(args, list) or len(args) > MCP_MAX_ARGS or any(
            not isinstance(arg, str) or len(arg) > MCP_MAX_ARG_LENGTH or "\0" in arg for arg in args
        ):
            raise ValueError(f"mcpServers[{index}].args must be an array of bounded strings")
        if not isinstance(env, list) or len(env) > MCP_MAX_ENV_VARS:
            raise ValueError(f"mcpServers[{index}].env must be an array of at most {MCP_MAX_ENV_VARS} entries")
        env_values: dict[str, str] = {}
        env_total = 0
        for env_index, item in enumerate(env):
            if not isinstance(item, dict):
                raise ValueError(f"mcpServers[{index}].env[{env_index}] must be an object")
            key, item_value = item.get("name"), item.get("value")
            if (
                not isinstance(key, str)
                or not _ENV_NAME.fullmatch(key)
                or not isinstance(item_value, str)
                or "\0" in item_value
                or len(item_value) > MCP_MAX_ENV_VALUE_LENGTH
            ):
                raise ValueError(f"mcpServers[{index}].env[{env_index}] has an invalid name or value")
            if key in env_values:
                raise ValueError(f"mcpServers[{index}].env contains a duplicate variable")
            env_values[key] = item_value
            env_total += len(key) + len(item_value)
        if env_total > MCP_MAX_ENV_TOTAL_LENGTH:
            raise ValueError(f"mcpServers[{index}].env exceeds the size limit")
        validated.append({"name": name, "command": command, "args": list(args), "env": env_values})
    return validated


def discover_mcp_config(
    workspace_root: str | Path | None = None,
    explicit_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Discover and parse MCP server configurations according to priority rules.

    Priority:
    1. Explicit path (e.g. from --mcp-config)
    2. <workspace_root>/.mcp.json (or repo root / cwd)
    3. ~/.harness/mcp.json

    Supports:
    - {"mcpServers": {...}} (standard Claude/Cursor format)
    - {"servers": {...}}
    - Direct server map ({<name>: {...}})
    """
    target: Path | None = None
    if explicit_path:
        candidate = Path(explicit_path).expanduser().resolve()
        if candidate.is_file():
            target = candidate
        else:
            return {}
    else:
        root: Path
        if workspace_root is not None:
            root = Path(workspace_root).expanduser().resolve()
        else:
            try:
                from paths import resolve_repo_root

                root = resolve_repo_root()
            except ImportError:
                root = Path.cwd().resolve()
        if (root / ".mcp.json").is_file():
            target = root / ".mcp.json"
        elif Path.cwd().resolve() != root and (Path.cwd().resolve() / ".mcp.json").is_file():
            target = Path.cwd().resolve() / ".mcp.json"
        elif (Path.home() / ".harness" / "mcp.json").is_file():
            target = Path.home() / ".harness" / "mcp.json"

    if target is None:
        return {}

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"warning: failed to parse MCP config '{target}': {exc}", file=sys.stderr)
        return {}
    except OSError as exc:
        print(f"warning: failed to read MCP config '{target}': {exc}", file=sys.stderr)
        return {}

    if not isinstance(data, dict):
        print(f"warning: MCP config '{target}' is not a JSON object", file=sys.stderr)
        return {}

    raw: Any = None
    if "mcpServers" in data:
        raw = data["mcpServers"]
    elif "servers" in data:
        raw = data["servers"]
    elif all(isinstance(v, dict) for v in data.values()) and data:
        raw = data

    result: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict):
                cfg = dict(v)
                cfg.setdefault("name", str(k))
                result[str(k)] = cfg
    elif isinstance(raw, list):
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                name = str(item.get("name") or f"server_{idx}")
                cfg = dict(item)
                cfg.setdefault("name", name)
                result[name] = cfg

    return result


def _process_environment(extra: dict[str, str]) -> dict[str, str]:
    """Pass only platform essentials plus explicitly configured server values."""
    inherited = os.environ
    allowlisted = ["SystemRoot", "WINDIR", "TEMP", "TMP", "PATH"]
    if sys.platform == "win32":
        allowlisted.append("PATHEXT")
    environment = {key: inherited[key] for key in allowlisted if key in inherited}
    environment.update(extra)
    return environment


def _resolve_safe_command(cmd: str, cwd: str) -> str:
    """Resolve an MCP command safely, preventing CWE-426 binary planting."""
    if not isinstance(cmd, str) or not cmd.strip():
        raise MCPStdioError("MCP server command must be a non-empty string")
    cmd = cmd.strip()

    cwd_path = Path(cwd).resolve()
    workspace_root: Path | None = None
    try:
        from paths import resolve_repo_root

        workspace_root = resolve_repo_root().resolve()
    except Exception:
        workspace_root = None

    if os.path.isabs(cmd):
        resolved = shutil.which(cmd) or (cmd if (os.path.isfile(cmd) and os.access(cmd, os.X_OK)) else None)
        if not resolved or not os.path.isfile(resolved):
            raise MCPStdioError(f"Command '{cmd}' does not exist or is not executable")
        resolved_path = Path(resolved).resolve()
    else:
        # Reject relative paths with path separators (e.g. ./foo, bar/baz, .\foo)
        if os.path.dirname(cmd):
            raise MCPStdioError(f"Relative command path '{cmd}' with directory separators is not permitted")

        # Filter system PATH directories to absolute paths only and exclude cwd and workspace_root
        raw_path = os.environ.get("PATH", "")
        clean_dirs: list[str] = []
        for d in raw_path.split(os.pathsep):
            d = d.strip()
            if not d or not os.path.isabs(d):
                continue
            try:
                dp = Path(d).resolve()
            except (OSError, RuntimeError):
                continue
            if dp == cwd_path or dp.is_relative_to(cwd_path):
                continue
            if workspace_root is not None and (dp == workspace_root or dp.is_relative_to(workspace_root)):
                continue
            clean_dirs.append(str(dp))

        clean_path = os.pathsep.join(clean_dirs)

        # On Windows, shutil.which() prepends os.curdir to path. Search clean_dirs directly.
        resolved: str | None = None
        if sys.platform == "win32":
            pathext_source = os.getenv("PATHEXT") or ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC"
            pathext = [ext for ext in pathext_source.split(os.pathsep) if ext]
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                candidate_names = [cmd]
            else:
                candidate_names = [cmd + ext for ext in pathext]

            for d in clean_dirs:
                for name in candidate_names:
                    candidate_file = os.path.join(d, name)
                    if os.path.isfile(candidate_file) and os.access(candidate_file, os.X_OK):
                        resolved = candidate_file
                        break
                if resolved:
                    break
        else:
            resolved = shutil.which(cmd, path=clean_path)

        if not resolved:
            raise MCPStdioError(f"Command '{cmd}' could not be safely resolved from system PATH")
        resolved_path = Path(resolved).resolve()

    # Verify resolved executable does NOT reside inside cwd or workspace root
    if resolved_path == cwd_path or resolved_path.is_relative_to(cwd_path):
        raise MCPStdioError(f"Refusing to execute command residing inside working directory: {resolved_path}")
    if workspace_root is not None and (resolved_path == workspace_root or resolved_path.is_relative_to(workspace_root)):
        raise MCPStdioError(f"Refusing to execute command residing inside workspace root: {resolved_path}")

    return str(resolved_path)


class MCPStdioClient:
    """A synchronous JSON-RPC client for one ACP stdio server configuration."""

    def __init__(self, config: dict[str, Any], *, cwd: str) -> None:
        self.config = config
        self.cwd = cwd
        self.name = config["name"]
        self._proc: subprocess.Popen[bytes] | None = None
        self._reader: threading.Thread | None = None
        self._messages: queue.Queue[Any] = queue.Queue(maxsize=MCP_MAX_PENDING_MESSAGES)
        self._write_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._active_lock = threading.Lock()
        self._active_ids: set[int] = set()
        self._active_versions: dict[int, str] = {}
        self._cancelled_ids: set[int] = set()
        self._next_id = 0
        self._closing = threading.Event()
        self.protocol_version = ""
        self.modern = False
        self.capabilities: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []
        try:
            self._spawn()
            self._negotiate()
            self.refresh_tools()
        except BaseException:
            self.close()
            raise

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None

    @property
    def returncode(self) -> int | None:
        return self._proc.poll() if self._proc is not None else None

    def _spawn(self) -> None:
        self._closing.clear()
        self._messages = queue.Queue(maxsize=MCP_MAX_PENDING_MESSAGES)
        cmd = self.config["command"]
        resolved_cmd = _resolve_safe_command(cmd, cwd=self.cwd)
        try:
            self._proc = subprocess.Popen(
                [resolved_cmd, *self.config["args"]],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.cwd,
                env=_process_environment(self.config["env"]),
                shell=False,
                close_fds=True,
                bufsize=0,
            )
        except OSError:
            raise MCPStdioError("MCP server process could not be started") from None
        assert self._proc.stdout is not None
        self._reader = threading.Thread(target=self._read_stdout, name="mcp-stdio-reader", daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            while not self._closing.is_set():
                raw = self._proc.stdout.readline(MCP_MAX_STDIO_MESSAGE_BYTES + 2)
                if not raw:
                    break
                if len(raw) > MCP_MAX_STDIO_MESSAGE_BYTES or not raw.endswith(b"\n"):
                    self._put_message(MCPStdioError("MCP server output exceeded the message limit"))
                    break
                try:
                    value = json.loads(raw[:-1].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._put_message(MCPStdioError("MCP server emitted invalid UTF-8 JSON-RPC output"))
                    break
                if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                    self._put_message(MCPStdioError("MCP server emitted an invalid JSON-RPC message"))
                    break
                if isinstance(value.get("method"), str):
                    if "id" in value:
                        if self.modern:
                            self._put_message(MCPStdioError("modern MCP servers must not send client-directed requests"))
                            break
                        self._write({
                            "jsonrpc": "2.0",
                            "id": value["id"],
                            "error": {"code": -32601, "message": "method not found"},
                        })
                    # Notifications are not needed by this profile.
                    continue
                self._put_message(value)
        except (OSError, ValueError):
            if not self._closing.is_set():
                self._put_message(MCPStdioError("MCP server output could not be read"))
        finally:
            self._put_message(_STOP)

    def _put_message(self, value: Any) -> None:
        deadline = time.monotonic() + 1.0
        while not self._closing.is_set() and time.monotonic() < deadline:
            try:
                self._messages.put(value, timeout=0.1)
                return
            except queue.Full:
                continue

    def _write(self, message: dict[str, Any]) -> None:
        proc = self._proc
        if proc is None or proc.poll() is not None or proc.stdin is None:
            raise MCPStdioError("MCP server process is not running")
        try:
            encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            raw = (encoded + "\n").encode("utf-8")
            if len(raw) > MCP_MAX_STDIO_MESSAGE_BYTES:
                raise MCPStdioError("MCP request exceeded the message limit")
            with self._write_lock:
                proc.stdin.write(raw)
                proc.stdin.flush()
        except (OSError, UnicodeEncodeError, ValueError, BrokenPipeError) as exc:
            if isinstance(exc, MCPStdioError):
                raise
            raise MCPStdioError("MCP request could not be written") from None

    def _metadata(self, version: str) -> dict[str, Any]:
        return {
            MCP_META_PROTOCOL_VERSION: version,
            MCP_META_CLIENT_INFO: MCP_CLIENT_INFO,
            MCP_META_CLIENT_CAPABILITIES: {},
        }

    def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        version: str,
        timeout: float = MCP_REQUEST_TIMEOUT_SEC,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        with self._request_lock:
            self._next_id += 1
            request_id = self._next_id
            request_params = dict(params or {})
            if version == MODERN_VERSION:
                request_params.setdefault("_meta", self._metadata(version))
            request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": request_params}
            with self._active_lock:
                self._active_ids.add(request_id)
                self._active_versions[request_id] = version
            try:
                self._write(request)
                deadline = time.monotonic() + timeout
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        self._send_cancelled_once(request_id, version=version)
                        raise MCPRequestCancelled("MCP tool call was cancelled")
                    if self._closing.is_set():
                        raise MCPStdioError("MCP server process was closed")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._send_cancelled_once(request_id, version=version)
                        raise _RequestTimeout(f"MCP request '{method}' timed out")
                    try:
                        message = self._messages.get(timeout=min(0.1, remaining))
                    except queue.Empty:
                        continue
                    if message is _STOP:
                        raise MCPStdioError("MCP server closed its output stream")
                    if isinstance(message, BaseException):
                        raise message
                    if message.get("id") != request_id:
                        continue
                    if "error" in message:
                        error = message.get("error")
                        if not isinstance(error, dict) or not isinstance(error.get("code"), int):
                            raise MCPStdioError("MCP server returned an invalid JSON-RPC error")
                        raise _JSONRPCError(error["code"], error.get("message"), error.get("data"))
                    result = message.get("result")
                    if not isinstance(result, dict):
                        raise MCPStdioError("MCP server returned an invalid result")
                    return result
            finally:
                with self._active_lock:
                    self._active_ids.discard(request_id)
                    self._active_versions.pop(request_id, None)
                    self._cancelled_ids.discard(request_id)

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        request_params = dict(params or {})
        if self.protocol_version == MODERN_VERSION:
            request_params.setdefault("_meta", self._metadata(self.protocol_version))
        if request_params:
            payload["params"] = request_params
        self._write(payload)

    def _send_cancelled(self, request_id: int, *, version: str | None = None) -> None:
        try:
            params: dict[str, Any] = {"requestId": request_id}
            if version == MODERN_VERSION:
                params["_meta"] = self._metadata(version)
            elif version in SUPPORTED_LEGACY_VERSIONS:
                # Legacy protocol request metadata is connection-scoped; cancel
                # notifications carry only the ID of the request being cancelled.
                pass
            self._notify("notifications/cancelled", params)
        except MCPStdioError:
            pass

    def _send_cancelled_once(self, request_id: int, *, version: str | None = None) -> None:
        with self._active_lock:
            if request_id not in self._active_ids or request_id in self._cancelled_ids:
                return
            self._cancelled_ids.add(request_id)
            version = version or self._active_versions.get(request_id)
        self._send_cancelled(request_id, version=version)

    def _negotiate(self) -> None:
        try:
            discovered = self._request(
                "server/discover",
                version=MODERN_VERSION,
                timeout=MCP_DISCOVERY_TIMEOUT_SEC,
            )
        except _JSONRPCError as exc:
            if exc.code == -32022:
                supported = exc.data.get("supported") if isinstance(exc.data, dict) else None
                if not isinstance(supported, list):
                    raise MCPStdioError("MCP server supports no compatible modern protocol version") from None
                if MODERN_VERSION in supported:
                    # Retry modern discovery once when the server advertises
                    # the version despite rejecting the first discovery request.
                    discovered = self._request("server/discover", version=MODERN_VERSION)
                else:
                    legacy_versions = [
                        candidate
                        for candidate in supported
                        if isinstance(candidate, str) and candidate in SUPPORTED_LEGACY_VERSIONS
                    ]
                    if not legacy_versions:
                        raise MCPStdioError(
                            "MCP server supports no compatible modern protocol version"
                        ) from None
                    # Legacy-only errors get one fresh-process initialize handshake.
                    self._restart_for_legacy(version=max(legacy_versions))
                    return
            else:
                self._restart_for_legacy()
                return
        except (MCPStdioError, _RequestTimeout):
            self._restart_for_legacy()
            return

        versions = discovered.get("supportedVersions")
        if discovered.get("resultType") != "complete" or not isinstance(versions, list):
            raise MCPStdioError("MCP server returned an invalid server/discover result")
        if MODERN_VERSION in versions:
            self.protocol_version = MODERN_VERSION
            self.modern = True
            self.capabilities = discovered.get("capabilities") if isinstance(discovered.get("capabilities"), dict) else {}
            return
        raise MCPStdioError("MCP server supports no compatible modern protocol version")

    def _restart_for_legacy(self, *, version: str = LEGACY_VERSION) -> None:
        self.close()
        self._spawn()
        result = self._request(
            "initialize",
            {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": MCP_CLIENT_INFO,
            },
            version="legacy-initialize",
        )
        negotiated = result.get("protocolVersion")
        if negotiated not in SUPPORTED_LEGACY_VERSIONS:
            raise MCPStdioError("MCP server negotiated an unsupported legacy version")
        self.protocol_version = negotiated
        self.modern = False
        self.capabilities = result.get("capabilities") if isinstance(result.get("capabilities"), dict) else {}
        self._notify("notifications/initialized")

    def refresh_tools(self, *, cancel_event: threading.Event | None = None) -> list[dict[str, Any]]:
        if not isinstance(self.capabilities, dict) or not isinstance(self.capabilities.get("tools"), dict):
            self.tools = []
            return []
        cursor: str | None = None
        visited: set[str] = set()
        tools: list[dict[str, Any]] = []
        for _page in range(64):
            params: dict[str, Any] = {}
            if cursor is not None:
                params["cursor"] = cursor
            result = self._request(
                "tools/list", params, version=self.protocol_version, cancel_event=cancel_event
            )
            result_type = result.get("resultType")
            if self.modern and result_type != "complete":
                raise MCPStdioError("MCP tools/list returned an unsupported result type")
            if result_type not in (None, "complete"):
                raise MCPStdioError("MCP tools/list returned an unsupported result type")
            page = result.get("tools")
            if not isinstance(page, list):
                raise MCPStdioError("MCP tools/list did not return a tools array")
            for item in page:
                if not isinstance(item, dict):
                    raise MCPStdioError("MCP tools/list returned an invalid tool")
                name = item.get("name")
                schema = item.get("inputSchema")
                if (
                    not isinstance(name, str)
                    or not name
                    or len(name) > 128
                    or not isinstance(schema, dict)
                ):
                    raise MCPStdioError("MCP tools/list returned an invalid tool name or schema")
                try:
                    serialized_schema = json.dumps(schema, ensure_ascii=False, allow_nan=False)
                except (TypeError, ValueError):
                    raise MCPStdioError("MCP tool schema is not JSON-compatible") from None
                if len(serialized_schema.encode("utf-8")) > MCP_MAX_SCHEMA_BYTES:
                    raise MCPStdioError("MCP tool schema exceeded the size limit")
                tools.append(item)
                if len(tools) > MCP_MAX_TOOLS_PER_SERVER:
                    raise MCPStdioError("MCP server exposed too many tools")
            next_cursor = result.get("nextCursor")
            if next_cursor is None:
                break
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in visited:
                raise MCPStdioError("MCP tools/list returned an invalid pagination cursor")
            visited.add(next_cursor)
            cursor = next_cursor
        else:
            raise MCPStdioError("MCP tools/list exceeded the pagination limit")
        self.tools = tools
        return list(tools)

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        cancel_event: threading.Event | None = None,
    ) -> ToolOutcome:
        try:
            result = self._request(
                "tools/call",
                {"name": name, "arguments": arguments},
                version=self.protocol_version,
                cancel_event=cancel_event,
            )
        except MCPRequestCancelled as exc:
            return ToolOutcome(error=str(exc))
        except _RequestTimeout as exc:
            return ToolOutcome(error=str(exc))
        except _JSONRPCError as exc:
            return ToolOutcome(error=f"MCP server error ({exc.code}): {exc}")
        except MCPStdioError as exc:
            return ToolOutcome(error=f"MCP server error: {exc}")
        result_type = result.get("resultType")
        if self.modern and result_type != "complete":
            return ToolOutcome(error="MCP server returned an invalid modern tool result")
        if result_type not in (None, "complete"):
            return ToolOutcome(error=f"MCP server returned unsupported result type '{result_type}'")
        if result.get("isError") is True:
            try:
                detail = json.dumps(result, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError):
                detail = "tool execution failed"
            return ToolOutcome(error=f"MCP tool returned an error: {detail[:4000]}")
        return ToolOutcome(result=result)

    def cancel_active_requests(self) -> None:
        with self._active_lock:
            requests = [(request_id, self._active_versions.get(request_id)) for request_id in self._active_ids]
        for request_id, version in requests:
            self._send_cancelled_once(request_id, version=version)

    def close(self) -> None:
        proc = self._proc
        self._closing.set()
        if proc is None:
            return
        if proc.stdin is not None:
            try:
                proc.stdin.close()
            except (OSError, ValueError):
                pass
        try:
            proc.wait(timeout=MCP_SHUTDOWN_GRACE_SEC)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except OSError:
                    try:
                        proc.kill()
                    except OSError:
                        pass
            else:
                try:
                    proc.terminate()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=MCP_SHUTDOWN_GRACE_SEC)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except OSError:
                        pass
            try:
                proc.wait(timeout=MCP_SHUTDOWN_GRACE_SEC)
            except subprocess.TimeoutExpired:
                pass
        reader = self._reader
        if reader is not None and reader.is_alive():
            reader.join(timeout=MCP_SHUTDOWN_GRACE_SEC)
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except (OSError, ValueError):
                pass
        self._put_message(_STOP)


@dataclass(frozen=True)
class _ExposedTool:
    alias: str
    client: MCPStdioClient
    source_name: str
    description: str
    input_schema: dict[str, Any]


class ACPSessionMCP:
    """Own server subprocesses and provider tools for one active ACP session."""

    def __init__(self, configs: list[dict[str, Any]] | dict[str, dict[str, Any]], *, cwd: str) -> None:
        self.cwd = cwd
        self._lock = threading.RLock()
        self._clients: list[MCPStdioClient] = []
        self._exposed: dict[str, _ExposedTool] = {}
        self._ended = False
        self.configs = self._normalize_configs(configs)
        self._start()

    @staticmethod
    def _normalize_configs(configs: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        if isinstance(configs, dict):
            for name, item in configs.items():
                if isinstance(item, dict):
                    cfg = dict(item)
                    cfg.setdefault("name", str(name))
                    cfg.setdefault("args", [])
                    env = cfg.get("env")
                    if isinstance(env, dict):
                        cfg["env"] = {str(k): str(v) for k, v in env.items()}
                    elif isinstance(env, list):
                        cfg["env"] = {
                            str(x["name"]): str(x["value"])
                            for x in env
                            if isinstance(x, dict) and "name" in x and "value" in x
                        }
                    else:
                        cfg["env"] = {}
                    normalized.append(cfg)
        elif isinstance(configs, list):
            for item in configs:
                if isinstance(item, dict):
                    cfg = dict(item)
                    cfg.setdefault("args", [])
                    env = cfg.get("env")
                    if isinstance(env, dict):
                        cfg["env"] = {str(k): str(v) for k, v in env.items()}
                    elif isinstance(env, list):
                        cfg["env"] = {
                            str(x["name"]): str(x["value"])
                            for x in env
                            if isinstance(x, dict) and "name" in x and "value" in x
                        }
                    else:
                        cfg["env"] = {}
                    normalized.append(cfg)
        return normalized

    def _start(self) -> None:
        clients: list[MCPStdioClient] = []
        try:
            for config in self.configs:
                clients.append(MCPStdioClient(config, cwd=self.cwd))
        except BaseException:
            for client in clients:
                client.close()
            raise
        self._clients = clients

    def tool_registry(self, base: ToolRegistry, cancel_event: threading.Event | None = None) -> Any:
        with self._lock:
            if self._ended:
                raise MCPStdioError("ACP session is closed")
            if any(client.returncode is not None for client in self._clients):
                self._close_processes()
            if not self._clients and self.configs:
                self._start()
            cancel = cancel_event if cancel_event is not None else threading.Event()
            exposed: dict[str, _ExposedTool] = {}
            for server_index, client in enumerate(self._clients):
                for tool_index, tool in enumerate(client.refresh_tools(cancel_event=cancel)):
                    source_name = tool["name"]
                    safe_tool_name = _TOOL_ALIAS_CHARS.sub("_", source_name).strip("_-") or "tool"
                    alias = f"mcp{server_index}_{tool_index}_{safe_tool_name}"[:64]
                    if alias in exposed or any(item.name == alias for item in base.definitions):
                        raise MCPStdioError("MCP tool names collide after provider-safe namespacing")
                    description = tool.get("description", "")
                    if not isinstance(description, str):
                        description = ""
                    prefix = f"MCP server {client.name!r} tool {source_name!r}"
                    full_description = f"{prefix}: {description}" if description else prefix
                    exposed[alias] = _ExposedTool(alias, client, source_name, full_description[:8000], tool["inputSchema"])
            if len(exposed) + len(base.definitions) > MCP_MAX_TOOLS_TOTAL:
                raise MCPStdioError("ACP session exposed too many total tools")
            self._exposed = exposed
            return _ACPSessionToolRegistry(base, exposed, cancel)

    def list_servers(self) -> list[dict[str, Any]]:
        with self._lock:
            result = []
            for client in self._clients:
                if client.returncode is not None:
                    status = f"stopped ({client.returncode})"
                elif client._proc is not None and client._proc.poll() is None:
                    status = "running"
                else:
                    status = "stopped"
                result.append({
                    "name": client.name,
                    "command": client.config.get("command"),
                    "status": status,
                })
            return result

    def list_tools(self) -> list[dict[str, Any]]:
        with self._lock:
            if self._exposed:
                return [
                    {
                        "name": tool.alias,
                        "source_name": tool.source_name,
                        "server": tool.client.name,
                        "description": tool.description,
                    }
                    for tool in self._exposed.values()
                ]
            tools = []
            for client in self._clients:
                for tool in client.tools:
                    tools.append({
                        "name": tool.get("name", ""),
                        "source_name": tool.get("name", ""),
                        "server": client.name,
                        "description": tool.get("description", ""),
                    })
            return tools

    def cancel(self) -> None:
        with self._lock:
            for client in self._clients:
                client.cancel_active_requests()

    def close(self) -> None:
        with self._lock:
            self._ended = True
            for client in self._clients:
                client.cancel_active_requests()
            self._close_processes()

    def _close_processes(self) -> None:
        clients, self._clients = self._clients, []
        for client in clients:
            client.close()


class _ACPSessionToolRegistry:
    """Combine trusted injected tools with untrusted MCP server definitions."""

    def __init__(
        self,
        base: ToolRegistry,
        mcp_tools: dict[str, _ExposedTool],
        cancel_event: threading.Event,
    ) -> None:
        self.base = base
        self.mcp_tools = mcp_tools
        self.cancel_event = cancel_event

    def provider_definitions(self) -> list[dict[str, Any]]:
        local = self.base.provider_definitions()
        remote = [
            {
                "name": tool.alias,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self.mcp_tools.values()
        ]
        return local + remote

    def execute(self, name: str, arguments: Any) -> ToolOutcome:
        remote = self.mcp_tools.get(name)
        if remote is None:
            return self.base.execute(name, arguments)
        if not isinstance(arguments, dict):
            return ToolOutcome(error="MCP tool arguments must be a JSON object.")
        return remote.client.call_tool(remote.source_name, arguments, cancel_event=self.cancel_event)

    @property
    def definitions(self) -> tuple[Any, ...]:
        base_defs = self.base.definitions if hasattr(self.base, "definitions") else ()
        from cli.tool_registry import ToolDefinition

        def _make_handler(t: _ExposedTool) -> Any:
            def handler(args: dict[str, Any]) -> Any:
                outcome = t.client.call_tool(t.source_name, args, cancel_event=self.cancel_event)
                if outcome.error:
                    raise RuntimeError(outcome.error)
                return outcome.result

            return handler

        remote_defs = tuple(
            ToolDefinition(
                tool.alias,
                tool.description,
                tool.input_schema,
                _make_handler(tool),
            )
            for tool in self.mcp_tools.values()
        )
        return tuple(base_defs) + remote_defs

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)
