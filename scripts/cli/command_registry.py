"""Slash-command registry shared by the harness REPL and `harness commands`.

tags: [harness, cli, slash, commands, registry]
routing_hints: [slash, commands, help, status, model, sessions, title, busy, quit]
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
    CommandDef("title", "Rename the active session (usage: /title <text>)"),
    CommandDef("busy", "Show or set busy input mode: interrupt, queue, or steer"),
    CommandDef("quit", "Exit the interactive REPL"),
)


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
