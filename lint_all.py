#!/usr/bin/env python3
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: CI linter for the dotfiles repository.
import logging
import os
import shutil
import subprocess

SH_EXTS = [".sh"]
SH_SHEBANGS = ["#!/bin/sh", "#!/bin/bash"]

PY_EXTS = [".py"]
PY_SHEBANGS = ["#!/usr/bin/env python3"]

BASH_CONFIG_FILES = [".bash_profile", ".bashrc"]
DOTFILES_SH_SCRIPTS = ["bootstrap.sh", "setup.sh"]

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
        result = subprocess.run(["shellcheck", file_path, "-e", "SC1090", "-e", "SC1091"])

        if result.returncode != 0:
            files_failed.append(file_path)
            continue

        # File looks ok.
        logging.debug(f"{file_path}: OK")

    # Report the files that failed to lint.
    return files_failed


################################################################################
# Lint a list of python files, and return a list of the files that failed a
# linter check.
#
# This function assumes that `mypy` and `ruff` are installed, otherwise a sub-
# process exception will be raised. 
################################################################################
def lint_py_files(file_paths: list[str]) -> list[str]: 
    # Make sure Python linter tools are available.
    if shutil.which("mypy") is None:
        raise Exception("cannot lint python scripts - mypy not found")
    if shutil.which("ruff") is None:
        raise Exception("cannot lint python scripts - ruff not found")

    # Lint each file individually.
    files_failed: list[str] = []

    for file_path in file_paths:
        # Typecheck the python file.
        result = subprocess.run(["mypy", "--no-error-summary", file_path])

        if result.returncode != 0:
            files_failed.append(file_path)
            continue

        # Apply standard linting rules with Ruff.
        result = subprocess.run(["ruff", "check", file_path])

        if result.returncode != 0:
            files_failed.append(file_path)

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
    for x in file_exts:
        if filepath.endswith(x):
            return True

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
def main() -> None:
    # Show log info messages (disabled by default).
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
    logging.info("linting python scripts...")
    failed_py_files = lint_py_files(
        ["lint_all.py"] + find_shell_scripts("bin", PY_EXTS, PY_SHEBANGS)
    )

    if len(failed_py_files) > 0:
        logging.warning(f"{len(failed_py_files)} python scripts failed linter checks")

    # TODO: Test bash profile with a docker container.
    # TODO: Test zsh profile with a docker container.
    # TODO: Test bootstrap process in a docker container.

    # Report if all tests passed or not.
    if len(failed_sh_files) + len(failed_py_files) == 0:
        logging.info("all lint checks passed!")
    else:
        logging.warning("linter issues found")


main()
