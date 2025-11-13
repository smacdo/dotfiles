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

from _pydotlib.bootstrap import (
    configure_vcs_author,
    create_dirs,
    download_files,
    initialize_vim_plugin_manager,
    is_dotfiles_root,
    safe_symlink,
)
from _pydotlib.cli import ColoredLogFormatter, confirm, input_field
from _pydotlib.git import get_repo_root
from _pydotlib.xdg import xdg_config_dir, xdg_data_dir, xdg_state_dir

logger = logging.getLogger(__name__)

MY_GITCONFIG_PATH = Path.joinpath(Path.home(), ".my_gitconfig")


def apply_dotfile_symlinks(
    dotfiles_dir: Path, dry_run: bool, files: list[tuple[str | Path, Path]]
) -> None:
    assert dotfiles_dir.is_dir()

    for source, target in files:
        safe_symlink(
            source=dotfiles_dir.joinpath(source), target=target, dry_run=dry_run
        )


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
    args_parser.add_argument(
        "--git-name", type=str, help="Name to use when initializing .my_gitconfig"
    )
    args_parser.add_argument(
        "--git-email", type=str, help="Email to use when initializing .my_gitconfig"
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

    create_dirs(
        dry_run=args.dry_run,
        dirs=[
            xdg_state_dir() / "vim/backups",
            xdg_state_dir() / "vim/tmp",
        ],
    )

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
            ("settings/ghostty/config", xdg_config_dir() / "ghostty/config"),
            ("settings/wezterm/wezterm.lua", xdg_config_dir() / "wezterm/wezterm.lua"),
        ],
    )

    download_files(
        dry_run=args.dry_run,
        urls=[
            (
                "https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim",
                home_dir / ".vim/autoload/plug.vim",
            ),
            (
                "https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim",
                xdg_data_dir() / "nvim/site/autoload/plug.vim",
            ),
        ],
    )

    initialize_vim_plugin_manager()
    configure_vcs_author(
        gitconfig_path=MY_GITCONFIG_PATH, name=args.git_name, email=args.git_email
    )


if __name__ == "__main__":
    main()