import os
import subprocess
import sys
import unittest
from dataclasses import dataclass
from functools import cache, lru_cache
from unittest.mock import patch


@lru_cache(maxsize=1)
def should_use_colors() -> bool:
    if os.getenv("NO_COLOR") or os.getenv("CLICOLOR") == "0":
        return False
    elif (
        os.getenv("CLICOLOR") == "1"
        or os.getenv("CLICOLOR_FORCE")
        or os.getenv("FORCE_COLOR")
    ):
        return True
    elif sys.stdout.isatty():
        try:
            colors_supported = subprocess.check_output(["tput", "colors"]).decode()
            return int(colors_supported) >= 8
        except ValueError:
            return False
    else:
        return False


@dataclass(frozen=True)
class ColorCodes:
    """
    ANSI color codes.

    All attributes in this class are ANSI control codes that change terminal formatting when printed
    as output. The attributes are only set when `should_use_colors()` is True, otherwise all the
    attributes are initialized to empty strings.
    """

    RESET: str
    BOLD: str
    DIM: str
    UNDERLINE: str
    INVERSE: str
    HIDDEN: str
    STRIKE: str
    BLACK: str
    RED: str
    GREEN: str
    YELLOW: str
    BLUE: str
    MAGENTA: str
    CYAN: str
    WHITE: str
    DEFAULT: str
    BLACK_BG: str
    RED_BG: str
    GREEN_BG: str
    YELLOW_BG: str
    BLUE_BG: str
    MAGENTA_BG: str
    CYAN_BG: str
    WHITE_BG: str
    DEFAULT_BG: str
    BRIGHT_GRAY: str
    BRIGHT_RED: str
    BRIGHT_GREEN: str
    BRIGHT_YELLOW: str
    BRIGHT_BLUE: str
    BRIGHT_MAGENTA: str
    BRIGHT_CYAN: str
    BRIGHT_WHITE: str
    BRIGHT_GRAY_BG: str
    BRIGHT_RED_BG: str
    BRIGHT_GREEN_BG: str
    BRIGHT_YELLOW_BG: str
    BRIGHT_BLUE_BG: str
    BRIGHT_MAGENTA_BG: str
    BRIGHT_CYAN_BG: str
    BRIGHT_WHITE_BG: str


@lru_cache(maxsize=1)
def _get_colors() -> ColorCodes:
    """
    Get `Colors` object with class attributes initialized to the correct ASCII control values if
    colors are enabled, otherwise set all attributes to be empty strings.
    """
    use_colors = should_use_colors()

    def c(code: str) -> str:
        return code if use_colors else ""

    return ColorCodes(
        RESET=c("\033[0m"),
        BOLD=c("\033[1m"),
        DIM=c("\033[2m"),
        UNDERLINE=c("\033[4m"),
        INVERSE=c("\033[7m"),
        HIDDEN=c("\033[8m"),
        STRIKE=c("\033[9m"),
        BLACK=c("\033[30m"),
        RED=c("\033[31m"),
        GREEN=c("\033[32m"),
        YELLOW=c("\033[33m"),
        BLUE=c("\033[34m"),
        MAGENTA=c("\033[35m"),
        CYAN=c("\033[36m"),
        WHITE=c("\033[37m"),
        DEFAULT=c("\033[39m"),
        BLACK_BG=c("\033[40m"),
        RED_BG=c("\033[41m"),
        GREEN_BG=c("\033[42m"),
        YELLOW_BG=c("\033[43m"),
        BLUE_BG=c("\033[44m"),
        MAGENTA_BG=c("\033[45m"),
        CYAN_BG=c("\033[46m"),
        WHITE_BG=c("\033[47m"),
        DEFAULT_BG=c("\033[49m"),
        BRIGHT_GRAY=c("\033[90m"),
        BRIGHT_RED=c("\033[91m"),
        BRIGHT_GREEN=c("\033[92m"),
        BRIGHT_YELLOW=c("\033[93m"),
        BRIGHT_BLUE=c("\033[94m"),
        BRIGHT_MAGENTA=c("\033[95m"),
        BRIGHT_CYAN=c("\033[96m"),
        BRIGHT_WHITE=c("\033[97m"),
        BRIGHT_GRAY_BG=c("\033[100m"),
        BRIGHT_RED_BG=c("\033[101m"),
        BRIGHT_GREEN_BG=c("\033[102m"),
        BRIGHT_YELLOW_BG=c("\033[103m"),
        BRIGHT_BLUE_BG=c("\033[104m"),
        BRIGHT_MAGENTA_BG=c("\033[105m"),
        BRIGHT_CYAN_BG=c("\033[106m"),
        BRIGHT_WHITE_BG=c("\033[107m"),
    )


Colors: ColorCodes = _get_colors()


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