import os
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache


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
        except (ValueError, FileNotFoundError, subprocess.CalledProcessError):
            return False
    else:
        return False


@dataclass(frozen=True)
class ColorCodes:
    """ANSI control codes for terminal formatting.

    Instances are constructed via `_get_colors()`, which fills every field
    with either the real escape sequence (when colors are enabled) or an
    empty string (when they're not).
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
