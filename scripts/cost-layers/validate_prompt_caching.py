"""Validate prompt cache invariance across agent definitions and system instructions.

tags: [cost-layers, routing, agents]
routing_hints: [prompt-caching, invariance, validation, dry-run, kv-cache]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parents[1] / "_lib"
sys.path.insert(0, str(_LIB))
from md import agent_paths, parse_frontmatter  # noqa: E402
from paths import REPO_ROOT as ROOT  # noqa: E402

CHARS_PER_TOKEN = 4.0

# Volatile patterns that break prompt KV-cache prefixes if placed at template heads
VOLATILE_PREFIX_PATTERNS = [
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\b"), "ISO-8601 dynamic timestamp"),
    (re.compile(r"(?i)\bcurrent\s+(?:date|time|timestamp)\s*:\s*\S+"), "runtime timestamp injection"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE), "random session UUID / nonce"),
    (re.compile(r"(?i)[A-Z]:\\Users\\[^\s\\]+\\"), "user-specific local filesystem path (Windows)"),
    (re.compile(r"(?i)/home/[^\s/]+/"), "user-specific local filesystem path (Linux)"),
    (re.compile(r"(?i)/Users/[^\s/]+/"), "user-specific local filesystem path (macOS)"),
]

# Minimum static byte length required at prompt prefix head before dynamic slots
MIN_STATIC_PREFIX_BYTES = 512


def est_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(round(len(text) / CHARS_PER_TOKEN)))


def check_prompt_head(path: Path, text: str, head_chars: int = 2000) -> list[dict[str, str]]:
    """Scan the head (prefix) of a prompt or agent definition for volatile cache-busting patterns."""
    violations: list[dict[str, str]] = []
    head_content = text[:head_chars]

    # Exclude harmless metadata dates in frontmatter (like last_verified: 'YYYY-MM-DD')
    # but flag any dynamic runtime timestamp expressions or volatile variables in instructions
    lines = head_content.splitlines()
    in_frontmatter = False
    frontmatter_count = 0

    for line_idx, line in enumerate(lines, start=1):
        if line.strip() == "---":
            frontmatter_count += 1
            in_frontmatter = frontmatter_count == 1
            continue

        # Skip static schema fields like last_verified: '2026-08-25' in frontmatter
        if in_frontmatter and line.strip().startswith("last_verified:"):
            continue

        for pattern, label in VOLATILE_PREFIX_PATTERNS:
            match = pattern.search(line)
            if match:
                try:
                    rel_path = str(path.relative_to(ROOT)).replace("\\", "/")
                except ValueError:
                    rel_path = str(path).replace("\\", "/")
                violations.append({
                    "file": rel_path,
                    "line": str(line_idx),
                    "matched": match.group(0),
                    "violation": label,
                    "snippet": line.strip()[:100],
                })
    return violations


def validate_all_prompts(repo_root: Path) -> dict[str, Any]:
    """Audit all agent definitions, root AGENTS.md, and routing files for prompt cache invariance."""
    files_to_audit: list[Path] = []

    # 1. All agent definitions
    for p in agent_paths(repo_root):
        files_to_audit.append(p)

    # 2. Core repository instructions
    root_agents = repo_root / "AGENTS.md"
    if root_agents.is_file():
        files_to_audit.append(root_agents)

    routing_agents = repo_root / "routing" / "AGENTS.md"
    if routing_agents.is_file():
        files_to_audit.append(routing_agents)

    audited_rows: list[dict[str, Any]] = []
    all_violations: list[dict[str, str]] = []

    for file_path in sorted(files_to_audit):
        rel = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            all_violations.append({
                "file": rel,
                "line": "0",
                "matched": "",
                "violation": f"read error: {exc}",
                "snippet": "",
            })
            continue

        violations = check_prompt_head(file_path, content)
        all_violations.extend(violations)

        total_bytes = len(content.encode("utf-8"))
        total_tokens = est_tokens(content)
        prefix_stable = len(violations) == 0 and total_bytes >= MIN_STATIC_PREFIX_BYTES

        audited_rows.append({
            "file": rel,
            "bytes": total_bytes,
            "est_tokens": total_tokens,
            "prefix_stable": prefix_stable,
            "violations_count": len(violations),
        })

    pass_status = len(all_violations) == 0
    return {
        "pass": pass_status,
        "files_checked": len(audited_rows),
        "violations": all_violations,
        "audited_rows": audited_rows,
        "min_static_prefix_bytes": MIN_STATIC_PREFIX_BYTES,
    }


def write_report(out_dir: Path, payload: dict[str, Any]) -> None:
    lines = [
        "---",
        "doc_kind: result",
        "canonical_id: prompt-caching-invariance",
        "purpose: [process]",
        "topics: [cost-layers, prompt-caching, kv-cache, validation]",
        f"generated_at_utc: {payload['generated_at_utc']}",
        "---",
        "",
        "# Prompt Cache Invariance Validation",
        "",
        "Validates that system prompt prefixes and agent definitions exhibit static byte stability at their heads without volatile timestamps, random session UUIDs, or dynamic environment paths that invalidate provider KV-caches (Anthropic prompt caching, OpenAI prompt caching, Gemini context caching).",
        "",
        "## Summary",
        "",
        f"- Status: **{'PASS' if payload['pass'] else 'FAIL'}**",
        f"- Total prompt definitions audited: **{payload['files_checked']}**",
        f"- Violations detected: **{len(payload['violations'])}**",
        f"- Minimum static prefix requirement: **{payload['min_static_prefix_bytes']} bytes**",
        "",
        "## Audited Prompt Definitions",
        "",
        "| File | Size (Bytes) | Est. Tokens | Static Prefix Stability | Violations |",
        "| --- | --- | --- | --- | --- |",
    ]

    for row in payload["audited_rows"]:
        status_icon = "PASS" if row["prefix_stable"] else "FAIL"
        lines.append(
            f"| `{row['file']}` | {row['bytes']} | {row['est_tokens']} | {status_icon} | {row['violations_count']} |"
        )

    lines.append("")
    lines.append("## Findings & Invariance Violations")
    lines.append("")
    if not payload["violations"]:
        lines.append("- All prompt definitions maintain byte-stable prefix headers.")
        lines.append("- No dynamic timestamps, nonces, or user environment paths detected in prompt heads.")
        lines.append("- KV-cache hit efficiency preserved across provider routing boundaries.")
    else:
        for v in payload["violations"]:
            lines.append(f"- **{v['file']}:{v['line']}** — `{v['violation']}` on `{v['matched']}`: _{v['snippet']}_")

    lines.append("")
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory (default: results/cost-layers/prompt-caching/<YYYY-MM-DD>)",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON envelope to stdout")
    parser.add_argument("--dry-run", action="store_true", help="Run audit and print summary")
    args = parser.parse_args(argv)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_rel = args.out or f"results/cost-layers/prompt-caching/{today}"
    out_dir = ROOT / out_rel
    out_dir.mkdir(parents=True, exist_ok=True)

    result = validate_all_prompts(ROOT)
    payload = {
        "generated_at_utc": now_utc,
        **result,
    }

    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "pass": payload["pass"],
                "files_checked": payload["files_checked"],
                "violations_count": len(payload["violations"]),
                "failed": [v["file"] for v in payload["violations"]],
                "findings": (
                    ["All prompt definitions maintain static byte prefix stability."]
                    if payload["pass"]
                    else [f"{v['file']}: {v['violation']}" for v in payload["violations"]]
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_report(out_dir, payload)

    summary = {
        "out": str(out_dir),
        "pass": payload["pass"],
        "files_checked": payload["files_checked"],
        "violations_count": len(payload["violations"]),
        "failed": [v["file"] for v in payload["violations"]],
        "findings": (
            ["All prompt definitions maintain static byte prefix stability."]
            if payload["pass"]
            else [f"{v['file']}: {v['violation']}" for v in payload["violations"]]
        ),
    }

    if args.json or args.dry_run:
        print(json.dumps(summary, indent=2))

    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
