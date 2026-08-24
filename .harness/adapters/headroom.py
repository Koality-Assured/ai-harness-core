"""HTTP client and fallback adapter for Headroom compression proxy."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:
    from ..config import HarnessConfig, HeadroomAdapterConfig
except (ImportError, ValueError):
    _HARNESS_ROOT = Path(__file__).resolve().parents[1]
    if str(_HARNESS_ROOT) not in sys.path:
        sys.path.insert(0, str(_HARNESS_ROOT))
    from config import HarnessConfig, HeadroomAdapterConfig

CHARS_PER_TOKEN = 4.0


class HeadroomError(RuntimeError):
    """Base error for Headroom compression operations."""


@dataclass
class HeadroomCompressResult:
    """Result of message compression from Headroom proxy or local engine."""

    messages: list[dict[str, Any]]
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    compression_ratio: float
    transforms_applied: list[str] = field(default_factory=list)
    proxy_used: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)


class HeadroomAdapter:
    """Adapter for interacting with Headroom proxy on port 8787 or in-process engine."""

    def __init__(
        self,
        config: HeadroomAdapterConfig | HarnessConfig | None = None,
        base_url: str | None = None,
        port: int | None = None,
        timeout_sec: float | None = None,
        enabled: bool = True,
    ) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.adapters.headroom
        elif isinstance(config, HeadroomAdapterConfig):
            self.config = config
        else:
            self.config = HeadroomAdapterConfig()

        self.port = port if port is not None else self.config.port
        self.base_url = (base_url or self.config.base_url).rstrip("/")
        self.timeout_sec = timeout_sec if timeout_sec is not None else float(self.config.timeout_sec)
        self.enabled = enabled and self.config.enabled

    @staticmethod
    def est_tokens(text: str) -> int:
        """Estimate tokens using chars/4 standard heuristic."""
        if not text:
            return 0
        return max(1, int(round(len(text) / CHARS_PER_TOKEN)))

    def is_healthy(self) -> bool:
        """Check if Headroom compression HTTP server is running and healthy."""
        if not self.enabled:
            return False

        endpoints = [f"{self.base_url}/health", f"{self.base_url}/"]
        for url in endpoints:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=min(2.0, self.timeout_sec)) as resp:
                    if resp.status in {200, 204}:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                continue
        return False

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        model: str = "gpt-4o",
        threshold_tokens: int | None = None,
        fallback_local: bool = True,
    ) -> HeadroomCompressResult:
        """Compress messages via HTTP proxy or local headroom module fallback."""
        if not self.enabled or not messages:
            raw_dump = json.dumps(messages) if messages else ""
            tokens = self.est_tokens(raw_dump) if messages else 0
            return HeadroomCompressResult(
                messages=messages,
                tokens_before=tokens,
                tokens_after=tokens,
                tokens_saved=0,
                compression_ratio=0.0,
                transforms_applied=[],
                proxy_used=False,
            )

        # Estimate tokens before
        raw_dump = json.dumps(messages)
        est_before = self.est_tokens(raw_dump)

        if threshold_tokens and est_before < threshold_tokens:
            return HeadroomCompressResult(
                messages=messages,
                tokens_before=est_before,
                tokens_after=est_before,
                tokens_saved=0,
                compression_ratio=0.0,
                transforms_applied=[],
                proxy_used=False,
            )

        # 1. Try HTTP Proxy
        try:
            payload = json.dumps({"messages": messages, "model": model}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/compress",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    compressed_msgs = data.get("messages", messages)
                    tok_before = int(data.get("tokens_before", est_before))
                    tok_after = int(data.get("tokens_after", self.est_tokens(json.dumps(compressed_msgs))))
                    tok_saved = int(data.get("tokens_saved", max(0, tok_before - tok_after)))
                    ratio = float(data.get("compression_ratio", round(tok_saved / max(1, tok_before), 4)))
                    transforms = list(data.get("transforms_applied", ["proxy_compress"]))

                    return HeadroomCompressResult(
                        messages=compressed_msgs,
                        tokens_before=tok_before,
                        tokens_after=tok_after,
                        tokens_saved=tok_saved,
                        compression_ratio=ratio,
                        transforms_applied=transforms,
                        proxy_used=True,
                    )
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            pass

        # 2. Fallback to in-process python headroom module
        if fallback_local:
            try:
                import headroom  # type: ignore

                result = headroom.compress(messages, model=model)
                transforms = list(getattr(result, "transforms_applied", []) or [])
                return HeadroomCompressResult(
                    messages=result.messages,
                    tokens_before=result.tokens_before,
                    tokens_after=result.tokens_after,
                    tokens_saved=result.tokens_saved,
                    compression_ratio=float(result.compression_ratio),
                    transforms_applied=transforms,
                    proxy_used=False,
                )
            except (ImportError, Exception):
                pass

        # 3. Graceful fallback: return uncompressed
        return HeadroomCompressResult(
            messages=messages,
            tokens_before=est_before,
            tokens_after=est_before,
            tokens_saved=0,
            compression_ratio=0.0,
            transforms_applied=[],
            proxy_used=False,
        )

    def compress_tool_output(
        self,
        tool_name: str,
        raw_output: str,
        model: str = "gpt-4o",
    ) -> tuple[str, HeadroomCompressResult]:
        """Wrap tool output in message format, compress it, and unpack."""
        messages = [
            {"role": "user", "content": "Run tool"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": tool_name, "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": raw_output},
        ]
        res = self.compress_messages(messages, model=model)
        for msg in res.messages:
            if msg.get("role") == "tool" and msg.get("tool_call_id") == "c1":
                return str(msg.get("content", raw_output)), res

        return raw_output, res
