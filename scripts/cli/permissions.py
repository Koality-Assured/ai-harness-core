"""Tool execution permission policies and tool classification.

tags: [harness, cli, permissions, policy, security]
routing_hints: [permissions, policy, ask, auto-edit, yolo, tool-approval]
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Callable, Literal

PermissionModeLiteral = Literal["ask", "auto-edit", "yolo"]


class PermissionMode(str, Enum):
    ASK = "ask"
    AUTO_EDIT = "auto-edit"
    YOLO = "yolo"


READ_ONLY_EXACT = frozenset({
    "read_file",
    "list_dir",
    "grep_search",
    "ast_outline",
    "ask_question",
    "qmd_search",
    "qmd_vsearch",
    "qmd_query",
    "qmd_get",
    "qmd_multi_get",
    "qmd_status",
})

EDIT_EXACT = frozenset({
    "edit_file",
    "write_file",
})

DANGEROUS_UNSCOPED_TOOLS = frozenset({
    "run_command",
    "bash",
    "exec",
    "eval",
})


def classify_tool(name: str) -> str:
    """Classify tool name into 'read_only', 'edit', or 'command'."""
    tool = (name or "").strip().lower()
    if tool in READ_ONLY_EXACT:
        return "read_only"
    if tool in EDIT_EXACT:
        return "edit"
    return "command"


def _extract_command_argument(arguments: dict[str, Any] | None) -> str:
    """Extract command string from arguments for dangerous tool scoping."""
    if not isinstance(arguments, dict):
        return ""
    for key in ("command", "cmd", "script", "code"):
        val = arguments.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    try:
        return json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(arguments)


class PermissionPolicy:
    """Policy governing whether tool executions are auto-approved, prompted, or denied."""

    def __init__(self, mode: str = "ask", is_interactive: bool = True) -> None:
        self.mode = mode.lower() if isinstance(mode, str) else str(mode)
        self.is_interactive = bool(is_interactive)
        self.session_allowed: set[str | tuple[str, str]] = set()

    def check_permission(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        prompt_callback: Callable[..., Any] | None = None,
    ) -> tuple[bool, str | None]:
        tool_name = (name or "").strip().lower()
        category = classify_tool(tool_name)
        args = arguments if arguments is not None else {}

        if self.mode == "yolo":
            return (True, None)

        if tool_name in DANGEROUS_UNSCOPED_TOOLS:
            cmd_arg = _extract_command_argument(args)
            if (tool_name, cmd_arg) in self.session_allowed:
                return (True, None)
        elif tool_name in self.session_allowed:
            return (True, None)

        if category == "read_only":
            return (True, None)

        if self.mode == "auto-edit" and category == "edit":
            return (True, None)

        if not self.is_interactive:
            return (
                False,
                f"Tool '{name}' requires interactive confirmation; run interactively or with --permissions yolo.",
            )

        if prompt_callback is not None:
            try:
                result = prompt_callback(name, args)
            except TypeError:
                result = prompt_callback(name)

            if isinstance(result, tuple):
                decision = result[0]
                feedback = result[1] if len(result) > 1 else None
            else:
                decision = result
                feedback = None

            decision_str = str(decision).lower() if decision is not None else "deny"

            if decision_str == "allow_session":
                if tool_name in DANGEROUS_UNSCOPED_TOOLS:
                    cmd_arg = _extract_command_argument(args)
                    self.session_allowed.add((tool_name, cmd_arg))
                else:
                    self.session_allowed.add(tool_name)
                return (True, None)
            if decision_str == "allow_once":
                return (True, None)
            if decision_str == "deny":
                return (False, feedback or f"Execution of tool '{name}' was denied by user.")
            return (False, feedback or f"Execution of tool '{name}' was denied by user.")

        return (
            False,
            f"Tool '{name}' requires interactive confirmation; run interactively or with --permissions yolo.",
        )
