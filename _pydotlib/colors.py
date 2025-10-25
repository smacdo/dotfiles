import os
import subprocess
import sys
from functools import cache


@cache
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


class Colors:
    """Class to store ANSI color codes for easier use."""

    RESET = "\033[0m" if should_use_colors() else ""
    BOLD = "\033[1m" if should_use_colors() else ""
    DIM = "\033[2m" if should_use_colors() else ""
    UNDERLINE = "\033[4m" if should_use_colors() else ""
    INVERSE = "\033[7m" if should_use_colors() else ""
    HIDDEN = "\033[8m" if should_use_colors() else ""
    STRIKE = "\033[9m" if should_use_colors() else ""
    BLACK = "\033[30m" if should_use_colors() else ""
    RED = "\033[31m" if should_use_colors() else ""
    GREEN = "\033[32m" if should_use_colors() else ""
    YELLOW = "\033[33m" if should_use_colors() else ""
    BLUE = "\033[34m" if should_use_colors() else ""
    MAGENTA = "\033[35m" if should_use_colors() else ""
    CYAN = "\033[36m" if should_use_colors() else ""
    WHITE = "\033[37m" if should_use_colors() else ""
    DEFAULT = "\033[39m" if should_use_colors() else ""
    BLACK_BG = "\033[40m" if should_use_colors() else ""
    RED_BG = "\033[41m" if should_use_colors() else ""
    GREEN_BG = "\033[42m" if should_use_colors() else ""
    YELLOW_BG = "\033[43m" if should_use_colors() else ""
    BLUE_BG = "\033[44m" if should_use_colors() else ""
    MAGENTA_BG = "\033[45m" if should_use_colors() else ""
    CYAN_BG = "\033[46m" if should_use_colors() else ""
    WHITE_BG = "\033[47m" if should_use_colors() else ""
    DEFAULT_BG = "\033[49m" if should_use_colors() else ""
    BRIGHT_GRAY = "\033[90m" if should_use_colors() else ""
    BRIGHT_RED = "\033[91m" if should_use_colors() else ""
    BRIGHT_GREEN = "\033[92m" if should_use_colors() else ""
    BRIGHT_YELLOW = "\033[93m" if should_use_colors() else ""
    BRIGHT_BLUE = "\033[94m" if should_use_colors() else ""
    BRIGHT_MAGENTA = "\033[95m" if should_use_colors() else ""
    BRIGHT_CYAN = "\033[96m" if should_use_colors() else ""
    BRIGHT_WHITE = "\033[97m" if should_use_colors() else ""
    BRIGHT_GRAY_BG = "\033[100m" if should_use_colors() else ""
    BRIGHT_RED_BG = "\033[101m" if should_use_colors() else ""
    BRIGHT_GREEN_BG = "\033[102m" if should_use_colors() else ""
    BRIGHT_YELLOW_BG = "\033[103m" if should_use_colors() else ""
    BRIGHT_BLUE_BG = "\033[104m" if should_use_colors() else ""
    BRIGHT_MAGENTA_BG = "\033[105m" if should_use_colors() else ""
    BRIGHT_CYAN_BG = "\033[106m" if should_use_colors() else ""
    BRIGHT_WHITE_BG = "\033[107m" if should_use_colors() else ""