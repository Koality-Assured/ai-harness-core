"""Slash-command registry shared by the harness REPL and `harness commands`.

tags: [harness, cli, slash, commands, registry]
routing_hints: [slash, commands, help, status, model, sessions, compact, context, thinking, effort, title, busy, permissions, quit]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CommandDef:
    name: str
    summary: str


BUILTIN_COMMANDS: tuple[CommandDef, ...] = (
    CommandDef("help", "List available slash commands"),
    CommandDef("status", "Show active session provider, model, and cwd"),
    CommandDef("model", "Show or set the session model (usage: /model <id>)"),
    CommandDef("sessions", "List recent sessions"),
    CommandDef("compact", "Summarize middle turns into a new session"),
    CommandDef("context", "Show context usage and configure auto-compaction (usage: /context [auto-compact <pct>])"),
    CommandDef("thinking", "Show or set thinking/reasoning budget (usage: /thinking off|low|medium|high|xhigh|<budget>)"),
    CommandDef("effort", "Show or set reasoning effort (usage: /effort low|medium|high|xhigh)"),
    CommandDef("title", "Rename the active session (usage: /title <text>)"),
    CommandDef("busy", "Show or set busy input mode: interrupt, queue, or steer"),
    CommandDef("preset", "Show or switch system preset (usage: /preset <name>)"),
    CommandDef("system", "Show or set custom system prompt (usage: /system <prompt>)"),
    CommandDef("mcp", "Inspect or reload MCP servers (/mcp list|tools|reload)"),
    CommandDef("permissions", "Show or set tool execution permission mode (usage: /permissions ask|auto-edit|yolo)"),
    CommandDef("quit", "Exit the interactive REPL"),
)


def builtin_commands() -> tuple[CommandDef, ...]:
    return BUILTIN_COMMANDS


def list_commands() -> list[dict[str, str]]:
    return [asdict(c) for c in BUILTIN_COMMANDS]


def parse_slash(line: str) -> tuple[str, str] | None:
    """Parse a slash command line into (name, arg) or None if not a slash command."""
    text = (line or "").strip()
    if not text.startswith("/"):
        return None
    body = text[1:].strip()
    if not body:
        return ("", "")
    if " " in body:
        name, arg = body.split(" ", 1)
        return (name.lower(), arg.strip())
    return (body.lower(), "")
