#!/usr/bin/env python3
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: CI linter for the dotfiles repository.

import argparse
import logging
import os
import shutil
import subprocess
import sys

SH_EXTS = [".sh"]
SH_SHEBANGS = ["#!/bin/sh", "#!/bin/bash"]

PY_EXTS = [".py"]
PY_SHEBANGS = ["#!/usr/bin/env python3"]

BASH_CONFIG_FILES = [".bash_profile", ".bashrc"]
DOTFILES_SH_SCRIPTS = ["_setup.sh"]
DOTFILES_PY_SCRIPTS = [os.path.basename(__file__), "bootstrap.py"]


################################################################################
# Lint a list of shell scripts, and return a list of files that failed a linter
# check.
################################################################################
def lint_sh_files(file_paths: list[str]) -> list[str]:
    # Make sure linter tool is available.
    if shutil.which("shellcheck") is None:
        raise Exception("cannot lint shell scripts - shellcheck not found")

    # Lint each script individually.
    files_failed: list[str] = []

    for file_path in file_paths:
        # SC1090 - ignore warning for can't follow non-constant source.
        # SC1091 - ignore warning for included files that cannot be found.
        result = subprocess.run(
            ["shellcheck", file_path, "-e", "SC1090", "-e", "SC1091"]
        )

        if result.returncode != 0:
            files_failed.append(file_path)
            continue

        # File looks ok.
        logging.debug(f"{file_path}: OK")

    # Report the files that failed to lint.
    return files_failed


# TODO: documentation
def typecheck_py_file(file_path: str) -> (bool, str):
    result = subprocess.run(
        ["uvx", "ty", "check", "--no-progress", "--color", "always", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    return (result.returncode == 0, result.stdout)


# TODO: documentation
def ruff_lint_py_file(file_path: str, auto_fix=False) -> (bool, str):
    fix_arg = "--fix" if auto_fix else "--no-fix"

    custom_env = os.environ.copy()
    custom_env["FORCE_COLOR"] = "1"

    result = subprocess.run(
        ["uvx", "ruff", "check", fix_arg, file_path],
        env=custom_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    return (result.returncode == 0, result.stdout)


################################################################################
# Lint a list of python files, and return a list of the files that failed a
# linter check.
#
# This function assumes that `mypy` and `ruff` are installed, otherwise a sub-
# process exception will be raised.
################################################################################
def lint_py_files(file_paths: list[str]) -> list[str]:
    # Make sure Python linter tools are available.
    if shutil.which("uv") is None:
        raise Exception("`uv` is required for linting python scripts")

    # Lint each file individually.
    files_failed: list[str] = []

    for file_path in file_paths:
        # Typecheck the python file.
        typecheck_ok, typecheck_output = typecheck_py_file(file_path)

        if not typecheck_ok:
            print(typecheck_output)
            files_failed.append(file_path)
            continue

        # Apply standard linting rules with Ruff.
        ruff_ok, ruff_output = ruff_lint_py_file(file_path)

        if not ruff_ok:
            print(ruff_output)
            files_failed.append(file_path)
            continue

        # File is good
        logging.debug(f"{file_path}: OK")

    # Report the files that failed to lint.
    return files_failed


################################################################################
# Check if the given file could be considered a script given a list of valid
# script file extensions and shebang first line candidates. A file matching any
# of these criteria will be considered a script.
################################################################################
def is_script(filepath: str, file_exts: list[str], first_lines: list[str]) -> bool:
    # Ignore directories, and files that do not exist.
    if not os.path.exists(filepath) or os.path.isdir(filepath):
        return False

    # Check if file extension matches.
    for x in file_exts:
        if filepath.endswith(x):
            return True

    # Look for first line of file matches.
    with open(filepath) as f:
        first_line = f.readline().strip()
        for x in first_lines:
            if first_line == x:
                return True

    return False


################################################################################
# Return a list of files that could be considered a script given a list of valid
# script file extensions and shebang first line candidates. A file matching any
# of these criteria will be considered a script.
################################################################################
def find_shell_scripts(
    dirpath: str, file_exts: list[str], first_lines: list[str]
) -> list[str]:
    return [
        os.path.join(dirpath, f)
        for f in os.listdir(dirpath)
        if is_script(os.path.join(dirpath, f), file_exts, first_lines)
    ]


################################################################################
# Script main
################################################################################
def main() -> int:
    has_fatal_lints = False

    # Command line arguments.
    parser = argparse.ArgumentParser("dotfiles lint checker")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")

    args = parser.parse_args()

    # Show log info messages (disabled by default).
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # Lint shell scripts.
    logging.info("linting shell scripts...")

    failed_sh_files = lint_sh_files(
        BASH_CONFIG_FILES
        + DOTFILES_SH_SCRIPTS
        + find_shell_scripts("shell_profile", SH_EXTS, SH_SHEBANGS)
        + find_shell_scripts("bin", SH_EXTS, SH_SHEBANGS)
    )

    if len(failed_sh_files) > 0:
        logging.warning(f"{len(failed_sh_files)} shell scripts failed linter checks")

    # Lint python scripts.
    # TODO: Apply auto fixes if --fix is passed.
    logging.info("linting python scripts...")

    failed_py_files = lint_py_files(DOTFILES_PY_SCRIPTS)

    if len(failed_py_files) > 0:
        has_fatal_lints = True
        logging.error(
            f"{len(failed_py_files)} core python scripts failed required linter checks"
        )

    failed_py_files += lint_py_files(find_shell_scripts("bin", PY_EXTS, PY_SHEBANGS))

    if len(failed_py_files) > 0:
        logging.warning(
            f"{len(failed_py_files)} python bin scripts failed linter checks"
        )

    # TODO: Auto-format files if --format is passed. Apply formatting to any file for which there
    #       are no linting errors, even if other files failed.

    # Report if all tests passed or not.
    if len(failed_sh_files) + len(failed_py_files) == 0:
        logging.info("all lint checks passed!")
    else:
        is_fatal_text = "fatal" if has_fatal_lints else "non-fatal"
        logging.warning(f"{is_fatal_text} linter issues found")

    return 1 if has_fatal_lints else 0


# TODO: Move functions into _pydotlib modules
# TODO: Use the _pydotlib shared logger with color
# TODO: Add an argument to report which shell and python scripts are detected
# TODO: Add auto-formatting to this script (or new `./format_all`)
# TODO: Add ability to lint / format only a specific script
# TODO: Add ability to execlude known problematic scripts.
# TODO: Turn color on/off rather than force.


if __name__ == "__main__":
    sys.exit(main())
