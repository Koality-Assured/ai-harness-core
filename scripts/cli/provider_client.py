"""HTTP provider clients for harness conversation turns (stdlib only).

tags: [harness, cli, provider, anthropic, openai, gemini]
routing_hints: [provider, complete, messages, chat, transport]
"""

from __future__ import annotations

import codecs
import functools
import http.client
import json
import os
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator

# Injectable transport: (url, headers, body_bytes) -> (status, body_bytes)
Transport = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]
# Streaming transport returns an open byte iterator on success, or the error body
# as bytes. The caller closes the iterator/response when the stream ends or aborts.
StreamTransport = Callable[[str, dict[str, str], bytes], tuple[int, Iterable[bytes] | bytes]]

DEFAULT_TIMEOUT_SEC = 120
ANTHROPIC_BASE_URL_ENV = "HARNESS_ANTHROPIC_BASE_URL"
ANTHROPIC_MESSAGES_PATH = "/v1/messages"


def _anthropic_messages_url() -> str:
    base = os.environ.get(ANTHROPIC_BASE_URL_ENV, "").strip()
    if not base:
        return "https://api.anthropic.com" + ANTHROPIC_MESSAGES_PATH
    try:
        parsed = urllib.parse.urlsplit(base)
        parsed.port
    except ValueError as exc:
        raise ProviderError(
            f"invalid {ANTHROPIC_BASE_URL_ENV}; expected an HTTP(S) origin"
        ) from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or "?" in base
        or parsed.fragment
    ):
        raise ProviderError(
            f"invalid {ANTHROPIC_BASE_URL_ENV}; expected an HTTP(S) origin"
        )
    return base.rstrip("/") + ANTHROPIC_MESSAGES_PATH

# Confirmed alias in Anthropic Messages API docs:
# https://platform.claude.com/docs/en/api/messages
# https://platform.claude.com/docs/en/build-with-claude/working-with-messages
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-5"

# OpenAI Chat Completions requires an explicit model (no API default):
# https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create/
# Gemini model ids churn across docs; require --model rather than inventing one:
# https://ai.google.dev/gemini-api/docs/models
# https://ai.google.dev/api/generate-content

PROVIDER_ALIASES: dict[str, str] = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "cursor": "cursor",
    "gemini": "gemini",
    "google": "gemini",
    "openai": "openai",
    "gpt": "openai",
}


class ProviderError(Exception):
    """Typed provider failure with HTTP status and a short body excerpt (never the API key)."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body_excerpt: str = "",
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body_excerpt = body_excerpt


class StreamCancelled(Exception):
    """A streaming provider request was interrupted by its caller."""


@dataclass(frozen=True)
class ToolCall:
    id: str | None
    name: str
    arguments: Any


@dataclass(frozen=True)
class CompletionResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_message: dict[str, Any] | None = None


def _validate_required_tool_call_ids(provider: str, tool_calls: list[ToolCall]) -> None:
    """Reject native calls that cannot receive a valid paired result message."""
    if provider not in ("anthropic", "openai"):
        return
    if any(not isinstance(call.id, str) or not call.id.strip() for call in tool_calls):
        raise ProviderError(f"{provider} returned a tool call without a required call ID")


def _token_count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def normalize_provider(raw: str) -> str | None:
    return PROVIDER_ALIASES.get((raw or "").lower().strip())


def _excerpt(body: bytes | str, limit: int = 240) -> str:
    text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    text = text.replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _default_transport(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SEC) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return int(exc.code), raw
    except urllib.error.URLError as exc:
        raise ProviderError(f"network error: {exc.reason}") from exc


class _CancellableHTTPStream:
    """Own the URL opener's connection and response so ACP cancellation can close either phase."""

    def __init__(self, cancel_event: threading.Event | None) -> None:
        self.cancel_event = cancel_event
        self._lock = threading.RLock()
        self._connection: Any = None
        self._response: Any = None
        self._closed = False
        self._done = threading.Event()
        self._monitor: threading.Thread | None = None
        if cancel_event is not None:
            self._monitor = threading.Thread(
                target=self._monitor_cancel,
                name="provider-http-cancel",
                daemon=True,
            )
            self._monitor.start()

    def _monitor_cancel(self) -> None:
        assert self.cancel_event is not None
        while not self._done.wait(0.025):
            if self.cancel_event.is_set():
                self._close_resources()
                return

    def attach_connection(self, connection: Any) -> None:
        with self._lock:
            self._connection = connection
            should_close = self._closed or (self.cancel_event is not None and self.cancel_event.is_set())
        if should_close:
            try:
                connection.close()
            except Exception:
                pass

    def attach_response(self, response: Any) -> None:
        with self._lock:
            self._response = response
            should_close = self._closed or (self.cancel_event is not None and self.cancel_event.is_set())
        if should_close:
            try:
                response.close()
            except Exception:
                pass

    def raise_if_cancelled(self) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise StreamCancelled("provider stream was cancelled")

    def _close_resources(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            response, connection = self._response, self._connection
        # Shutdown first to wake a response parser blocked on its socket
        # makefile, then close the response's file object.
        for resource in (connection, response):
            abort = getattr(resource, "abort", None)
            if callable(abort):
                try:
                    abort()
                except Exception:
                    pass
                continue
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def close(self) -> None:
        self._done.set()
        self._close_resources()
        if self._monitor is not None and self._monitor is not threading.current_thread():
            self._monitor.join(timeout=0.2)

    def __iter__(self) -> "_CancellableHTTPStream":
        return self

    def __next__(self) -> bytes:
        if self.cancel_event is not None and self.cancel_event.is_set():
            self.close()
            raise StreamCancelled("provider stream was cancelled")
        with self._lock:
            response = self._response
        if response is None:
            raise StopIteration
        try:
            return next(response)
        except StopIteration:
            raise
        except Exception:
            if self.cancel_event is not None and self.cancel_event.is_set():
                raise StreamCancelled("provider stream was cancelled") from None
            raise


class _TrackedHTTPResponse(http.client.HTTPResponse):
    def __init__(
        self,
        sock: Any,
        debuglevel: int = 0,
        method: str | None = None,
        url: str | None = None,
        *,
        stream: _CancellableHTTPStream,
    ) -> None:
        super().__init__(sock, debuglevel=debuglevel, method=method, url=url)
        stream.attach_response(self)


class _TrackedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, *, stream: _CancellableHTTPStream, **kwargs: Any) -> None:
        self.stream = stream
        super().__init__(host, **kwargs)
        self.response_class = functools.partial(_TrackedHTTPResponse, stream=stream)

    def abort(self) -> None:
        sock = self.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.close()

    def connect(self) -> None:
        self.stream.raise_if_cancelled()
        try:
            super().connect()
        except BaseException:
            if self.stream.cancel_event is not None and self.stream.cancel_event.is_set():
                self.close()
                raise StreamCancelled("provider stream was cancelled") from None
            raise
        if self.stream.cancel_event is not None and self.stream.cancel_event.is_set():
            self.close()
            raise StreamCancelled("provider stream was cancelled")


class _TrackedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, stream: _CancellableHTTPStream, **kwargs: Any) -> None:
        self.stream = stream
        super().__init__(host, **kwargs)
        self.response_class = functools.partial(_TrackedHTTPResponse, stream=stream)

    def abort(self) -> None:
        sock = self.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.close()

    def connect(self) -> None:
        self.stream.raise_if_cancelled()
        try:
            super().connect()
        except BaseException:
            if self.stream.cancel_event is not None and self.stream.cancel_event.is_set():
                self.close()
                raise StreamCancelled("provider stream was cancelled") from None
            raise
        if self.stream.cancel_event is not None and self.stream.cancel_event.is_set():
            self.close()
            raise StreamCancelled("provider stream was cancelled")


class _TrackedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, stream: _CancellableHTTPStream) -> None:
        super().__init__()
        self.stream = stream

    def http_open(self, req: urllib.request.Request) -> Any:
        def connection_factory(host: str, **kwargs: Any) -> _TrackedHTTPConnection:
            connection = _TrackedHTTPConnection(host, stream=self.stream, **kwargs)
            self.stream.attach_connection(connection)
            return connection

        return self.do_open(connection_factory, req)


class _TrackedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, stream: _CancellableHTTPStream) -> None:
        super().__init__()
        self.stream = stream

    def https_open(self, req: urllib.request.Request) -> Any:
        def connection_factory(host: str, **kwargs: Any) -> _TrackedHTTPSConnection:
            connection = _TrackedHTTPSConnection(host, stream=self.stream, **kwargs)
            self.stream.attach_connection(connection)
            return connection

        return self.do_open(
            connection_factory,
            req,
            context=self._context,
            check_hostname=self._check_hostname,
        )


def _default_stream_transport(
    url: str,
    headers: dict[str, str],
    body: bytes,
    *,
    cancel_event: threading.Event | None = None,
) -> tuple[int, Iterable[bytes] | bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    stream = _CancellableHTTPStream(cancel_event)
    opener = urllib.request.build_opener(_TrackedHTTPHandler(stream), _TrackedHTTPSHandler(stream))
    try:
        response = opener.open(req, timeout=DEFAULT_TIMEOUT_SEC)
        stream.attach_response(response)
        if cancel_event is not None and cancel_event.is_set():
            stream.close()
            raise StreamCancelled("provider stream was cancelled")
        return int(response.status), stream
    except urllib.error.HTTPError as exc:
        stream.attach_response(exc)
        try:
            raw = exc.read() if hasattr(exc, "read") else b""
        except Exception:
            if cancel_event is not None and cancel_event.is_set():
                raise StreamCancelled("provider stream was cancelled") from None
            raise
        finally:
            stream.close()
        return int(exc.code), raw
    except urllib.error.URLError as exc:
        stream.close()
        if cancel_event is not None and cancel_event.is_set():
            raise StreamCancelled("provider stream was cancelled") from None
        raise ProviderError(f"network error: {exc.reason}") from exc
    except BaseException:
        stream.close()
        if cancel_event is not None and cancel_event.is_set():
            raise StreamCancelled("provider stream was cancelled") from None
        raise


def _safe_excerpt(raw: bytes, api_key: str) -> str:
    excerpt = _excerpt(raw)
    return excerpt.replace(api_key, "[redacted]") if api_key else excerpt


def _require_model(provider: str, model: str | None) -> str:
    if model and model.strip():
        return model.strip()
    raise ProviderError(
        f"provider '{provider}' requires --model (no safe default confirmed from official docs)"
    )


def _resolve_model(provider: str, model: str | None) -> str:
    if provider == "anthropic":
        return (model or "").strip() or ANTHROPIC_DEFAULT_MODEL
    return _require_model(provider, model)


def _provider_data(message: dict[str, Any]) -> dict[str, Any]:
    data = message.get("provider_data") or message.get("_provider_data") or {}
    return data if isinstance(data, dict) else {}


def _messages_for_anthropic(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pending_results: list[dict[str, Any]] = []

    def flush_tool_results() -> None:
        if pending_results:
            out.append({"role": "user", "content": list(pending_results)})
            pending_results.clear()

    for m in messages:
        role = m.get("role", "user")
        if role == "system":
            # Fold system into a user preface; Messages API uses top-level system separately.
            continue
        data = _provider_data(m)
        if role == "tool" and data.get("provider") == "anthropic":
            result = data.get("tool_result") or {}
            if isinstance(result, dict):
                pending_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.get("id") or "",
                        "content": result.get("content", m.get("content", "")),
                        **({"is_error": True} if result.get("is_error") else {}),
                    }
                )
                continue
        flush_tool_results()
        if role == "assistant" and data.get("provider") == "anthropic":
            native = data.get("message")
            if isinstance(native, dict) and native.get("role") == "assistant":
                out.append(native)
                continue
        if role not in ("user", "assistant"):
            role, content = "user", f"Tool result: {m.get('content', '')}"
        else:
            content = m.get("content", "")
        out.append({"role": role, "content": content})
    flush_tool_results()
    return out


def _system_from_messages(messages: list[dict[str, Any]]) -> str | None:
    parts = [
        m.get("content", "")
        for m in messages
        if m.get("role") == "system" and isinstance(m.get("content", ""), str)
    ]
    text = "\n".join(p for p in parts if p)
    return text or None


def _complete_anthropic(
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: Transport,
    tools: list[dict[str, Any]] | None = None,
) -> CompletionResult:
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": 4096,
        "messages": _messages_for_anthropic(messages),
    }
    system = _system_from_messages(messages)
    if system:
        payload["system"] = system
    if tools:
        payload["tools"] = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            }
            for tool in tools
        ]
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    status, raw = transport(_anthropic_messages_url(), headers, body)
    if status != 200:
        raise ProviderError(
            f"anthropic HTTP {status}",
            status=status,
            body_excerpt=_safe_excerpt(raw, api_key),
        )
    data = json.loads(raw.decode("utf-8"))
    blocks = data.get("content") or []
    texts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"]
    tool_calls = [
        ToolCall(
            id=block.get("id") if isinstance(block.get("id"), str) else None,
            name=block.get("name") if isinstance(block.get("name"), str) else "",
            arguments=block.get("input"),
        )
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]
    _validate_required_tool_call_ids("anthropic", tool_calls)
    usage = data.get("usage") or {}
    return CompletionResult(
        "".join(texts),
        input_tokens=_token_count(usage.get("input_tokens")),
        output_tokens=_token_count(usage.get("output_tokens")),
        tool_calls=tool_calls,
        provider_message={"role": "assistant", "content": blocks},
    )


def _complete_openai(
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: Transport,
    tools: list[dict[str, Any]] | None = None,
) -> CompletionResult:
    payload: dict[str, Any] = {"model": model, "messages": _messages_for_openai(messages)}
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}",
    }
    status, raw = transport("https://api.openai.com/v1/chat/completions", headers, body)
    if status != 200:
        raise ProviderError(
            f"openai HTTP {status}",
            status=status,
            body_excerpt=_safe_excerpt(raw, api_key),
        )
    data = json.loads(raw.decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        text = ""
        provider_message = {"role": "assistant", "content": ""}
        tool_calls: list[ToolCall] = []
    else:
        msg = choices[0].get("message") or {}
        text = str(msg.get("content") or "")
        provider_message = dict(msg)
        tool_calls = []
        for call in msg.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function") or {}
            if not isinstance(function, dict):
                function = {}
            tool_calls.append(
                ToolCall(
                    id=call.get("id") if isinstance(call.get("id"), str) else None,
                    name=function.get("name") if isinstance(function.get("name"), str) else "",
                    arguments=function.get("arguments"),
                )
            )
    _validate_required_tool_call_ids("openai", tool_calls)
    usage = data.get("usage") or {}
    return CompletionResult(
        text,
        input_tokens=_token_count(usage.get("prompt_tokens")),
        output_tokens=_token_count(usage.get("completion_tokens")),
        tool_calls=tool_calls,
        provider_message=provider_message,
    )


def _messages_for_openai(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role", "user")
        data = _provider_data(message)
        if role == "assistant" and data.get("provider") == "openai":
            native = data.get("message")
            if isinstance(native, dict) and native.get("role") == "assistant":
                contents.append(native)
                continue
        if role == "tool" and data.get("provider") == "openai":
            result = data.get("tool_result") or {}
            if isinstance(result, dict):
                contents.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.get("id") or "",
                        "content": result.get("content", message.get("content", "")),
                    }
                )
                continue
        if role not in ("system", "user", "assistant"):
            role, content = "user", f"Tool result: {message.get('content', '')}"
        else:
            content = message.get("content", "")
        contents.append({"role": role, "content": content})
    return contents


def _gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contents: list[dict[str, Any]] = []
    pending_results: list[dict[str, Any]] = []

    def flush_tool_results() -> None:
        if pending_results:
            contents.append({"role": "user", "parts": list(pending_results)})
            pending_results.clear()

    for message in messages:
        role = message.get("role", "user")
        if role == "system":
            continue
        data = _provider_data(message)
        if role == "tool" and data.get("provider") == "gemini":
            result = data.get("tool_result") or {}
            if isinstance(result, dict):
                response = result.get("result")
                if result.get("is_error"):
                    response = {"error": result.get("content", "Tool failed.")}
                elif not isinstance(response, dict):
                    response = {"result": response}
                function_response: dict[str, Any] = {
                    "name": result.get("name", ""),
                    "response": response,
                }
                if isinstance(result.get("id"), str) and result.get("id"):
                    function_response["id"] = result["id"]
                pending_results.append({"functionResponse": function_response})
                continue
        flush_tool_results()
        if role == "assistant" and data.get("provider") == "gemini":
            native = data.get("message")
            if isinstance(native, dict) and native.get("role") == "model":
                contents.append(native)
                continue
        gem_role = "model" if role == "assistant" else "user"
        if role not in ("user", "assistant"):
            content = f"Tool result: {message.get('content', '')}"
        else:
            content = message.get("content", "")
        contents.append({"role": gem_role, "parts": [{"text": content}]})
    flush_tool_results()
    return contents


def _complete_gemini(
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: Transport,
    tools: list[dict[str, Any]] | None = None,
) -> CompletionResult:
    payload: dict[str, Any] = {"contents": _gemini_contents(messages)}
    system = _system_from_messages(messages)
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        payload["tools"] = [
            {
                "functionDeclarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }
                    for tool in tools
                ]
            }
        ]
    body = json.dumps(payload).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "content-type": "application/json",
        "x-goog-api-key": api_key,
    }
    status, raw = transport(url, headers, body)
    if status != 200:
        raise ProviderError(
            f"gemini HTTP {status}",
            status=status,
            body_excerpt=_safe_excerpt(raw, api_key),
        )
    data = json.loads(raw.decode("utf-8"))
    candidates = data.get("candidates") or []
    text = ""
    provider_message: dict[str, Any] | None = None
    tool_calls: list[ToolCall] = []
    if candidates:
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        text = "".join(str(p.get("text") or "") for p in parts if isinstance(p, dict))
        provider_message = dict(content)
        for part in parts:
            if not isinstance(part, dict):
                continue
            function_call = part.get("functionCall")
            if not isinstance(function_call, dict):
                continue
            tool_calls.append(
                ToolCall(
                    id=function_call.get("id") if isinstance(function_call.get("id"), str) else None,
                    name=function_call.get("name") if isinstance(function_call.get("name"), str) else "",
                    arguments=function_call.get("args"),
                )
            )
        if "role" not in provider_message:
            provider_message["role"] = "model"
    usage = data.get("usageMetadata") or {}
    return CompletionResult(
        text,
        input_tokens=_token_count(usage.get("promptTokenCount")),
        output_tokens=_token_count(usage.get("candidatesTokenCount")),
        tool_calls=tool_calls,
        provider_message=provider_message,
    )


def _iter_sse_events(chunks: Iterable[bytes]) -> Iterator[tuple[str, str]]:
    """Decode SSE framing without assuming each transport chunk is one event."""
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    buffer = ""
    event_name = ""
    data_lines: list[str] = []

    def consume_line(line: str) -> tuple[str, str] | None:
        nonlocal event_name, data_lines
        if not line:
            if not data_lines:
                event_name = ""
                return None
            result = (event_name, "\n".join(data_lines))
            event_name = ""
            data_lines = []
            return result
        if line.startswith(":"):
            return None
        field, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)
        return None

    for chunk in chunks:
        if not isinstance(chunk, (bytes, bytearray)):
            raise ProviderError("stream transport yielded a non-byte chunk")
        buffer += decoder.decode(bytes(chunk), final=False)
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            result = consume_line(line[:-1] if line.endswith("\r") else line)
            if result is not None:
                yield result

    buffer += decoder.decode(b"", final=True)
    if buffer:
        result = consume_line(buffer[:-1] if buffer.endswith("\r") else buffer)
        if result is not None:
            yield result
    result = consume_line("")
    if result is not None:
        yield result


def _stream_request(
    provider: str,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
    tools: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, str], bytes]:
    headers = {"content-type": "application/json"}
    if provider == "anthropic":
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": _messages_for_anthropic(messages),
            "stream": True,
        }
        system = _system_from_messages(messages)
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "input_schema": tool["input_schema"],
                }
                for tool in tools
            ]
        headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        return _anthropic_messages_url(), headers, json.dumps(payload).encode("utf-8")
    if provider == "openai":
        payload = {
            "model": model,
            "messages": _messages_for_openai(messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
                for tool in tools
            ]
        headers["authorization"] = f"Bearer {api_key}"
        return "https://api.openai.com/v1/chat/completions", headers, json.dumps(payload).encode("utf-8")
    payload = {"contents": _gemini_contents(messages)}
    system = _system_from_messages(messages)
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        payload["tools"] = [
            {
                "functionDeclarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    }
                    for tool in tools
                ]
            }
        ]
    headers["x-goog-api-key"] = api_key
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    return url, headers, json.dumps(payload).encode("utf-8")


def stream_complete(
    provider: str,
    model: str | None,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: StreamTransport | None = None,
    tools: list[dict[str, Any]] | None = None,
    cancel_event: threading.Event | None = None,
) -> Iterator[str | CompletionResult]:
    """Yield text deltas and a completion with assembled native tool calls."""
    canonical = normalize_provider(provider) or (provider or "").lower().strip()
    if canonical == "cursor":
        raise ProviderError("provider 'cursor' chat is not wired: no documented public chat endpoint to call")
    if canonical not in ("anthropic", "openai", "gemini"):
        raise ProviderError(f"unsupported provider '{provider}'")

    resolved = _resolve_model(canonical, model)
    url, headers, body = _stream_request(canonical, resolved, messages, api_key, tools)
    if transport is None:
        status, response_body = _default_stream_transport(
            url, headers, body, cancel_event=cancel_event
        )
    else:
        status, response_body = transport(url, headers, body)
    if cancel_event is not None and cancel_event.is_set():
        close = getattr(response_body, "close", None)
        if callable(close):
            close()
        raise StreamCancelled("provider stream was cancelled")
    if status != 200:
        error_body = response_body if isinstance(response_body, bytes) else b""
        raise ProviderError(
            f"{canonical} HTTP {status}",
            status=status,
            body_excerpt=_safe_excerpt(error_body, api_key),
        )

    chunks: Iterable[bytes] = (response_body,) if isinstance(response_body, bytes) else response_body
    assembled: list[str] = []
    input_tokens: int | None = None
    output_tokens: int | None = None
    anthropic_blocks: dict[int, dict[str, Any]] = {}
    anthropic_arguments: dict[int, list[str]] = {}
    openai_calls: dict[int, dict[str, Any]] = {}
    gemini_candidates: dict[int, dict[int, dict[str, Any]]] = {}
    gemini_templates: dict[int, dict[str, Any]] = {}

    def merge_fragment(old: Any, new: Any) -> Any:
        if isinstance(old, dict) and isinstance(new, dict):
            merged = dict(old)
            for key, value in new.items():
                merged[key] = merge_fragment(merged[key], value) if key in merged else value
            return merged
        return new

    monitor_done = threading.Event()
    close_lock = threading.Lock()
    stream_closed = False

    def close_stream() -> None:
        nonlocal stream_closed
        with close_lock:
            if stream_closed:
                return
            stream_closed = True
        close = getattr(response_body, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    def monitor_cancellation() -> None:
        if cancel_event is None:
            return
        while not monitor_done.wait(0.025):
            if cancel_event.is_set():
                close_stream()
                return

    monitor = threading.Thread(target=monitor_cancellation, name="provider-stream-cancel", daemon=True)
    monitor.start()
    try:
        for event_name, raw_data in _iter_sse_events(chunks):
            if cancel_event is not None and cancel_event.is_set():
                raise StreamCancelled("provider stream was cancelled")
            if canonical == "openai" and raw_data == "[DONE]":
                break
            try:
                data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                raise ProviderError(f"{canonical} returned an invalid streaming event") from None
            if not isinstance(data, dict):
                continue

            if canonical == "anthropic":
                if event_name == "error" or data.get("type") == "error":
                    raise ProviderError("anthropic returned a streaming error event")
                event_type = data.get("type")
                if event_type == "message_start":
                    usage = (data.get("message") or {}).get("usage") or {}
                    input_tokens = _token_count(usage.get("input_tokens"))
                elif event_type == "message_delta":
                    usage = data.get("usage") or {}
                    if "output_tokens" in usage:
                        output_tokens = _token_count(usage.get("output_tokens"))
                elif event_type == "content_block_start":
                    index = data.get("index")
                    if isinstance(index, int) and isinstance(data.get("content_block"), dict):
                        anthropic_blocks[index] = dict(data["content_block"])
                        if anthropic_blocks[index].get("type") == "tool_use":
                            anthropic_arguments[index] = []
                elif event_type == "content_block_delta":
                    delta = data.get("delta") or {}
                    index = data.get("index")
                    if delta.get("type") == "text_delta":
                        text = delta.get("text")
                        if isinstance(text, str) and text:
                            assembled.append(text)
                            if isinstance(index, int) and index in anthropic_blocks:
                                block = anthropic_blocks[index]
                                block["text"] = str(block.get("text") or "") + text
                            yield text
                    elif delta.get("type") == "input_json_delta":
                        partial = delta.get("partial_json")
                        if isinstance(index, int) and isinstance(partial, str):
                            anthropic_arguments.setdefault(index, []).append(partial)
            elif canonical == "openai":
                usage = data.get("usage") or {}
                if isinstance(usage, dict):
                    if "prompt_tokens" in usage:
                        input_tokens = _token_count(usage.get("prompt_tokens"))
                    if "completion_tokens" in usage:
                        output_tokens = _token_count(usage.get("completion_tokens"))
                for choice in data.get("choices") or []:
                    if not isinstance(choice, dict):
                        continue
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        assembled.append(text)
                        yield text
                    for fragment in delta.get("tool_calls") or []:
                        if not isinstance(fragment, dict) or not isinstance(fragment.get("index"), int):
                            continue
                        index = fragment["index"]
                        call = openai_calls.setdefault(
                            index,
                            {"id": None, "type": "function", "function": {"name": "", "arguments": ""}},
                        )
                        if isinstance(fragment.get("id"), str):
                            call["id"] = fragment["id"]
                        if fragment.get("type"):
                            call["type"] = fragment["type"]
                        function = fragment.get("function") or {}
                        if isinstance(function, dict):
                            name = function.get("name")
                            args = function.get("arguments")
                            if isinstance(name, str):
                                call["function"]["name"] += name
                            if isinstance(args, str):
                                call["function"]["arguments"] += args
            else:
                usage = data.get("usageMetadata") or {}
                if isinstance(usage, dict):
                    if "promptTokenCount" in usage:
                        input_tokens = _token_count(usage.get("promptTokenCount"))
                    if "candidatesTokenCount" in usage:
                        output_tokens = _token_count(usage.get("candidatesTokenCount"))
                for candidate in data.get("candidates") or []:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_index = candidate.get("index", 0)
                    if not isinstance(candidate_index, int):
                        continue
                    content = candidate.get("content") or {}
                    if not isinstance(content, dict):
                        continue
                    gemini_templates.setdefault(candidate_index, dict(content))
                    parts = gemini_candidates.setdefault(candidate_index, {})
                    for part_index, part in enumerate(content.get("parts") or []):
                        if not isinstance(part, dict):
                            continue
                        existing = parts.setdefault(part_index, {})
                        text = part.get("text")
                        if isinstance(text, str) and text:
                            existing["text"] = str(existing.get("text") or "") + text
                            assembled.append(text)
                            yield text
                        function_call = part.get("functionCall")
                        if isinstance(function_call, dict):
                            previous = existing.get("functionCall", {})
                            existing["functionCall"] = merge_fragment(previous, function_call)
                        for key, value in part.items():
                            if key not in ("text", "functionCall"):
                                existing[key] = value
    except Exception:
        if cancel_event is not None and cancel_event.is_set():
            raise StreamCancelled("provider stream was cancelled") from None
        raise
    finally:
        monitor_done.set()
        close_stream()
        monitor.join(timeout=0.1)

    tool_calls: list[ToolCall] = []
    provider_message: dict[str, Any] | None = None
    if canonical == "anthropic":
        blocks: list[dict[str, Any]] = []
        for index in sorted(anthropic_blocks):
            block = dict(anthropic_blocks[index])
            if block.get("type") == "tool_use":
                raw_arguments = "".join(anthropic_arguments.get(index, []))
                if raw_arguments:
                    try:
                        parsed_arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        parsed_arguments = raw_arguments
                    block["input"] = parsed_arguments if isinstance(parsed_arguments, dict) else {}
                    arguments = parsed_arguments
                else:
                    arguments = block.get("input")
                tool_calls.append(
                    ToolCall(
                        id=block.get("id") if isinstance(block.get("id"), str) else None,
                        name=block.get("name") if isinstance(block.get("name"), str) else "",
                        arguments=arguments,
                    )
                )
            blocks.append(block)
        provider_message = {"role": "assistant", "content": blocks}
    elif canonical == "openai":
        native_calls = [openai_calls[index] for index in sorted(openai_calls)]
        for call in native_calls:
            function = call["function"]
            tool_calls.append(
                ToolCall(
                    id=call.get("id") if isinstance(call.get("id"), str) else None,
                    name=function.get("name", ""),
                    arguments=function.get("arguments", ""),
                )
            )
        provider_message = {
            "role": "assistant",
            "content": "".join(assembled) if assembled else (None if native_calls else ""),
        }
        if native_calls:
            provider_message["tool_calls"] = native_calls
    else:
        selected_index = min(gemini_candidates) if gemini_candidates else None
        if selected_index is not None:
            template = gemini_templates.get(selected_index, {})
            provider_message = dict(template)
            provider_message["role"] = provider_message.get("role") or "model"
            provider_message["parts"] = [
                gemini_candidates[selected_index][index]
                for index in sorted(gemini_candidates[selected_index])
            ]
            for part in provider_message["parts"]:
                function_call = part.get("functionCall") if isinstance(part, dict) else None
                if isinstance(function_call, dict):
                    tool_calls.append(
                        ToolCall(
                            id=function_call.get("id") if isinstance(function_call.get("id"), str) else None,
                            name=function_call.get("name") if isinstance(function_call.get("name"), str) else "",
                            arguments=function_call.get("args"),
                        )
                    )

    _validate_required_tool_call_ids(canonical, tool_calls)

    yield CompletionResult(
        "".join(assembled),
        input_tokens,
        output_tokens,
        tool_calls=tool_calls,
        provider_message=provider_message,
    )


def complete(
    provider: str,
    model: str | None,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: Transport | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> str:
    """Run one provider completion. Does not print or log the API key."""
    return complete_result(provider, model, messages, api_key, transport, tools).text


def complete_result(
    provider: str,
    model: str | None,
    messages: list[dict[str, Any]],
    api_key: str,
    transport: Transport | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> CompletionResult:
    """Run one non-streaming completion and retain provider usage when present."""
    canonical = normalize_provider(provider) or (provider or "").lower().strip()
    if canonical == "cursor":
        raise ProviderError(
            "provider 'cursor' chat is not wired: no documented public chat endpoint to call"
        )
    if canonical not in ("anthropic", "openai", "gemini"):
        raise ProviderError(f"unsupported provider '{provider}'")

    resolved = _resolve_model(canonical, model)
    xport = transport or _default_transport

    if canonical == "anthropic":
        return _complete_anthropic(resolved, messages, api_key, xport, tools)
    if canonical == "openai":
        return _complete_openai(resolved, messages, api_key, xport, tools)
    return _complete_gemini(resolved, messages, api_key, xport, tools)
