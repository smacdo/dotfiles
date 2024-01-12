#!/usr/bin/env python3
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: CI linter for the dotfiles repository.
#
# Working directory must be root of dotfiles.
import logging
import os
import shutil
import subprocess


################################################################################
# Lint all shellscripts in the repo
################################################################################
def lint_all_shell_scripts() -> int:
    # Lint sh and bash shell script files.
    if shutil.which("shellcheck") == None:
        raise Exception("cannot lint shell scripts - shellcheck not found")

    SHELL_PROFILE_SCRIPTS = [".bash_profile", ".bashrc"]
    SHELL_REPO_SCRIPTS = ["bootstrap.sh", "setup.sh"]

    shell_scripts = (
        SHELL_PROFILE_SCRIPTS
        + SHELL_REPO_SCRIPTS
        + find_shell_scripts("shell_profile")
        + find_shell_scripts("bin")
    )

    sh_lint_issues = 0

    for script_filepath in shell_scripts:
        if not shellcheck_file(script_filepath):
            sh_lint_issues += 1

    return sh_lint_issues


################################################################################
# Runs the shellcheck tool on a given shell script file.
################################################################################
def shellcheck_file(script_filepath: str) -> bool:
    # SC1090 - ignore warning for can't follow non-constant source.
    # SC1091 - ignore warning for included files that cannot be found.
    result = subprocess.run(
        ["shellcheck", script_filepath, "-e", "SC1090", "-e", "SC1091"]
    )

    if result.returncode == 0:
        logging.debug(f"{script_filepath}: OK")
    elif result.returncode != 0:
        logging.error(f"{script_filepath}: SHELLCHECK FAILED")
        if result.stdout != None:
            logging.info(f"shellcheck output:\n{result.stdout}")

    return result.returncode == 0


# Check if the given filepath is a shell script. This function considers a file
# a shell script if it ends with `.sh` or if the first line contains a shebang
# reference to a shell interpreter.
def is_shell_script(filepath: str, base_dir=None) -> bool:
    if base_dir is not None:
        filepath = os.path.join(base_dir, filepath)

    if filepath.endswith(".sh"):
        return True

    with open(filepath) as f:
        first_line = f.readline().strip()
        if first_line == "#!/bin/sh" or first_line == "#!/bin/bash":
            return True


# Returns a list of shell scripts found in the given directory.
def find_shell_scripts(dirpath: str) -> list[str]:
    return [
        os.path.join(dirpath, f)
        for f in os.listdir(dirpath)
        if is_shell_script(f, dirpath)
    ]


def main() -> None:
    # Show log info messages (disabled by default).
    logging.getLogger().setLevel(logging.INFO)

    # Lint shell scripts.
    logging.info(f"linting shell scripts...")
    sh_lint_issues = lint_all_shell_scripts()

    if sh_lint_issues > 0:
        logging.warning(f"found {sh_lint_issues} shell scripts with linting issues")

    # TODO: Lint python scripts.

    # TODO: Test bash profile with a docker container.
    # TODO: Test zsh profile with a docker container.
    # TODO: Test bootstrap process in a docker container.

    # TODO: Determine if any errors were present when linting (as opposed to
    # warnings), and print that result down here.

    # Report if all tests passed or not.
    if sh_lint_issues == 0:
        logging.info("all lint checks passed!")
    else:
        logging.warning("linter issues found")


main()
