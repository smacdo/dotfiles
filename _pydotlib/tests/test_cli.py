import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest import mock
from unittest.mock import patch

from _pydotlib.cli import confirm, input_field


class InputFieldTests(unittest.TestCase):
    @patch("builtins.input", return_value="user input")
    def test_returns_user_input_when_provided(self, mock_input):
        result = input_field("Enter value")
        self.assertEqual(result, "user input")

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
    @patch("builtins.input", return_value="")
    def test_prints_message_with_yes_no(self, mocked_input):
        with redirect_stderr(StringIO()) as stderr_buffer:
            confirm(message="do something?", default=None)
            captured_stderr = stderr_buffer.getvalue()

            self.assertEqual("do something? [y/n] ", captured_stderr)

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
        result = input_field("Enter value", default="default")
        self.assertEqual(result, "default")

    @patch("builtins.input", return_value="")
    def test_returns_none_when_input_empty_and_no_default(self, mock_input):
        result = input_field("Enter value")
        self.assertIsNone(result)
