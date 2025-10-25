#!/usr/bin/env python3

"""
Author: Scott MacDonald <root@smacdo.com>

This script will configure the dotfiles repo for the current user to use.
"""
import os
import sys

from pathlib import Path

import argparse
import logging

from _pydotlib.bootstrap import is_dotfiles_root, safe_symlink
from _pydotlib.cli import ColoredLogFormatter, confirm, input_field
from _pydotlib.git import (
    get_repo_root,
    read_git_config_file,
    update_git_config_file,
)
from _pydotlib.xdg import xdg_config_dir, xdg_data_dir

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

    try_update_key(git_keys, "user:name", VCS_MISSING_NAME, "Enter your git name")
    try_update_key(git_keys, "user:email", VCS_MISSING_EMAIL, "Enter your git email")

    update_git_config_file(MY_GITCONFIG_PATH, git_keys)


def apply_dotfile_symlinks(
    dotfiles_dir: Path, dry_run: bool, files: list[tuple[str | Path, Path]]
) -> None:
    assert dotfiles_dir.is_dir()

    for source, target in files:
        safe_symlink(source=dotfiles_dir.joinpath(source), target=target, dry_run=True)


def main() -> None:
    # Argument parsing.
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging)",
    )
    args_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions but do not perform any changes",
    )

    args = args_parser.parse_args()

    # Set up more verbose logging if the user requested it.
    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setFormatter(ColoredLogFormatter())

    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Verify this command is being run from the dotfiles checkout.
    git_root = get_repo_root(Path(os.getcwd()).resolve())

    logging.debug(f"current git repo root is {git_root}")
    logging.debug(f"current git repo is dotfiles root: {is_dotfiles_root(git_root)}")

    if not is_dotfiles_root(git_root):
        logging.error(f"{__file__} must be run from the root of a dotfiles repository")
        sys.exit(1)

    # Run installation commands.
    home_dir = Path.home()

    apply_dotfile_symlinks(
        dotfiles_dir=git_root,
        dry_run=args.dry_run,
        files=[
            (".gitconfig", home_dir / ".gitconfig"),
            (".vim", home_dir / ".vim"),
            (".bash_profile", home_dir / ".bash_profile"),
            (".bashrc", home_dir / ".bashrc"),
            (".zshrc", home_dir / ".zshrc"),
            (".zshenv", home_dir / ".zshenv"),
            (".p10k.zsh", home_dir / ".p10k.zsh"),
            ("zsh_files", home_dir / ".zsh"),
            (".dircolors", home_dir / ".dircolors"),
            (".tmux.conf", home_dir / ".tmux.conf"),
            (".inputrc", home_dir / ".inputrc"),
            (".profile", home_dir / ".profile"),
            # Neovim should share most of its configs with vim to reduce duplication since I can't
            # always be sure if neovim is installed on the local machine.
            ("settings/nvim/init.vim", home_dir / ".vimrc"),
            ("settings/nvim/init.vim", xdg_config_dir() / "nvim/init.vim"),
            ("settings/nvim/site/plugin", xdg_data_dir() / "nvim/site/plugin"),
        ],
    )


if __name__ == "__main__":
    main()