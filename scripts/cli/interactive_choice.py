"""Interactive terminal choice and modal helpers for conversational tools.

tags: [harness, cli, interactive, choice, ask_question]
routing_hints: [interactive_choice, prompt_choice, ask_question, options]
"""

from __future__ import annotations

import sys
from typing import Any, Callable


def _get_default_choice(options: list[Any]) -> list[str]:
    if not options:
        return []
    for opt in options:
        opt_str = str(opt)
        if "(recommended)" in opt_str.lower():
            return [opt_str]
    return [str(options[0])]


def prompt_choice(
    question: str,
    options: list[Any],
    is_multi_select: bool = False,
    input_fn: Callable[[str], str] = input,
    *,
    is_interactive: bool | None = None,
) -> list[str]:
    """Prompt user with numbered options and optional custom write-in.

    In non-interactive environments (or when is_interactive=False), immediately returns
    the recommended option (or the first option) without prompting.
    If options list is empty in interactive mode, prompts for free-text write-in.
    """
    # Non-interactive determination:
    non_interactive = False
    if is_interactive is False:
        non_interactive = True
    elif is_interactive is None and input_fn is input:
        if not (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()):
            non_interactive = True

    if not options:
        if non_interactive:
            return []
        print(f"\n{question}")
        try:
            raw = input_fn("Answer: ").strip()
        except (EOFError, StopIteration):
            return []
        return [raw] if raw else []

    if non_interactive:
        return _get_default_choice(options)

    opts_str = [str(opt) for opt in options]

    print(f"\n{question}")
    for idx, opt in enumerate(opts_str, 1):
        print(f"  [{idx}] {opt}")
    print("  [c] Custom answer")

    prompt_label = "Select option(s) (comma-separated): " if is_multi_select else "Select option: "

    while True:
        try:
            raw = input_fn(prompt_label).strip()
        except (EOFError, StopIteration):
            return _get_default_choice(opts_str)

        if not raw:
            return _get_default_choice(opts_str)

        if raw.lower() == "c":
            try:
                custom = input_fn("Custom answer: ").strip()
            except (EOFError, StopIteration):
                return _get_default_choice(opts_str)
            return [custom] if custom else _get_default_choice(opts_str)

        if is_multi_select:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            selected: list[str] = []
            has_custom = False
            valid = True
            for part in parts:
                if part.lower() == "c":
                    has_custom = True
                    continue
                try:
                    num = int(part)
                    if 1 <= num <= len(opts_str):
                        selected.append(opts_str[num - 1])
                    else:
                        valid = False
                        break
                except ValueError:
                    valid = False
                    break

            if valid and (selected or has_custom):
                if has_custom:
                    try:
                        custom = input_fn("Custom answer: ").strip()
                        if custom:
                            selected.append(custom)
                    except (EOFError, StopIteration):
                        pass
                return selected if selected else _get_default_choice(opts_str)

            print(f"Please enter valid option numbers between 1 and {len(opts_str)}, comma-separated, or 'c'.")
        else:
            try:
                num = int(raw)
                if 1 <= num <= len(opts_str):
                    return [opts_str[num - 1]]
            except ValueError:
                pass
            print(f"Please enter a valid option number between 1 and {len(opts_str)}, or 'c'.")


def handle_ask_question(
    arguments: dict[str, Any],
    input_fn: Callable[[str], str] = input,
    *,
    is_interactive: bool | None = None,
) -> dict[str, Any]:
    """Handle an ask_question tool call payload."""
    questions = arguments.get("questions")
    if isinstance(questions, list) and questions:
        answers: list[dict[str, Any]] = []
        for item in questions:
            if isinstance(item, dict):
                q = item.get("question", "")
                opts = item.get("options", [])
                multi = bool(item.get("is_multi_select", False))
                selected = prompt_choice(
                    q, opts, is_multi_select=multi, input_fn=input_fn, is_interactive=is_interactive
                )
                answers.append({"question": q, "answers": selected})
        return {"results": answers}

    q = arguments.get("question", "")
    opts = arguments.get("options", [])
    multi = bool(arguments.get("is_multi_select", False))
    selected = prompt_choice(q, opts, is_multi_select=multi, input_fn=input_fn, is_interactive=is_interactive)
    return {"answers": selected}
