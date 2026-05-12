"""CLI utilities for interactive command-line applications.

Provides colored logging, user input prompts, and confirmation dialogs.
"""

import logging
import sys

from _pydotlib.colors import Colors

LOG_LEVEL_COLORS = {
    logging.DEBUG: Colors.BRIGHT_GRAY,
    logging.INFO: Colors.BRIGHT_WHITE,
    logging.WARNING: Colors.BRIGHT_YELLOW,
    logging.ERROR: Colors.BRIGHT_RED,
    logging.CRITICAL: Colors.RED_BG + Colors.BRIGHT_WHITE,
}


class ColoredLogFormatter(logging.Formatter):
    """Formatter that adds colors to log messages based on severity level."""

    format_strs: dict[int, logging.Formatter]

    def __init__(self) -> None:
        super().__init__()
        self.format_strs = {}

        for name, color in LOG_LEVEL_COLORS.items():
            self.format_strs[name] = logging.Formatter(
                f"{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Colors.RESET}"
            )

    def format(self, record):
        return self.format_strs[record.levelno].format(record)


def input_field(
    message: str, default_message: str | None = None, default: str | None = None
) -> str | None:
    """Prompt user for input with optional default value.

    Args:
        message: Prompt message to display
        default_message: Custom default message (overrides auto-generated)
        default: Value to return if user enters nothing

    Returns:
        User input string or default_value if empty input
    """

    if not sys.stdin.isatty() and default is not None:
        return default

    if default_message is None:
        default_message = (
            f"[{default}]"
            if (default is not None and default.strip() != "")
            else "(leave blank for none)"
        )
    else:
        default_message = f"({default_message})"

    input_result = input(f"{message} {default_message}: ")

    if len(input_result.strip()) == 0:
        return default
    else:
        return input_result


def confirm(message: str, default: bool | None = None) -> bool | None:
    """Prompt user for yes/no confirmation.

    Args:
        message: Question to ask user
        default: Default answer if user enters nothing (None for required input)

    Returns:
        True for yes, False for no, default value for empty input
    """

    if not sys.stdin.isatty() and default is not None:
        return default

    while True:
        print(
            f"{message} [{'Y' if default is True else 'y'}/{'N' if default is False else 'n'}] ",
            end="",
            file=sys.stderr,
        )
        reply = input().strip().lower()

        if reply is None or len(reply) == 0:
            return default
        elif "yes".startswith(reply):
            return True
        elif "no".startswith(reply):
            return False
