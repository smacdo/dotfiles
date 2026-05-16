import logging
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest import mock
from unittest.mock import patch

from _pydotlib.cli import ColoredLogFormatter, confirm, input_field


class InputFieldTests(unittest.TestCase):
    @patch("builtins.input", return_value="user input")
    def test_returns_user_input_when_provided(self, mock_input):
        result = input_field("Enter value")
        self.assertEqual(result, "user input")

    @patch("builtins.input", return_value="x")
    def test_prompt_goes_to_stderr(self, mocked_input):
        with (
            redirect_stderr(StringIO()) as stderr_buffer,
            mock.patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = True
            input_field("Enter value", default="d")
            self.assertIn("Enter value", stderr_buffer.getvalue())

    @patch("builtins.input")
    def test_returns_default_without_prompting_if_not_atty(self, mocked_input):
        with (
            redirect_stderr(StringIO()) as stderr_buffer,
            mock.patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = False

            self.assertTrue(
                input_field(message="your value here", default="hello world")
            )

            captured_stderr = stderr_buffer.getvalue()
            self.assertEqual("", captured_stderr)

            self.assertFalse(mocked_input.called)


class ConfirmTests(unittest.TestCase):
    def setUp(self):
        # Most tests assume an interactive terminal; the explicit "non-tty"
        # tests patch isatty back to False locally.
        patcher = mock.patch("sys.stdin")
        self.mock_stdin = patcher.start()
        self.mock_stdin.isatty.return_value = True
        self.addCleanup(patcher.stop)

    @patch("builtins.input", return_value="")
    def test_prints_message_with_yes_no(self, mocked_input):
        # default=True so empty input resolves on the first prompt instead of looping.
        with redirect_stderr(StringIO()) as stderr_buffer:
            confirm(message="do something?", default=True)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [Y/n] ", captured_stderr)

    @patch("builtins.input")
    def test_returns_default_without_prompting_if_not_atty(self, mocked_input):
        with (
            redirect_stderr(StringIO()) as stderr_buffer,
            mock.patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = False

            self.assertTrue(confirm(message="do something?", default=True))
            self.assertFalse(confirm(message="do something?", default=False))

            captured_stderr = stderr_buffer.getvalue()
            self.assertEqual("", captured_stderr)

            self.assertFalse(mocked_input.called)

    @patch("builtins.input", return_value="")
    def test_prints_upper_y_if_default_true(self, mocked_input):
        with (
            redirect_stderr(StringIO()) as stderr_buffer,
            mock.patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = True
            confirm(message="do something?", default=True)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [Y/n] ", captured_stderr)

    @patch("builtins.input", return_value="")
    def test_prints_upper_n_if_default_false(self, mocked_input):
        with (
            redirect_stderr(StringIO()) as stderr_buffer,
            mock.patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = True
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
            self.assertTrue(confirm(message="do something?", default=True))
            self.assertFalse(confirm(message="do something?", default=False))

    @patch("builtins.input", return_value="     ")
    def test_returns_default_if_blank_input(self, mocked_input):
        with redirect_stderr(StringIO()):
            self.assertTrue(confirm(message="do something?", default=True))
            self.assertFalse(confirm(message="do something?", default=False))

    @patch("builtins.input", side_effect=["", "y"])
    def test_reprompts_on_empty_input_when_no_default(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            self.assertTrue(confirm(message="do something?", default=None))
            self.assertIn("Please answer yes or no.", stderr_buffer.getvalue())

    @patch("builtins.input", side_effect=["maybe", "n"])
    def test_reprompts_on_invalid_input(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            self.assertFalse(confirm(message="do something?", default=None))
            self.assertIn("Please answer yes or no.", stderr_buffer.getvalue())

    def test_raises_when_non_tty_and_no_default(self):
        with mock.patch("sys.stdin") as stdin:
            stdin.isatty.return_value = False
            with self.assertRaises(RuntimeError):
                confirm(message="do something?", default=None)

    @patch("builtins.input", return_value="")
    def test_returns_default_value_when_input_empty(self, mock_input):
        result = input_field("Enter value", default="default")
        self.assertEqual(result, "default")

    @patch("builtins.input", return_value="")
    def test_returns_none_when_input_empty_and_no_default(self, mock_input):
        result = input_field("Enter value")
        self.assertIsNone(result)


class ColoredLogFormatterTests(unittest.TestCase):
    def _make_record(self, level: int, msg: str = "hello") -> logging.LogRecord:
        return logging.LogRecord(
            name="test",
            level=level,
            pathname=__file__,
            lineno=0,
            msg=msg,
            args=None,
            exc_info=None,
        )

    def test_formats_includes_message_and_level(self):
        formatter = ColoredLogFormatter()
        for level_name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            level = logging.getLevelName(level_name)
            output = formatter.format(self._make_record(level, "msg-text"))
            self.assertIn("msg-text", output)
            self.assertIn(level_name, output)

    def test_formats_each_known_level_without_error(self):
        formatter = ColoredLogFormatter()
        for level in (
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ):
            formatter.format(self._make_record(level))

    def test_unknown_level_raises_keyerror(self):
        # Locks in current behavior: levels not in LOG_LEVEL_COLORS crash with
        # KeyError. If we ever want to be more forgiving, change this test
        # along with the production code.
        formatter = ColoredLogFormatter()
        with self.assertRaises(KeyError):
            formatter.format(self._make_record(logging.NOTSET))
