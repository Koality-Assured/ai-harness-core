"""Interactive Terminal User Interface (TUI) and Harness Switcher.

Provides zero-external-dependency terminal interaction for discovering,
inspecting, and switching between domain harnesses and repositories.

tags: [harness, cli, tui, switcher, interactive]
routing_hints: [harness, tui, switcher, switch, menu]
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from cli.registry import HarnessRegistry, get_registry


class TerminalUI:
    """Zero-dependency terminal UI renderer with ANSI color support."""

    def __init__(self, use_color: bool | None = None) -> None:
        if use_color is not None:
            self.use_color = use_color
        else:
            # Respect NO_COLOR standard (https://no-color.org/) and TTY presence
            no_color = bool(os.environ.get("NO_COLOR"))
            is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
            self.use_color = is_tty and not no_color

    def bold(self, text: str) -> str:
        return f"\033[1m{text}\033[0m" if self.use_color else text

    def green(self, text: str) -> str:
        return f"\033[32m{text}\033[0m" if self.use_color else text

    def cyan(self, text: str) -> str:
        return f"\033[36m{text}\033[0m" if self.use_color else text

    def yellow(self, text: str) -> str:
        return f"\033[33m{text}\033[0m" if self.use_color else text

    def magenta(self, text: str) -> str:
        return f"\033[35m{text}\033[0m" if self.use_color else text

    def red(self, text: str) -> str:
        return f"\033[31m{text}\033[0m" if self.use_color else text

    def dim(self, text: str) -> str:
        return f"\033[2m{text}\033[0m" if self.use_color else text


def format_harnesses_table(harnesses: list[dict[str, Any]], ui: TerminalUI | None = None) -> str:
    """Render a formatted ASCII/ANSI table of registered domain harnesses."""
    ui = ui or TerminalUI()
    lines: list[str] = []

    header = f"=== Registered AI Domain Harnesses ({len(harnesses)}) ==="
    lines.append(ui.bold(header))

    if not harnesses:
        lines.append(ui.yellow("\n  (No harnesses registered yet. Run 'harness scan' or 'harness register <path>').\n"))
        return "\n".join(lines)

    # Columns: Index | Active | ID / Name | Branch | Status | Worktrees | Domain | Path
    lines.append("")
    hdr_line = (
        f"  {'#':<4} {'Act':<5} {'Harness ID':<22} {'Branch':<20} "
        f"{'Status':<8} {'WkTrs':<7} {'Domain'}"
    )
    lines.append(ui.bold(hdr_line))
    lines.append("  " + "-" * (min(100, shutil.get_terminal_size((100, 20)).columns - 4)))

    for idx, h in enumerate(harnesses, start=1):
        is_active = h.get("is_active", False)
        active_mark = ui.green("* YES") if is_active else ui.dim("  no")
        hid = h.get("id", "")
        if is_active:
            hid_display = ui.bold(ui.cyan(hid))
        else:
            hid_display = hid

        live = h.get("live", {})
        branch = live.get("branch", "(unknown)")
        if len(branch) > 18:
            branch = branch[:16] + ".."

        status = live.get("status", "UNKNOWN")
        if status == "CLEAN":
            status_display = ui.green("CLEAN")
        elif status == "DIRTY":
            status_display = ui.yellow("DIRTY")
        elif status == "MISSING":
            status_display = ui.red("MISSING")
        else:
            status_display = ui.dim(status)

        wts = str(live.get("worktrees_count", 0))
        domain = h.get("domain", "")
        if len(domain) > 35:
            domain = domain[:33] + ".."

        idx_str = f"[{idx}]"
        row = (
            f"  {idx_str:<4} {active_mark:<14} {hid_display:<31} {branch:<20} "
            f"{status_display:<17} {wts:<7} {domain}"
        )
        lines.append(row)
        path_str = ui.dim(f"       -> {h.get('path', '')}")
        lines.append(path_str)

    lines.append("")
    return "\n".join(lines)


def run_switcher_tui(registry: HarnessRegistry | None = None) -> int:
    """Launch the interactive terminal UI switcher loop."""
    reg = registry or get_registry()
    ui = TerminalUI()

    # If non-interactive stdin, render table and return 0 without blocking
    if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
        harnesses = reg.list_harnesses()
        print(format_harnesses_table(harnesses, ui))
        return 0

    while True:
        harnesses = reg.list_harnesses()
        # Clear screen on ANSI terminals if possible
        if ui.use_color:
            print("\033[2J\033[H", end="")

        print(format_harnesses_table(harnesses, ui))

        print(ui.bold("Actions:"))
        print(f"  {ui.cyan('[1-' + str(len(harnesses)) + ']')} Switch active harness")
        print(f"  {ui.cyan('[s]')}     Scan sibling repositories for harnesses")
        print(f"  {ui.cyan('[r]')}     Refresh view")
        print(f"  {ui.cyan('[q]')}     Quit switcher")
        print()

        try:
            choice = input(ui.bold("Select option > ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting switcher.")
            return 0

        if not choice or choice.lower() in ("q", "quit", "exit"):
            return 0

        if choice.lower() in ("r", "refresh"):
            continue

        if choice.lower() in ("s", "scan"):
            print("\nScanning sibling directories for domain harnesses...")
            discovered = reg.scan_siblings(auto_register=True)
            print(f"Scan complete. Discovered/updated {len(discovered)} harness(es).")
            try:
                input("\nPress Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                return 0
            continue

        # Check numeric selection
        try:
            val = int(choice)
            if 1 <= val <= len(harnesses):
                selected = harnesses[val - 1]
                target_id = selected["id"]
                reg.switch(target_id)
                print(f"\n{ui.green('✓')} Active harness switched to: {ui.bold(target_id)} ({selected.get('path')})")
                try:
                    input("\nPress Enter to return to menu (or 'q' to exit)...")
                except (EOFError, KeyboardInterrupt):
                    return 0
            else:
                print(ui.red(f"Invalid selection: enter 1 through {len(harnesses)}."))
                try:
                    input("Press Enter to continue...")
                except (EOFError, KeyboardInterrupt):
                    return 0
        except ValueError:
            print(ui.red(f"Unrecognized command: '{choice}'."))
            try:
                input("Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                return 0

    return 0
