import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from _pydotlib.colors import _get_colors, should_use_colors


class TestShouldUseColors(unittest.TestCase):
    def setUp(self):
        # clear the cached value from `should_use_colors` before running a unit test
        should_use_colors.cache_clear()

    def tearDown(self):
        # reset cache on `should_use_colors` to prevent unit test from modifying the function's
        # expected behavior.
        should_use_colors.cache_clear()

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_returns_false_when_no_color_env_set(self):
        self.assertFalse(should_use_colors())

    @patch.dict(os.environ, {"CLICOLOR": "0"})
    def test_returns_false_when_clicolor__env_zero(self):
        self.assertFalse(should_use_colors())

    @patch.dict(os.environ, {"CLICOLOR": "1"})
    def test_returns_true_when_clicolor__env_one(self):
        self.assertTrue(should_use_colors())

    @patch.dict(os.environ, {"CLICOLOR_FORCE": "1"})
    def test_returns_true_when_clicolor_force_env(self):
        self.assertTrue(should_use_colors())

    @patch.dict(os.environ, {"FORCE_COLOR": "1"})
    def test_returns_true_when_force_color_env(self):
        self.assertTrue(should_use_colors())

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.stdout.isatty", return_value=True)
    @patch("subprocess.check_output", return_value=b"256")
    def test_returns_true_when_tty_and_colors_supported(
        self, mock_subprocess, mock_isatty
    ):
        self.assertTrue(should_use_colors())

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.stdout.isatty", return_value=True)
    @patch("subprocess.check_output", return_value=b"4")
    def test_returns_false_when_tty_but_insufficient_colors(
        self, mock_subprocess, mock_isatty
    ):
        self.assertFalse(should_use_colors())

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.stdout.isatty", return_value=False)
    def test_returns_false_when_not_tty(self, mock_isatty):
        self.assertFalse(should_use_colors())

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.stdout.isatty", return_value=True)
    @patch("subprocess.check_output", return_value=b"invalid")
    def test_returns_false_when_tput_returns_invalid(
        self, mock_subprocess, mock_isatty
    ):
        self.assertFalse(should_use_colors())

    @patch.dict(os.environ, {"NO_COLOR": "1", "CLICOLOR": "1"})
    def test_no_color_takes_precedence(self):
        # NO_COLOR should override CLICOLOR
        self.assertFalse(should_use_colors())


class TestColorsClass(unittest.TestCase):
    def setUp(self):
        should_use_colors.cache_clear()
        _get_colors.cache_clear()

    def tearDown(self):
        should_use_colors.cache_clear()
        _get_colors.cache_clear()

    @patch.dict("os.environ", {"CLICOLOR_FORCE": "1"}, clear=True)
    def test_colors_enabled_when_forced(self):
        colors = _get_colors()
        self.assertEqual(colors.RED, "\033[31m")
        self.assertEqual(colors.BOLD, "\033[1m")
        self.assertEqual(colors.RESET, "\033[0m")

    @patch.dict("os.environ", {"NO_COLOR": "1"}, clear=True)
    def test_colors_disabled_when_no_color_set(self):
        colors = _get_colors()
        self.assertEqual(colors.RED, "")
        self.assertEqual(colors.GREEN, "")
        self.assertEqual(colors.BOLD, "")
        self.assertEqual(colors.RESET, "")
