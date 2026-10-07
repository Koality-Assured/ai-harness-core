"""Slice 15 HTTP/SSE and ACP v1 entry points over the shared conversation loop.

tags: [harness, cli, gateway, acp, adapter]
routing_hints: [harness, cli, gateway, acp, session, streaming]
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, TextIO

from cli.conversation import TurnCancelled, compact_session, run_turn
from cli.provider_client import (
    ANTHROPIC_DEFAULT_MODEL,
    ProviderError,
    normalize_provider,
)
from cli.session_store import SessionStore, default_state_db_path
from cli.tool_registry import ToolRegistry, ToolOutcome
from cli.mcp_stdio import ACPSessionMCP, MCPStdioError, validate_mcp_servers

MAX_HTTP_BODY = 1_048_576
GATEWAY_ROUTE = "/v1/chat/completions"
ACP_ROUTE = "agent"
ACP_CLOSE_TIMEOUT_SEC = 10.0


@dataclass
class TurnResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    compacted: bool = False


@dataclass
class _TurnJob:
    text: str
    on_delta: Callable[[str], None] | None
    on_tool_start: Callable[[str | None, str, dict[str, Any] | None], None] | None
    on_tool_complete: Callable[[str | None, str, dict[str, Any] | None, ToolOutcome], None] | None
    result: TurnResult | None = None
    error: BaseException | None = None


@dataclass
class _ActiveTurn:
    job: _TurnJob
    busy_mode: str = "interrupt"
    cancel_event: threading.Event = field(default_factory=threading.Event)
    followers: list[_TurnJob] = field(default_factory=list)
    steer_used: bool = False


class _SessionTurnQueue:
    """Serialize requests per adapter session and preserve persisted busy modes."""

    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.active: _ActiveTurn | None = None
        self.pending: deque[_TurnJob] = deque()

    def cancel(self) -> bool:
        with self.condition:
            if self.active is None:
                return False
            self.active.cancel_event.set()
            self.condition.notify_all()
            return True

    def cancel_and_wait(self, timeout: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        with self.condition:
            for job in self.pending:
                job.error = TurnCancelled("session is closing")
            self.pending.clear()
            if self.active is None:
                self.condition.notify_all()
                return True
            self.active.cancel_event.set()
            self.condition.notify_all()
            while self.active is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return True

    def submit(
        self,
        job: _TurnJob,
        *,
        busy_mode: str,
        execute: Callable[[threading.Event, _ActiveTurn], TurnResult],
    ) -> TurnResult:
        with self.condition:
            current = self.active
            self.pending.append(job)
            if current is not None:
                if busy_mode == "interrupt":
                    current.cancel_event.set()
                self.condition.notify_all()
            while True:
                if job.result is not None:
                    return job.result
                if job.error is not None:
                    raise job.error
                if self.active is None and self.pending and self.pending[0] is job:
                    self.pending.popleft()
                    active = _ActiveTurn(job, busy_mode=busy_mode)
                    self.active = active
                    break
                self.condition.wait()

        try:
            result = execute(active.cancel_event, active)
        except BaseException as exc:
            with self.condition:
                job.error = exc
                for follower in active.followers:
                    follower.error = exc
                self.active = None
                self.condition.notify_all()
            raise
        else:
            with self.condition:
                job.result = result
                for follower in active.followers:
                    follower.result = result
                self.active = None
                self.condition.notify_all()
            return result

    def take_steer(self, active: _ActiveTurn) -> str | None:
        with self.condition:
            if active.busy_mode != "steer" or active.steer_used:
                return None
            for job in self.pending:
                # Only the next explicitly steered input is folded into this turn.
                self.pending.remove(job)
                active.followers.append(job)
                active.steer_used = True
                self.condition.notify_all()
                return job.text.strip() or None
            return None

    @staticmethod
    def emit(active: _ActiveTurn, callback_name: str, *args: Any) -> None:
        callbacks = [getattr(active.job, callback_name)]
        callbacks.extend(getattr(job, callback_name) for job in active.followers)
        for callback in callbacks:
            if callback is not None:
                callback(*args)


class AdapterRuntime:
    """Session binding and turn scheduling shared by gateway and ACP."""

    def __init__(
        self,
        *,
        provider: str = "anthropic",
        model: str | None = None,
        db_path: Path | None = None,
        transport: Callable[..., Any] | None = None,
        stream_transport: Callable[..., Any] | None = None,
        tool_registry: ToolRegistry | None = None,
        credential_resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        normalized = normalize_provider(provider)
        if normalized is None:
            raise ValueError(f"unsupported provider: {provider}")
        self.provider = normalized
        self.model = model or (ANTHROPIC_DEFAULT_MODEL if normalized == "anthropic" else "")
        self.db_path = Path(db_path) if db_path else default_state_db_path()
        self.transport = transport
        self.stream_transport = stream_transport or transport
        self.tool_registry = tool_registry or ToolRegistry()
        self.credential_resolver = credential_resolver or self._default_credential
        self._queues_lock = threading.Lock()
        self._queues: dict[tuple[str, str, str, str], _SessionTurnQueue] = {}

    @staticmethod
    def _default_credential(provider: str) -> str | None:
        from cli.harness import _resolve_chat_credential

        token, code = _resolve_chat_credential(provider)
        return token if code == 0 else None

    @staticmethod
    def principal_for_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _queue(self, adapter: str, principal: str, route: str, handle: str) -> _SessionTurnQueue:
        key = (adapter, principal, route, handle)
        with self._queues_lock:
            return self._queues.setdefault(key, _SessionTurnQueue())

    def bind_session(
        self,
        adapter: str,
        principal: str,
        route: str,
        *,
        external_id: str | None = None,
        model: str | None = None,
        cwd: str = "",
        title: str = "",
        initial_messages: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        with SessionStore(self.db_path) as store:
            return store.bind_adapter_session(
                adapter,
                principal,
                route,
                external_id,
                cwd=cwd,
                title=title,
                provider=self.provider,
                model=model or self.model,
                busy_mode="interrupt",
                initial_messages=initial_messages,
            )

    def get_session(self, adapter: str, principal: str, route: str, handle: str) -> dict[str, Any] | None:
        with SessionStore(self.db_path) as store:
            return store.get_adapter_session(adapter, principal, route, handle)

    def cancel(self, adapter: str, principal: str, route: str, handle: str) -> bool:
        return self._queue(adapter, principal, route, handle).cancel()

    def cancel_and_wait(
        self,
        adapter: str,
        principal: str,
        route: str,
        handle: str,
        *,
        timeout: float,
    ) -> bool:
        return self._queue(adapter, principal, route, handle).cancel_and_wait(timeout)

    def run_prompt(
        self,
        adapter: str,
        principal: str,
        route: str,
        handle: str,
        text: str,
        *,
        on_delta: Callable[[str], None] | None = None,
        on_tool_start: Callable[[str | None, str, dict[str, Any] | None], None] | None = None,
        on_tool_complete: Callable[[str | None, str, dict[str, Any] | None, ToolOutcome], None] | None = None,
        tool_registry_factory: Callable[[threading.Event], Any] | None = None,
    ) -> TurnResult:
        identity = (adapter, principal, route, handle)
        queue = self._queue(*identity)
        job = _TurnJob(text, on_delta, on_tool_start, on_tool_complete)
        with SessionStore(self.db_path) as store:
            session = store.get_adapter_session(*identity)
            if session is None:
                raise KeyError("adapter session not found")
            busy_mode = session.get("busy_mode") or "interrupt"

        def execute(cancel_event: threading.Event, active: _ActiveTurn) -> TurnResult:
            with SessionStore(self.db_path) as store:
                session = store.get_adapter_session(*identity)
                if session is None:
                    raise KeyError("adapter session not found")
                session_id = session["id"]
                provider = session.get("provider") or self.provider
                model = session.get("model") or self.model
                if text.strip() == "/compact":
                    credential = self.credential_resolver(provider)
                    if not credential:
                        raise RuntimeError(f"no credentials for '{provider}'")
                    compacted = compact_session(
                        store,
                        session_id,
                        provider,
                        model,
                        credential,
                        self.transport,
                    )
                    if compacted is None:
                        return TurnResult("Session has too little history to compact.")
                    compacted_session = compacted["session"]
                    store.rebind_adapter_session(*identity, compacted_session["id"])
                    return TurnResult(
                        f"Compacted {compacted.get('compacted_turns', 0)} older turns.",
                        compacted=True,
                    )

                credential = self.credential_resolver(provider)
                if not credential:
                    raise RuntimeError(f"no credentials for '{provider}'")
                before = {item["id"] for item in store.list_messages(session_id)}
                try:
                    response = run_turn(
                        store,
                        session_id,
                        text,
                        provider=provider,
                        model=model or None,
                        api_key=credential,
                        transport=self.transport,
                        stream=True,
                        stream_transport=self.stream_transport,
                        on_delta=lambda delta: _SessionTurnQueue.emit(
                            active, "on_delta", delta
                        ),
                        tool_registry=(
                            tool_registry_factory(cancel_event)
                            if tool_registry_factory is not None
                            else self.tool_registry
                        ),
                        on_tool_batch=lambda: queue.take_steer(active),
                        on_tool_start=lambda call_id, name, arguments: _SessionTurnQueue.emit(
                            active, "on_tool_start", call_id, name, arguments
                        ),
                        on_tool_complete=lambda call_id, name, arguments, outcome: _SessionTurnQueue.emit(
                            active, "on_tool_complete", call_id, name, arguments, outcome
                        ),
                        cancel_event=cancel_event,
                    )
                except TurnCancelled:
                    raise
                after = store.list_messages(session_id)
                added = [message for message in after if message["id"] not in before]
                prompt_tokens = sum(message.get("input_tokens") or 0 for message in added)
                completion_tokens = sum(message.get("output_tokens") or 0 for message in added)
                return TurnResult(response, prompt_tokens, completion_tokens)

        return queue.submit(job, busy_mode=busy_mode, execute=execute)

    def history(self, adapter: str, principal: str, route: str, handle: str) -> list[dict[str, Any]]:
        with SessionStore(self.db_path) as store:
            session = store.get_adapter_session(adapter, principal, route, handle)
            if session is None:
                raise KeyError("adapter session not found")
            return store.list_messages(session["id"])


def _message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
                raise ValueError("only text message content is supported")
            parts.append(item["text"])
        return "".join(parts)
    if value is None:
        return ""
    raise ValueError("message content must be text")


def _gateway_history(messages: list[Any], provider: str) -> tuple[list[dict[str, Any]], str]:
    if not messages:
        raise ValueError("messages must contain at least one user message")
    normalized: list[dict[str, Any]] = []
    last_user_index = -1
    for raw in messages:
        if not isinstance(raw, dict):
            raise ValueError("each message must be an object")
        role = raw.get("role")
        if role not in ("system", "user", "assistant", "tool"):
            raise ValueError("message role must be system, user, assistant, or tool")
        content = _message_text(raw.get("content"))
        message: dict[str, Any] = {"role": role, "content": content}
        calls = raw.get("tool_calls")
        if role == "assistant" and calls:
            if not isinstance(calls, list):
                raise ValueError("assistant tool_calls must be an array")
            if provider == "openai":
                message["provider_data"] = {"provider": "openai", "message": {"role": "assistant", "content": content, "tool_calls": calls}}
            elif provider == "anthropic":
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for call in calls:
                    if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                        raise ValueError("assistant tool call must include a function object")
                    function = call["function"]
                    raw_arguments = function.get("arguments", {})
                    try:
                        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                    except json.JSONDecodeError:
                        raise ValueError("assistant tool arguments must be valid JSON") from None
                    if not isinstance(arguments, dict):
                        raise ValueError("assistant tool arguments must be an object")
                    blocks.append({"type": "tool_use", "id": call.get("id", ""), "name": function.get("name", ""), "input": arguments})
                message["provider_data"] = {"provider": "anthropic", "message": {"role": "assistant", "content": blocks}}
            else:
                raise ValueError("tool-call history is only supported for anthropic and openai providers")
        if role == "tool":
            tool_id = raw.get("tool_call_id")
            if not isinstance(tool_id, str) or not tool_id:
                raise ValueError("tool message must include tool_call_id")
            message["provider_data"] = {
                "provider": provider,
                "tool_result": {
                    "id": tool_id,
                    "name": raw.get("name", ""),
                    "content": content,
                    "result": None,
                    "is_error": False,
                },
            }
        normalized.append(message)
        if role == "user":
            last_user_index = len(normalized) - 1
    if last_user_index < 0:
        raise ValueError("messages must contain a user message")
    if last_user_index != len(normalized) - 1:
        raise ValueError("the final message must be from the user")
    final_text = normalized[last_user_index]["content"]
    return normalized[:last_user_index], final_text


def _usage_payload(result: TurnResult) -> dict[str, int]:
    return {
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_tokens": result.prompt_tokens + result.completion_tokens,
    }


def build_gateway_handler(runtime: AdapterRuntime, api_key: str) -> type[BaseHTTPRequestHandler]:
    expected = api_key.encode("utf-8")

    class GatewayHandler(BaseHTTPRequestHandler):
        server_version = "HarnessGateway/1"

        def log_message(self, format: str, *args: Any) -> None:
            # Avoid request-body or authorization content in standard logs.
            return

        def _json(self, status: int, payload: dict[str, Any], session_id: str | None = None) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if session_id:
                self.send_header("X-Hermes-Session-Id", session_id)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != GATEWAY_ROUTE:
                self._json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})
                return
            auth = self.headers.get("Authorization", "")
            scheme, _, supplied = auth.partition(" ")
            if scheme.lower() != "bearer" or not hmac.compare_digest(supplied.encode("utf-8"), expected):
                self._json(401, {"error": {"message": "unauthorized", "type": "authentication_error"}})
                return
            raw_length = self.headers.get("Content-Length", "")
            try:
                length = int(raw_length)
            except ValueError:
                self._json(411, {"error": {"message": "content-length required", "type": "invalid_request_error"}})
                return
            if length < 0 or length > MAX_HTTP_BODY:
                self._json(413, {"error": {"message": "request body too large", "type": "invalid_request_error"}})
                return
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("request body must be an object")
                if any(body.get(key) is not None for key in ("tools", "tool_choice", "functions", "function_call")):
                    raise ValueError("client-provided tools are unsupported; harness tools are configured by the server")
                messages = body.get("messages")
                if not isinstance(messages, list):
                    raise ValueError("messages must be an array")
                history, prompt = _gateway_history(messages, runtime.provider)
                stream = body.get("stream", False)
                if not isinstance(stream, bool):
                    raise ValueError("stream must be a boolean")
                model = body.get("model")
                if not isinstance(model, str) or not model:
                    raise ValueError("model is required and must be a non-empty string")
                external_id = self.headers.get("X-Hermes-Session-Id")
                principal = runtime.principal_for_token(self._authorized_token())
                handle, session = runtime.bind_session(
                    "gateway",
                    principal,
                    GATEWAY_ROUTE,
                    external_id=external_id,
                    model=model,
                    cwd=str(Path.cwd()),
                    title="Gateway conversation",
                    initial_messages=history,
                )
                if session.get("provider") != runtime.provider:
                    raise ValueError("session is bound to a different provider")
                # The session model is fixed on creation so an existing handle cannot silently switch models.
                session_model = session.get("model") or model
                if session_model != model:
                    raise ValueError("session is bound to a different model")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
                self._json(400, {"error": {"message": str(exc), "type": "invalid_request_error"}})
                return

            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())
            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("X-Hermes-Session-Id", handle)
                self.end_headers()
                self.wfile.flush()
                stream_lock = threading.Lock()
                stream_finished = threading.Event()

                def write_frame(payload: dict[str, Any], event: str | None = None) -> None:
                    frame = bytearray()
                    if event:
                        frame.extend(f"event: {event}\n".encode("utf-8"))
                    frame.extend(b"data: " + json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n\n")
                    with stream_lock:
                        self.wfile.write(frame)
                        self.wfile.flush()

                def keepalive() -> None:
                    while not stream_finished.wait(10):
                        try:
                            with stream_lock:
                                self.wfile.write(b": keepalive\n\n")
                                self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            runtime.cancel("gateway", principal, GATEWAY_ROUTE, handle)
                            return

                keepalive_thread = threading.Thread(target=keepalive, daemon=True)
                keepalive_thread.start()

                def delta(text: str) -> None:
                    write_frame({
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": session_model,
                        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                    })

                def tool_start(call_id: str | None, name: str, _arguments: dict[str, Any] | None) -> None:
                    write_frame(
                        {"tool": name, "toolCallId": call_id, "status": "running"},
                        "hermes.tool.progress",
                    )

                try:
                    result = runtime.run_prompt(
                        "gateway", principal, GATEWAY_ROUTE, handle, prompt,
                        on_delta=delta, on_tool_start=tool_start,
                    )
                    write_frame({
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": session_model,
                        "session_id": handle,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        "usage": _usage_payload(result),
                    })
                except (ProviderError, RuntimeError, TurnCancelled, KeyError) as exc:
                    message = str(exc) if isinstance(exc, ProviderError) else "turn failed"
                    write_frame({"error": {"message": message, "type": "server_error"}})
                except (BrokenPipeError, ConnectionResetError):
                    runtime.cancel("gateway", principal, GATEWAY_ROUTE, handle)
                    return
                finally:
                    stream_finished.set()
                    keepalive_thread.join(timeout=1)
                    try:
                        with stream_lock:
                            self.wfile.write(b"data: [DONE]\n\n")
                            self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                return

            try:
                result = runtime.run_prompt("gateway", principal, GATEWAY_ROUTE, handle, prompt)
            except (ProviderError, RuntimeError, TurnCancelled, KeyError):
                self._json(502, {"error": {"message": "turn failed", "type": "server_error"}}, handle)
                return
            self._json(200, {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "model": session_model,
                "session_id": handle,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop"}],
                "usage": _usage_payload(result),
            }, handle)

        def _authorized_token(self) -> str:
            auth = self.headers.get("Authorization", "")
            return auth.partition(" ")[2]

    return GatewayHandler


def serve_gateway(
    runtime: AdapterRuntime,
    *,
    host: str = "127.0.0.1",
    port: int = 8642,
    api_key: str | None = None,
) -> None:
    secret = api_key if api_key is not None else os.environ.get("HARNESS_GATEWAY_API_KEY", "")
    if not secret:
        raise RuntimeError("set HARNESS_GATEWAY_API_KEY before starting the gateway")
    server = ThreadingHTTPServer((host, port), build_gateway_handler(runtime, secret))
    server.daemon_threads = True
    print(f"Harness gateway listening on http://{host}:{server.server_port}{GATEWAY_ROUTE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _rpc_response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result if result is not None else {}
    return response


def _acp_notification(session_id: str, update: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": session_id, "update": update}}


def _acp_text(prompt: Any) -> str:
    if not isinstance(prompt, list) or not prompt:
        raise ValueError("prompt must be a non-empty content array")
    chunks: list[str] = []
    for item in prompt:
        if not isinstance(item, dict):
            raise ValueError("prompt content blocks must be objects")
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            chunks.append(item["text"])
            continue
        if item.get("type") == "resource_link":
            if not all(isinstance(item.get(field), str) and item[field] for field in ("name", "uri")):
                raise ValueError("resource_link prompt blocks require non-empty name and uri strings")
            try:
                encoded = json.dumps(item, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
            except (TypeError, ValueError):
                raise ValueError("resource_link prompt block must contain JSON-compatible fields") from None
            chunks.append("\n[ACP resource_link reference; untrusted and not fetched]\n")
            chunks.append(encoded)
            chunks.append("\n")
            continue
        raise ValueError("text and resource_link prompt blocks are supported")
    return "".join(chunks)


def _native_tool_calls(message: dict[str, Any]) -> list[tuple[str, str, Any]]:
    data = message.get("provider_data") or {}
    native = data.get("message") if isinstance(data, dict) else None
    provider = data.get("provider") if isinstance(data, dict) else None
    calls: list[tuple[str, str, Any]] = []
    if provider == "openai" and isinstance(native, dict):
        for call in native.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function") or {}
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            calls.append((str(call.get("id") or ""), str(function.get("name") or "tool"), arguments))
    elif provider == "anthropic" and isinstance(native, dict):
        for block in native.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                calls.append((str(block.get("id") or ""), str(block.get("name") or "tool"), block.get("input")))
    elif provider == "gemini" and isinstance(native, dict):
        for part in native.get("parts") or []:
            function = part.get("functionCall") if isinstance(part, dict) else None
            if isinstance(function, dict):
                calls.append((str(function.get("id") or ""), str(function.get("name") or "tool"), function.get("args")))
    return calls


def run_acp_stdio(
    runtime: AdapterRuntime,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """Serve ACP v1 JSON-RPC messages over newline-delimited stdio."""
    import sys

    source = input_stream or sys.stdin
    sink = output_stream or sys.stdout
    write_lock = threading.Lock()
    acp_principal = "stdio"
    initialized = False
    mcp_sessions: dict[str, ACPSessionMCP] = {}
    mcp_sessions_lock = threading.RLock()
    prompt_threads: dict[str, set[threading.Thread]] = {}
    prompt_threads_condition = threading.Condition()
    def write(message: dict[str, Any]) -> None:
        encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        with write_lock:
            sink.write(encoded + "\n")
            sink.flush()

    def send_update(session_id: str, update: dict[str, Any]) -> None:
        write(_acp_notification(session_id, update))

    def respond(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> None:
        write(_rpc_response(request_id, result, error))

    def session_mcp(handle: str) -> ACPSessionMCP | None:
        with mcp_sessions_lock:
            return mcp_sessions.get(handle)

    def run_prompt_thread(request_id: Any, handle: str, session_id: str, prompt_text: str) -> None:
        try:
            handle_prompt(request_id, handle, session_id, prompt_text)
        finally:
            current = threading.current_thread()
            with prompt_threads_condition:
                sessions = prompt_threads.get(handle)
                if sessions is not None:
                    sessions.discard(current)
                    if not sessions:
                        prompt_threads.pop(handle, None)
                prompt_threads_condition.notify_all()

    def start_prompt_thread(request_id: Any, handle: str, session_id: str, prompt_text: str) -> None:
        thread = threading.Thread(
            target=run_prompt_thread,
            args=(request_id, handle, session_id, prompt_text),
            daemon=True,
        )
        with prompt_threads_condition:
            prompt_threads.setdefault(handle, set()).add(thread)
        thread.start()

    def wait_prompt_threads(handle: str, timeout: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout)
        with prompt_threads_condition:
            while prompt_threads.get(handle):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                prompt_threads_condition.wait(remaining)
            return True

    def handle_prompt(request_id: Any, session_handle: str, session_id: str, prompt_text: str) -> None:
        mcp_session = session_mcp(session_handle)
        if mcp_session is None:
            respond(request_id, error={"code": -32001, "message": "session is not active; load it before prompting"})
            return
        message_id = str(uuid.uuid4())
        streamed: list[str] = []
        send_update(session_handle, {
            "sessionUpdate": "user_message_chunk",
            "messageId": message_id,
            "content": {"type": "text", "text": prompt_text},
        })
        agent_message_id = str(uuid.uuid4())
        tool_ids: dict[tuple[str, str], str] = {}
        try:
            def on_delta(delta: str) -> None:
                streamed.append(delta)
                send_update(session_handle, {
                    "sessionUpdate": "agent_message_chunk",
                    "messageId": agent_message_id,
                    "content": {"type": "text", "text": delta},
                })

            def on_tool_start(call_id: str | None, name: str, arguments: dict[str, Any] | None) -> None:
                stable_call_id = call_id or str(uuid.uuid4())
                tool_ids[(call_id or "", name)] = stable_call_id
                send_update(session_handle, {
                    "sessionUpdate": "tool_call",
                    "toolCallId": stable_call_id,
                    "title": name,
                    "name": name,
                    "kind": "other",
                    "status": "in_progress",
                    "rawInput": arguments,
                })

            def on_tool_complete(call_id: str | None, name: str, _arguments: dict[str, Any] | None, outcome: ToolOutcome) -> None:
                stable_call_id = tool_ids.get((call_id or "", name)) or call_id or str(uuid.uuid4())
                send_update(session_handle, {
                    "sessionUpdate": "tool_call_update",
                    "toolCallId": stable_call_id,
                    "status": "failed" if outcome.error else "completed",
                    "rawOutput": outcome.error if outcome.error else outcome.result,
                })

            result = runtime.run_prompt(
                "acp", acp_principal, ACP_ROUTE, session_handle, prompt_text,
                on_delta=on_delta,
                on_tool_start=on_tool_start,
                on_tool_complete=on_tool_complete,
                tool_registry_factory=lambda cancel_event: mcp_session.tool_registry(
                    runtime.tool_registry, cancel_event
                ),
            )
            if not streamed and result.text:
                send_update(session_handle, {
                    "sessionUpdate": "agent_message_chunk",
                    "messageId": agent_message_id,
                    "content": {"type": "text", "text": result.text},
                })
            respond(request_id, {"stopReason": "end_turn"})
        except TurnCancelled:
            respond(request_id, {"stopReason": "cancelled"})
        except ProviderError:
            respond(request_id, error={"code": -32000, "message": "provider request failed"})
        except Exception:
            respond(request_id, error={"code": -32000, "message": "prompt failed"})

    try:
        for raw_line in source:
            line = raw_line.strip()
            if not line:
                continue
            request_id: Any = None
            is_notification = False
            try:
                request = json.loads(line)
                if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
                    raise ValueError("invalid JSON-RPC message")
                request_id = request.get("id")
                is_notification = "id" not in request
                method = request["method"]
                params = request.get("params") or {}
                if not isinstance(params, dict):
                    raise ValueError("params must be an object")

                if method == "initialize":
                    if params.get("protocolVersion") != 1:
                        raise ValueError("only ACP protocol version 1 is supported")
                    initialized = True
                    respond(request_id, {
                        "protocolVersion": 1,
                        "agentCapabilities": {
                            "loadSession": True,
                            "promptCapabilities": {"image": False, "audio": False, "embeddedContext": False},
                            "mcpCapabilities": {"http": False, "sse": False},
                            "sessionCapabilities": {"close": {}},
                        },
                        "agentInfo": {"name": "Harness", "version": "0.15.0"},
                    })
                elif not initialized:
                    raise RuntimeError("initialize must be called first")
                elif method == "session/new":
                    cwd = params.get("cwd")
                    servers = params.get("mcpServers", [])
                    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
                        raise ValueError("cwd must be an absolute path")
                    servers = validate_mcp_servers(servers)
                    if not runtime.model:
                        raise ValueError(f"provider '{runtime.provider}' requires --model")
                    resolved_cwd = str(Path(cwd).resolve())
                    mcp_session = ACPSessionMCP(servers, cwd=resolved_cwd)
                    try:
                        handle, _session = runtime.bind_session(
                            "acp", acp_principal, ACP_ROUTE, cwd=resolved_cwd, title="ACP session"
                        )
                    except BaseException:
                        mcp_session.close()
                        raise
                    with mcp_sessions_lock:
                        mcp_sessions[handle] = mcp_session
                    respond(request_id, {"sessionId": handle})
                elif method == "session/load":
                    handle = params.get("sessionId")
                    cwd = params.get("cwd")
                    if not isinstance(handle, str) or not isinstance(cwd, str) or not Path(cwd).is_absolute():
                        raise ValueError("sessionId and absolute cwd are required")
                    servers = validate_mcp_servers(params.get("mcpServers", []))
                    session = runtime.get_session("acp", acp_principal, ACP_ROUTE, handle)
                    if session is None:
                        respond(request_id, error={"code": -32001, "message": "session not found"})
                        continue
                    if str(Path(session.get("cwd") or "").resolve()) != str(Path(cwd).resolve()):
                        respond(request_id, error={"code": -32602, "message": "cwd does not match the stored session"})
                        continue
                    resolved_cwd = str(Path(cwd).resolve())
                    mcp_session = ACPSessionMCP(servers, cwd=resolved_cwd)
                    with mcp_sessions_lock:
                        previous_mcp_session = mcp_sessions.get(handle)
                        mcp_sessions[handle] = mcp_session
                    if previous_mcp_session is not None:
                        previous_mcp_session.close()
                    messages = runtime.history("acp", acp_principal, ACP_ROUTE, handle)
                    active_tools: dict[str, tuple[str, str]] = {}
                    for message in messages:
                        role = message.get("role")
                        if role == "user":
                            send_update(handle, {
                                "sessionUpdate": "user_message_chunk",
                                "messageId": message["id"],
                                "content": {"type": "text", "text": message.get("content", "")},
                            })
                        elif role == "assistant":
                            if message.get("content"):
                                send_update(handle, {
                                    "sessionUpdate": "agent_message_chunk",
                                    "messageId": message["id"],
                                    "content": {"type": "text", "text": message.get("content", "")},
                                })
                            for tool_id, name, args in _native_tool_calls(message):
                                stable_id = tool_id or str(uuid.uuid4())
                                active_tools[tool_id] = (stable_id, name)
                                send_update(handle, {
                                    "sessionUpdate": "tool_call",
                                    "toolCallId": stable_id,
                                    "title": name,
                                    "name": name,
                                    "kind": "other",
                                    "status": "in_progress",
                                    "rawInput": args,
                                })
                        elif role == "tool":
                            result_data = (message.get("provider_data") or {}).get("tool_result") or {}
                            tool_id = result_data.get("id") or ""
                            mapped = active_tools.get(tool_id)
                            if mapped:
                                stable_id, _name = mapped
                                send_update(handle, {
                                    "sessionUpdate": "tool_call_update",
                                    "toolCallId": stable_id,
                                    "status": "failed" if result_data.get("is_error") else "completed",
                                    "rawOutput": result_data.get("content", message.get("content", "")),
                                })
                    respond(request_id, {})
                elif method == "session/prompt":
                    handle = params.get("sessionId")
                    if not isinstance(handle, str):
                        raise ValueError("sessionId is required")
                    session = runtime.get_session("acp", acp_principal, ACP_ROUTE, handle)
                    if session is None:
                        respond(request_id, error={"code": -32001, "message": "session not found"})
                        continue
                    prompt_text = _acp_text(params.get("prompt"))
                    start_prompt_thread(request_id, handle, session["id"], prompt_text)
                elif method == "session/cancel":
                    handle = params.get("sessionId")
                    if isinstance(handle, str):
                        runtime.cancel("acp", acp_principal, ACP_ROUTE, handle)
                        mcp_session = session_mcp(handle)
                        if mcp_session is not None:
                            mcp_session.cancel()
                elif method == "session/close":
                    handle = params.get("sessionId")
                    if not isinstance(handle, str):
                        raise ValueError("sessionId is required")
                    runtime.cancel("acp", acp_principal, ACP_ROUTE, handle)
                    mcp_session = session_mcp(handle)
                    if mcp_session is not None:
                        mcp_session.cancel()
                    deadline = time.monotonic() + ACP_CLOSE_TIMEOUT_SEC
                    queue_stopped = runtime.cancel_and_wait(
                        "acp", acp_principal, ACP_ROUTE, handle,
                        timeout=max(0.0, deadline - time.monotonic()),
                    )
                    prompts_stopped = wait_prompt_threads(
                        handle, max(0.0, deadline - time.monotonic())
                    )
                    if not queue_stopped or not prompts_stopped:
                        respond(request_id, error={
                            "code": -32000,
                            "message": "session work did not stop before the close timeout; session resources remain active",
                        })
                        continue
                    with mcp_sessions_lock:
                        mcp_session = mcp_sessions.pop(handle, None)
                    if mcp_session is not None:
                        mcp_session.close()
                    respond(request_id, {})
                else:
                    if not is_notification:
                        respond(request_id, error={"code": -32601, "message": "method not found"})
            except json.JSONDecodeError:
                if not is_notification:
                    respond(request_id, error={"code": -32700, "message": "parse error"})
            except MCPStdioError as exc:
                if not is_notification:
                    respond(request_id, error={"code": -32000, "message": str(exc)})
            except (ValueError, RuntimeError) as exc:
                if not is_notification:
                    respond(request_id, error={"code": -32602, "message": str(exc)})
    finally:
        with mcp_sessions_lock:
            ending_sessions = list(mcp_sessions.items())
            mcp_sessions.clear()
        for handle, mcp_session in ending_sessions:
            runtime.cancel("acp", acp_principal, ACP_ROUTE, handle)
            mcp_session.cancel()
            deadline = time.monotonic() + ACP_CLOSE_TIMEOUT_SEC
            runtime.cancel_and_wait(
                "acp", acp_principal, ACP_ROUTE, handle,
                timeout=max(0.0, deadline - time.monotonic()),
            )
            wait_prompt_threads(handle, max(0.0, deadline - time.monotonic()))
            mcp_session.close()
