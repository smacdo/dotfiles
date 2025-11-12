"""CLI utilities for interactive command-line applications.

Provides colored logging, user input prompts, and confirmation dialogs.
"""

import logging
import sys
import unittest

from io import StringIO
from contextlib import redirect_stderr
from unittest.mock import patch

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

    def __init__(self):
        super().__init__()
        self.format_strs = {}

        for name, color in LOG_LEVEL_COLORS.items():
            self.format_strs[name] = logging.Formatter(
                f"{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{Colors.RESET}"
            )

    def format(self, record):
        return self.format_strs[record.levelno].format(record)


def input_field(
    message: str, default_message: str | None = None, default_value: str | None = None
) -> str | None:
    """Prompt user for input with optional default value.

    Args:
        message: Prompt message to display
        default_message: Custom default message (overrides auto-generated)
        default_value: Value to return if user enters nothing

    Returns:
        User input string or default_value if empty input
    """
    if default_message is None:
        default_message = (
            f"[{default_value}]"
            if (default_value is not None and default_value.strip() != "")
            else "(leave blank for none)"
        )
    else:
        default_message = f"({default_message})"

    input_result = input(f"{message} {default_message}: ")

    if len(input_result.strip()) == 0:
        return default_value
    else:
        return input_result


def confirm(message: str, default: bool | None = None) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        message: Question to ask user
        default: Default answer if user enters nothing (None for required input)

    Returns:
        True for yes, False for no, default value for empty input
    """
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


class InputFieldTests(unittest.TestCase):
    @patch("builtins.input", return_value="user input")
    def test_returns_user_input_when_provided(self, mock_input):
        result = input_field("Enter value")
        self.assertEqual(result, "user input")

    @patch("builtins.input", return_value="")
    def test_confirm_prints_message_with_yes_no(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            confirm(message="do something?", default=None)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [y/n] ", captured_stderr)

    @patch("builtins.input", return_value="")
    def test_confirm_prints_upper_y_if_default_true(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            confirm(message="do something?", default=True)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [Y/n] ", captured_stderr)

    @patch("builtins.input", return_value="")
    def test_confirm_prints_upper_n_if_default_false(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            confirm(message="do something?", default=False)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [y/N] ", captured_stderr)

    @patch("builtins.input")
    def test_returns_true_for_input_yes(self, mocked_input):
        with redirect_stderr(StringIO()):
            mocked_input.return_value = "y"
            self.assertTrue(confirm(message="do something?", default=None))

            mocked_input.return_value = "Y"
            self.assertTrue(confirm(message="do something?", default=None))

            mocked_input.return_value = "ye"
            self.assertTrue(confirm(message="do something?", default=None))

            mocked_input.return_value = "yes"
            self.assertTrue(confirm(message="do something?", default=None))

            mocked_input.return_value = "YeS"
            self.assertTrue(confirm(message="do something?", default=None))

    @patch("builtins.input")
    def test_returns_false_for_input_no(self, mocked_input):
        with redirect_stderr(StringIO()):
            mocked_input.return_value = "n"
            self.assertFalse(confirm(message="do something?", default=None))

            mocked_input.return_value = "N"
            self.assertFalse(confirm(message="do something?", default=None))

            mocked_input.return_value = "no"
            self.assertFalse(confirm(message="do something?", default=None))

            mocked_input.return_value = "NO"
            self.assertFalse(confirm(message="do something?", default=None))

            mocked_input.return_value = "nO"
            self.assertFalse(confirm(message="do something?", default=None))

    @patch("builtins.input")
    def test_confirm_requests_input_until_valid_response(self, mocked_input):
        with redirect_stderr(StringIO()):
            mocked_input.side_effect = ["blargh", "no"]
            self.assertFalse(confirm(message="do something?", default=None))

    @patch("builtins.input", return_value="")
    def test_returns_default_if_no_input(self, mocked_input):
        with redirect_stderr(StringIO()):
            self.assertIsNone(confirm(message="do something?", default=None))
            self.assertTrue(confirm(message="do something?", default=True))
            self.assertFalse(confirm(message="do something?", default=False))

    @patch("builtins.input", return_value="     ")
    def test_returns_default_if_blank_input(self, mocked_input):
        with redirect_stderr(StringIO()):
            self.assertIsNone(confirm(message="do something?", default=None))
            self.assertTrue(confirm(message="do something?", default=True))
            self.assertFalse(confirm(message="do something?", default=False))

    @patch("builtins.input", return_value="")
    def test_returns_default_value_when_input_empty(self, mock_input):
        result = input_field("Enter value", default_value="default")
        self.assertEqual(result, "default")

    @patch("builtins.input", return_value="")
    def test_returns_none_when_input_empty_and_no_default(self, mock_input):
        result = input_field("Enter value")
        self.assertIsNone(result)