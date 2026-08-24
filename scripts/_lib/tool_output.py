"""Tool output formatting, truncation, and compression helper.

Provides reusable context-protection functions for CLI scripts and agent runners
to prevent token ballooning from bulky tool dumps, build logs, and test outputs.

tags: [tooling, cost-layers, headroom, compression]
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# GPT-family token estimate heuristic
CHARS_PER_TOKEN = 4.0

ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

ERROR_PATTERNS = [
    re.compile(r"^\s*(?:ERROR|FATAL|EXCEPTION|CRITICAL|Traceback)\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:fatal error|unhandled exception|segmentation fault|panic:)\b"),
    re.compile(r"^\s*File \".*\", line \d+"),
    re.compile(r"^\s*at .*\(\w+:\d+:\d+\)"),
]

NON_ERROR_DIFF_PREFIXES = ("+++", "---", "+", "-", "@@")


def estimate_tokens(text: str) -> int:
    """Estimate token count using the chars/4 heuristic."""
    return int(len(text) / CHARS_PER_TOKEN)


def extract_error_lines(lines: list[str], max_error_lines: int = 20) -> list[str]:
    """Identify and preserve genuine error/exception lines from output."""
    found: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip diff markers and common code assignments
        if any(stripped.startswith(p) for p in NON_ERROR_DIFF_PREFIXES):
            continue
        if any(pat.search(line) for pat in ERROR_PATTERNS):
            found.append(line)
            if len(found) >= max_error_lines:
                break
    return found


def truncate_output(
    text: str,
    max_lines: int = 100,
    max_chars: int = 8000,
    head_lines: int = 40,
    tail_lines: int = 40,
    preserve_errors: bool = True,
) -> str:
    """Truncate bulky text to protect the context window while preserving key signals.

    Keeps the head lines, tail lines, and significant error signatures.
    """
    if not text:
        return ""

    lines = text.splitlines()
    if len(lines) <= max_lines and len(text) <= max_chars:
        return text

    head = lines[:head_lines]
    tail = lines[-tail_lines:] if tail_lines > 0 else []

    middle_lines = lines[head_lines:-tail_lines] if tail_lines > 0 else lines[head_lines:]
    omitted_count = len(middle_lines)

    error_snippet: list[str] = []
    if preserve_errors and omitted_count > 0:
        errs = extract_error_lines(middle_lines)
        if errs:
            error_snippet = [
                f"\n[... {len(errs)} error signature line(s) detected in omitted section ...]",
                *errs[:10],
            ]

    summary_marker = f"\n[... {omitted_count} lines ({len(text)} chars) omitted for context economy ...]"

    truncated_blocks = head + [summary_marker] + error_snippet + [""] + tail
    result = "\n".join(truncated_blocks)

    # Hard cap if individual lines were unusually long
    if len(result) > max_chars:
        result = result[: max_chars - 100] + f"\n[... truncated at {max_chars} chars ...]"

    return result


def compress_via_headroom(
    text: str,
    proxy_url: str = "http://127.0.0.1:8787",
    timeout_sec: float = 1.0,
) -> tuple[str, bool]:
    """Attempt compression via a local Headroom proxy instance.

    Returns (compressed_or_original_text, was_compressed).
    Fails open gracefully to original text on connection failure or timeout.
    """
    if not text or len(text) < 500:
        return text, False

    try:
        parsed = urllib.parse.urlparse(proxy_url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_LOCAL_HOSTS:
            # Reject non-loopback URLs to eliminate SSRF boundary
            return text, False
    except Exception:
        return text, False

    endpoint = f"{proxy_url.rstrip('/')}/compress"
    payload = json.dumps({"text": text}).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                compressed = data.get("text") or data.get("compressed_text")
                if compressed and len(compressed) < len(text):
                    return compressed, True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        pass

    return text, False


def format_tool_execution(
    stdout: str,
    stderr: str = "",
    exit_code: int = 0,
    max_lines: int = 80,
    try_headroom: bool = True,
) -> dict[str, Any]:
    """Format and compress a tool or CLI execution result for agent consumption."""
    raw_combined = stdout
    if stderr:
        raw_combined = f"{stdout}\n--- STDERR ---\n{stderr}".strip()

    compressed_text = raw_combined
    compressed_via_proxy = False

    if try_headroom:
        compressed_text, compressed_via_proxy = compress_via_headroom(raw_combined)

    final_text = truncate_output(compressed_text, max_lines=max_lines)

    return {
        "exit_code": exit_code,
        "output": final_text,
        "raw_chars": len(raw_combined),
        "output_chars": len(final_text),
        "est_raw_tokens": estimate_tokens(raw_combined),
        "est_output_tokens": estimate_tokens(final_text),
        "headroom_compressed": compressed_via_proxy,
    }


if __name__ == "__main__":
    sample = sys.stdin.read()
    if sample:
        result = format_tool_execution(sample)
        print(json.dumps(result, indent=2))
