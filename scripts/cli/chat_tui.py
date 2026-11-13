"""Terminal User Interface (TUI) components for interactive harness chat.

Provides anchored status bar, slash-command and @file autocompletion,
rich markdown rendering, visual tool call/outcome banners, and session management.

tags: [harness, cli, tui, rich, prompt_toolkit, chat]
routing_hints: [chat_tui, completer, status_bar, render_markdown, render_diff, render_tool_call]
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable, Iterable

# Graceful optional imports for rich
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.markup import escape
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore[assignment,misc]
    Markdown = None  # type: ignore[assignment,misc]
    Panel = None  # type: ignore[assignment,misc]
    Syntax = None  # type: ignore[assignment,misc]
    Text = None  # type: ignore[assignment,misc]

    def escape(text: str) -> str:  # type: ignore[misc]
        return text


# Graceful optional imports for prompt_toolkit
try:
    from prompt_toolkit.completion import CompleteEvent, Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.shortcuts import PromptSession

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

    class Completer:  # type: ignore[no-redef]
        def get_completions(self, document: Any, complete_event: Any = None) -> Iterable[Any]:
            return []

    class Completion:  # type: ignore[no-redef]
        def __init__(
            self,
            text: str,
            start_position: int = 0,
            display: str | None = None,
            display_meta: str | None = None,
        ) -> None:
            self.text = text
            self.start_position = start_position
            self.display = display or text
            self.display_meta = display_meta or ""

    class Document:  # type: ignore[no-redef]
        def __init__(self, text: str = "", cursor_position: int | None = None) -> None:
            self.text = text
            self.cursor_position = len(text) if cursor_position is None else cursor_position

        @property
        def text_before_cursor(self) -> str:
            return self.text[: self.cursor_position]

        @property
        def current_line_before_cursor(self) -> str:
            lines = self.text_before_cursor.split("\n")
            return lines[-1] if lines else ""

    FileHistory = None  # type: ignore[assignment,misc]
    PromptSession = None  # type: ignore[assignment,misc]


def _enforce_private_dir(path: str) -> None:
    """Enforce strict user-only permissions on directory (0700 on POSIX, restricted ACLs on Windows)."""
    if not os.path.exists(path):
        return
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if user:
            try:
                import subprocess

                subprocess.run(
                    ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(OI)(CI)(F)"],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
    else:
        try:
            os.chmod(path, 0o700)
        except Exception:
            pass


def _enforce_private_file(path: str) -> None:
    """Enforce strict user-only permissions on file (0600 on POSIX, restricted ACLs on Windows)."""
    if not os.path.exists(path):
        return
    if os.name == "nt":
        user = os.environ.get("USERNAME")
        if user:
            try:
                import subprocess

                subprocess.run(
                    ["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:F"],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
    else:
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass


def format_status_bar(
    provider: str,
    model: str,
    thinking: str | int | None,
    context_pct: float | None,
    cost: float | str | None,
    mcp_count: int,
    permission_mode: str,
) -> str:
    """Format anchored status bar string.

    Returns: `[harness] [provider:model] [thinking: level] [ctx: X%] [$X.XXXX] [mcp: N] [mode: ask]`
    """
    prov = provider or "unknown"
    mod = model or "default"

    if thinking is None or str(thinking).strip().lower() in ("none", "", "off", "0"):
        thinking_disp = "off"
    else:
        thinking_disp = str(thinking).strip()

    if context_pct is None:
        ctx_disp = "0%"
    elif isinstance(context_pct, (int, float)):
        if float(context_pct).is_integer():
            ctx_disp = f"{int(context_pct)}%"
        else:
            ctx_disp = f"{context_pct:.1f}%"
    else:
        s = str(context_pct).strip()
        ctx_disp = s if s.endswith("%") else f"{s}%"

    if cost is None:
        cost_disp = "$0.0000"
    elif isinstance(cost, (int, float)):
        cost_disp = f"${float(cost):.4f}"
    elif isinstance(cost, str):
        c_str = cost.strip()
        if c_str.startswith("$"):
            cost_disp = c_str
        else:
            try:
                cost_disp = f"${float(c_str):.4f}"
            except ValueError:
                cost_disp = f"${c_str}"
    else:
        cost_disp = "$0.0000"

    mcp_disp = int(mcp_count) if mcp_count is not None else 0
    mode_disp = permission_mode or "ask"

    return (
        f"[harness] [{prov}:{mod}] [thinking: {thinking_disp}] "
        f"[ctx: {ctx_disp}] [{cost_disp}] [mcp: {mcp_disp}] [mode: {mode_disp}]"
    )


class HarnessCompleter(Completer):
    """Dynamic autocompletion for slash commands and workspace @file tokens.

    Includes in-memory cached file index with TTL, hard ceilings on disk walk,
    strict symlink containment, and start-of-token @ matching.
    """

    def __init__(self, workspace_root: str | None = None, cache_ttl: float = 20.0) -> None:
        self.workspace_root = workspace_root or os.getcwd()
        self._cache_ttl = cache_ttl
        self._cached_files: list[str] | None = None
        self._cache_time: float = 0.0

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory cached file index."""
        self._cached_files = None
        self._cache_time = 0.0

    def _get_workspace_files(self) -> list[str]:
        now = time.monotonic()
        if self._cached_files is not None and (now - self._cache_time) < self._cache_ttl:
            return self._cached_files

        root = os.path.abspath(self.workspace_root)
        real_root = os.path.realpath(root)
        ignored_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".pytest_cache",
            ".venv",
            "venv",
            ".idea",
            ".vscode",
        }

        all_files: list[str] = []
        scanned_count = 0

        if os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [
                    d for d in dirnames if not d.startswith(".") and d not in ignored_dirs
                ]
                rel_dir = os.path.relpath(dirpath, root)
                if rel_dir != "." and len(rel_dir.split(os.sep)) > 10:
                    dirnames.clear()
                    continue

                for fname in filenames:
                    scanned_count += 1
                    if scanned_count > 1000:
                        dirnames.clear()
                        break

                    if fname.startswith("."):
                        continue

                    full_path = os.path.join(dirpath, fname)
                    try:
                        # Symlink safety: resolve real path and verify workspace containment
                        real_path = os.path.realpath(full_path)
                        if os.path.commonpath([real_root, real_path]) != real_root:
                            continue
                    except (ValueError, OSError):
                        continue

                    rel_path = os.path.relpath(full_path, root).replace("\\", "/")
                    all_files.append(rel_path)
                    if len(all_files) >= 1000:
                        dirnames.clear()
                        break

                if scanned_count > 1000 or len(all_files) >= 1000:
                    break

        self._cached_files = all_files
        self._cache_time = now
        return all_files

    def get_completions(self, document: Any, complete_event: Any = None) -> Iterable[Completion]:
        text_before = getattr(document, "text_before_cursor", "") or ""
        line_before = getattr(document, "current_line_before_cursor", "") or ""

        # 1. Slash commands: when input begins with / and no arguments have been typed yet
        lstripped = text_before.lstrip()
        if lstripped.startswith("/") and " " not in lstripped:
            try:
                from cli.command_registry import builtin_commands

                cmds = builtin_commands()
            except Exception:
                try:
                    from cli.command_registry import BUILTIN_COMMANDS

                    cmds = BUILTIN_COMMANDS
                except Exception:
                    cmds = ()

            query = lstripped.lower()
            for cmd in cmds:
                name = getattr(cmd, "name", "")
                summary = getattr(cmd, "summary", "")
                full_cmd = f"/{name}"
                if full_cmd.lower().startswith(query):
                    yield Completion(
                        text=full_cmd,
                        start_position=-len(lstripped),
                        display=full_cmd,
                        display_meta=summary,
                    )

        # 2. @... file paths: ONLY trigger if the current word starts with @
        last_ws = max(line_before.rfind(" "), line_before.rfind("\t"))
        current_word = line_before[last_ws + 1 :] if last_ws >= 0 else line_before

        if current_word.startswith("@"):
            token_to_replace = current_word  # e.g. "@README" or "@scripts/cli/"
            file_prefix = token_to_replace[1:]  # e.g. "README" or "scripts/cli/"
            norm_prefix = file_prefix.replace("\\", "/")
            prefix_lower = norm_prefix.lower()

            all_files = self._get_workspace_files()
            matches: list[str] = []

            if "/" in norm_prefix:
                for rel in all_files:
                    if rel.lower().startswith(prefix_lower):
                        matches.append(rel)
            else:
                for rel in all_files:
                    if rel.lower().startswith(prefix_lower) or os.path.basename(rel).lower().startswith(
                        prefix_lower
                    ):
                        matches.append(rel)

            # Sort matches: shorter directory depth first, then alphabetical
            matches.sort(key=lambda p: (len(p.split("/")), p.lower()))
            matches = matches[:50]

            for rel in matches:
                comp = Completion(
                    text=f"@{rel}",
                    start_position=-len(token_to_replace),
                    display=rel,
                    display_meta="file",
                )
                setattr(comp, "path", rel)
                setattr(comp, "rel_path", rel)
                yield comp


def render_markdown(text: str, console: Any = None) -> None:
    """Renders formatted markdown using rich if available, otherwise prints plain text."""
    if not text:
        return
    if RICH_AVAILABLE:
        try:
            c = console if console is not None else Console()
            c.print(Markdown(text))
            return
        except Exception:
            pass
    print(text)


def render_diff(diff_text: str | None, console: Any = None) -> None:
    """Colors diff lines (green for additions +, red for deletions -, cyan for chunks @@)."""
    if not diff_text or not isinstance(diff_text, str):
        return

    all_lines = diff_text.splitlines()
    max_lines = 150
    truncated = len(all_lines) > max_lines
    lines = all_lines[:max_lines]

    if RICH_AVAILABLE:
        try:
            c = console if console is not None else Console()
            text_obj = Text()
            for line in lines:
                if line.startswith("+++"):
                    text_obj.append(line + "\n", style="bold green")
                elif line.startswith("---"):
                    text_obj.append(line + "\n", style="bold red")
                elif line.startswith("+"):
                    text_obj.append(line + "\n", style="green")
                elif line.startswith("-"):
                    text_obj.append(line + "\n", style="red")
                elif line.startswith("@@"):
                    text_obj.append(line + "\n", style="cyan")
                else:
                    text_obj.append(line + "\n", style="dim")
            if truncated:
                text_obj.append(
                    f"... ({len(all_lines) - max_lines} lines truncated)\n",
                    style="dim yellow",
                )
            c.print(text_obj)
            return
        except Exception:
            pass

    # ANSI fallback
    for line in lines:
        if line.startswith("+++"):
            print(f"\033[1;32m{line}\033[0m")
        elif line.startswith("---"):
            print(f"\033[1;31m{line}\033[0m")
        elif line.startswith("+"):
            print(f"\033[32m{line}\033[0m")
        elif line.startswith("-"):
            print(f"\033[31m{line}\033[0m")
        elif line.startswith("@@"):
            print(f"\033[36m{line}\033[0m")
        else:
            print(line)
    if truncated:
        print(f"\033[33m... ({len(all_lines) - max_lines} lines truncated)\033[0m")


def render_tool_call(name: str, arguments: dict[str, Any], console: Any = None) -> None:
    """Renders a clear visual panel or banner showing the tool call and arguments."""
    try:
        args_str = json.dumps(arguments or {}, indent=2, ensure_ascii=False)
    except Exception:
        args_str = str(arguments)

    safe_name = escape(str(name))

    if RICH_AVAILABLE:
        try:
            c = console if console is not None else Console()
            syntax = Syntax(args_str, "json", theme="monokai", word_wrap=True)
            panel = Panel(
                syntax,
                title=f"[bold cyan]Tool Call: {safe_name}[/bold cyan]",
                border_style="cyan",
                expand=False,
            )
            c.print(panel)
            return
        except Exception:
            pass

    print(f"\n>>> [Tool Call: {name}]")
    if arguments:
        print(args_str)
    print("<<<")


def render_tool_outcome(
    name: str,
    outcome_summary: str,
    is_error: bool = False,
    console: Any = None,
) -> None:
    """Renders visual outcome indicator for a tool execution."""
    safe_name = escape(str(name))
    safe_summary = escape(str(outcome_summary))

    if RICH_AVAILABLE:
        try:
            c = console if console is not None else Console()
            # Enforce encoding safety for non-utf8 consoles (e.g. Windows cp1252)
            try:
                target_file = getattr(c, "file", None)
                encoding = getattr(target_file, "encoding", None) or sys.stdout.encoding or "utf-8"
                "✓✗".encode(encoding)
                symbol = "✗" if is_error else "✓"
            except (UnicodeEncodeError, LookupError, AttributeError):
                symbol = "[FAIL]" if is_error else "[OK]"

            if is_error:
                c.print(f"[bold red]{symbol} {safe_name}[/bold red]: {safe_summary}")
            else:
                c.print(f"[bold green]{symbol} {safe_name}[/bold green]: {safe_summary}")
            return
        except Exception:
            pass

    tag = "[ERROR]" if is_error else "[OK]"
    color = "\033[31m" if is_error else "\033[32m"
    reset = "\033[0m"
    print(f"{color}{tag} {name}{reset}: {outcome_summary}")


class ChatTUISession:
    """Session Manager creating and managing prompt_toolkit.PromptSession with fallback."""

    def __init__(
        self,
        workspace_root: str | None = None,
        status_callback: Callable[[], str] | None = None,
        input_fn: Callable[[str], str] | None = None,
    ) -> None:
        self.workspace_root = workspace_root or os.getcwd()
        self.status_callback = status_callback
        self.fallback_input_fn = input_fn
        self._session: Any = None
        self.is_active: bool = False
        self._init_session()

    def _init_session(self) -> None:
        if not PROMPT_TOOLKIT_AVAILABLE:
            self.is_active = False
            return

        # Terminal sanity check: both stdin and stdout must report as interactive TTY
        if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
            self.is_active = False
            return
        if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
            self.is_active = False
            return

        try:
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.shortcuts import PromptSession

            history_path = os.path.expanduser("~/.harness/chat_history")
            history_dir = os.path.dirname(history_path)
            try:
                os.makedirs(history_dir, exist_ok=True)
                _enforce_private_dir(history_dir)
                _enforce_private_file(history_path)
                history = FileHistory(history_path)
            except Exception:
                history = None

            def get_toolbar_text() -> str:
                if self.status_callback is not None:
                    try:
                        return self.status_callback()
                    except Exception:
                        return ""
                return ""

            completer = HarnessCompleter(workspace_root=self.workspace_root)
            self._session = PromptSession(
                completer=completer,
                bottom_toolbar=get_toolbar_text,
                history=history,
                multiline=False,
            )
            self.is_active = True
        except Exception:
            self._session = None
            self.is_active = False

    def prompt(self, message: str = "> ", store_history: bool = True) -> str:
        """Prompt user for input using prompt_toolkit or fallback."""
        if self.is_active and self._session is not None:
            try:
                return self._session.prompt(message, store_history=store_history)
            except (EOFError, KeyboardInterrupt):
                raise
            except Exception:
                # Downgrade on terminal error during prompt
                self.is_active = False
                self._session = None

        if self.fallback_input_fn is not None:
            return self.fallback_input_fn(message)
        return input(message)
