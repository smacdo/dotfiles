#!/usr/bin/env python3

"""
Author: Scott MacDonald <root@smacdo.com>

This script will configure the dotfiles repo for the current user to use. Make sure to run
`bootstrap.sh` before using this script.
"""

# TODO: Fancy console output (eg, color or other effects) without needing 3rd party libraries.

from pathlib import Path

import argparse
import logging

from _pydotlib.cli import input_field
from _pydotlib.gitconfig import (
    read_git_config_file,
    update_git_config_file,
)

logger = logging.getLogger(__name__)


MY_GITCONFIG_PATH = Path.joinpath(Path.home(), ".my_gitconfig")
VCS_MISSING_NAME = "TODO_SET_USER_NAME"
VCS_MISSING_EMAIL = "TODO_SET_EMAIL_ADDRESS"


def configure_vcs_author() -> None:
    # Create the ~/.my_gitconfig file if it does not exist.
    if not MY_GITCONFIG_PATH.exists():
        MY_GITCONFIG_PATH.write_text(
            f"""[user]
  name = {VCS_MISSING_NAME}
  email = {VCS_MISSING_EMAIL}
"""
        )

    # Read ~/.my_gitconfig, and replace keys that are marked as `TODO_SET_*`.
    # Any line that is not modified should be written back out exactly as it was.
    def try_update_key(
        keys: dict[str, str], key: str, default_value: str, prompt: str
    ) -> str | None:
        if key in keys:
            git_keys[key] = input_field(
                prompt,
                default_message=(
                    git_keys[key]
                    if git_keys[key] != default_value
                    else "leave blank to skip"
                ),
                default_value=(
                    git_keys[key] if git_keys[key] != default_value else None
                ),
            )

    git_keys = read_git_config_file(MY_GITCONFIG_PATH, ["user:name", "user:email"])
    print(git_keys)

    try_update_key(git_keys, "user:name", VCS_MISSING_NAME, "Enter your git name")
    try_update_key(git_keys, "user:email", VCS_MISSING_EMAIL, "Enter your git email")

    update_git_config_file(MY_GITCONFIG_PATH, git_keys)


def main() -> None:
    # Argument parsing.
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging)",
    )

    args = args_parser.parse_args()

    # Set up more verbose logging if the user requested it.
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Run installation commands.
    configure_vcs_author()


if __name__ == "__main__":
    main()