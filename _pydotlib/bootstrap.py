"""
Utility functions for the bootstrap.py program.
"""

import functools
import json
import logging
import os
import shutil
import socket
import ssl
import subprocess
import urllib.request
import urllib.error

from datetime import datetime
from pathlib import Path
from typing import Any
from _pydotlib.cli import confirm, input_field
from _pydotlib.colors import Colors
from _pydotlib.git import (
    read_git_config_file,
    update_git_config_file,
)


VCS_MISSING_NAME = "TODO_SET_USER_NAME"
VCS_MISSING_EMAIL = "TODO_SET_EMAIL_ADDRESS"


def configure_vcs_author(
    gitconfig_path: Path | str,
    name: str | None = None,
    email: str | None = None,
    dry_run: bool = False,
) -> None:
    gitconfig_path = Path(gitconfig_path)
    dry_text = "[DRY RUN] " if dry_run else ""

    if gitconfig_path.exists():
        if dry_run:
            logging.info(f"{dry_text}{gitconfig_path} already exists")
            return
    else:
        if dry_run:
            logging.info(f"{dry_text}Would create {gitconfig_path} with git author config")
            return
        gitconfig_path.write_text(
            f"""[user]
  name = {VCS_MISSING_NAME}
  email = {VCS_MISSING_EMAIL}
"""
        )
    def try_update_key(
        keys: dict[str, str],
        key: str,
        placeholder: str,
        default: str | None,
        prompt: str,
    ) -> None:
        if key in keys:
            if default is None:
                new_value = input_field(
                    prompt,
                    default_message=(
                        git_keys[key]
                        if git_keys[key] != placeholder
                        else "leave blank to skip"
                    ),
                    default=(git_keys[key] if git_keys[key] != placeholder else None),
                )

                if new_value:
                    git_keys[key] = new_value
                else:
                    del keys[key]
            else:
                git_keys[key] = default

    git_keys = read_git_config_file(gitconfig_path, ["user:name", "user:email"])

    try_update_key(git_keys, "user:name", VCS_MISSING_NAME, name, "Enter your git name")
    try_update_key(
        git_keys, "user:email", VCS_MISSING_EMAIL, email, "Enter your git email"
    )

    update_git_config_file(gitconfig_path, git_keys)


def _detect_real_editor() -> str:
    if shutil.which("nvim"):
        return "nvim"
    if shutil.which("vim"):
        return "vim"
    env_editor = os.environ.get("EDITOR")
    if env_editor:
        return env_editor
    return "vi"


def configure_claude_code(
    settings_path: Path, dry_run: bool
) -> None:
    dry_text = "[DRY RUN] " if dry_run else ""

    settings_dir = settings_path.parent
    if not settings_dir.exists():
        if not dry_run:
            settings_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"{dry_text}Created dir {settings_dir}")

    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            logging.warning(f"Could not parse {settings_path}, skipping Claude Code configuration")
            return

    changed = False

    env = settings.get("env", {})
    desired_editor = "claude-editor"
    desired_real_editor = _detect_real_editor()

    if env.get("EDITOR") != desired_editor or env.get("REAL_EDITOR") != desired_real_editor:
        env["EDITOR"] = desired_editor
        env["REAL_EDITOR"] = desired_real_editor
        settings["env"] = env
        logging.info(f"{dry_text}Setting Claude Code EDITOR={desired_editor}, REAL_EDITOR={desired_real_editor}")
        changed = True
    else:
        logging.info(f"{dry_text}Claude Code editor already configured")

    if "statusLine" not in settings:
        settings["statusLine"] = {"type": "command", "command": "claude_status"}
        logging.info(f"{dry_text}Setting Claude Code statusLine to claude_status")
        changed = True
    else:
        logging.info(f"{dry_text}Claude Code statusLine already configured")

    if changed and not dry_run:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def configure_weather_location(
    location_path: Path | str,
    location: str | None = None,
    dry_run: bool = False,
) -> None:
    """Prompt for and persist the WEATHER_LOCATION value to `location_path`.

    If `location` is provided, it's used directly without prompting (mirrors
    `configure_vcs_author`'s `name`/`email` args).  Otherwise the user is
    shown the current value (from the file if it exists, falling back to
    $WEATHER_LOCATION) and prompted; an empty answer keeps the current value.
    Writes the file only if the resulting value is non-empty and differs from
    what's on disk.
    """
    location_path = Path(location_path)
    dry_text = "[DRY RUN] " if dry_run else ""

    on_disk: str | None = None
    if location_path.exists():
        on_disk = location_path.read_text().strip() or None

    current = on_disk or os.environ.get("WEATHER_LOCATION") or None

    if location is not None:
        new_value: str | None = location.strip() or None
    else:
        new_value = input_field("Enter your weather location", default=current)

    if not new_value:
        logging.info(f"{dry_text}No weather location set, skipping")
        return

    if new_value == on_disk:
        logging.info(f"{dry_text}Weather location already set to {new_value!r}")
        return

    if dry_run:
        logging.info(f"{dry_text}Would write weather location {new_value!r} to {location_path}")
        return

    location_path.parent.mkdir(parents=True, exist_ok=True)
    location_path.write_text(new_value + "\n")
    logging.info(f"Wrote weather location {new_value!r} to {location_path}")


def initialize_vim_plugin_manager(dry_run: bool) -> None:
    """
    Initializes the vim-plug plugin manager for vim and neovim, if they are installed on the system.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping vim plugin install")
        return

    for editor in ("nvim", "vim"):
        if shutil.which(editor) is None:
            logging.info(f"{dry_text}{editor} not installed - skip initializing vim-plug")
            continue

        logging.info(f"{dry_text}Initializing vim-plug for {editor}")

        if not dry_run:
            subprocess.check_call([editor, "+'PlugInstall --sync'", "+qa"])


def is_dotfiles_root(path: Path) -> bool:
    """Check if a path is the root of a dotfiles repository."""
    return path.joinpath(".__dotfiles_root__").is_file()


def create_backup_filename(target: Path) -> Path:
    backup_path = Path(str(target) + ".ORIGINAL")

    if backup_path.exists():
        name, ext = os.path.splitext(backup_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")[
            :-3
        ]  # First three millisecond digits.
        backup_path = Path(f"{name}_{timestamp}{ext}")

    return backup_path


def safe_symlink(source: Path, target: Path, dry_run: bool) -> None:
    """
    Create a shared config file that is symlinked to its source dotfile config. Any changes to the
    target config file will be reflected in the dotfiles checkout.

    This function tries to take precautions when creating the symlink. Targets that are already
    symlinked to `source` are skipped. If the target already exists, it will be renamed to
    `.ORIGINAL`

    Args:
        source: A dotfiles file to symlink to.
        target: Path in the user's home directory that will be symlinked to `source`.
        dry_run: Print the action but don't actually do it.
    """
    if not source.exists():
        raise ValueError(f"{source} does not exist")

    dry_text = "[DRY RUN] " if dry_run else ""

    # Create the directory leading up to the target if it doesn't exist.
    if not target.exists():
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)

        logging.info(f"{dry_text}Created dir {target.parent}")

    # Skip if the target is already symlinked to source.
    if target.is_symlink() and target.resolve() == source.resolve():
        logging.info(f"{dry_text}{target} is already symlinked to {source}")
        return

    # Remove broken symlinks so we can replace them.
    if target.is_symlink() and not target.exists():
        if not dry_run:
            target.unlink()
        logging.info(f"{dry_text}Removed broken symlink {target}")

    # Does the target file name already exist on the disk?
    if target.exists():
        # Ask user if they would like to "back up" the file by renaming before replacing it with a
        # symlink.
        backup_path = create_backup_filename(target)

        if confirm(
            message=f"{Colors.BOLD}Rename {target} to {backup_path.name} before replacing with symlink?{Colors.RESET}",
            default=True,
        ):
            if not dry_run:
                target.rename(backup_path)

            logging.info(f"{dry_text}Renamed {target} to {backup_path}")
        else:
            if not dry_run:
                target.unlink()

            logging.warning(f"{dry_text}Deleted {target}")

    # Create the symlink.
    if not dry_run:
        target.symlink_to(source)

    logging.info(f"{dry_text}Symlinked {target} to {source}")


def make_local_config(source: Path, target: Path) -> bool:
    """
    Create a local config file copy from the dotfiles repo rather than a symlink. This allows the
    user to modify the file without having the changes reflected in the dotfiles checkout.

    Args:
        source: Path to the source dotfiles file.
        target: Path to the target file.
    """
    if target.exists():
        logging.info(f"{target} already exists")
        return False

    if not source.exists():
        raise ValueError(f"{source} does not exist")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

    logging.info(f"Cloned config {source} to {target}")

    return True


def create_dirs(dry_run: bool, dirs: list[str | Path]) -> None:
    dry_text = "[DRY RUN] " if dry_run else ""

    for d in dirs:
        d = Path(d)

        if d.exists() and not d.is_dir():
            logging.error(f"{dry_text}expected {d} to be a directory, but it is not")
        elif d.exists():
            logging.info(f"{dry_text}{d} already exists")
        else:
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

            logging.info(f"{dry_text}Created dir {d}")


def download_file(url: str, dest: Path, dry_run: bool) -> bool:
    """
    Download a file from URL to a destination path.
    Tries urllib first, falls back to curl if SSL issues occur.

    Args:
        url: URL to download from.
        dest: Destination path for the downloaded file.
        dry_run:

    Returns:
        True if download succeeded, False otherwise.
    """
    if dry_run:
        logging.info(f"[DRY RUN] Would download {url} to {dest}")
        return True

    try:
        with urllib.request.urlopen(
            url, context=ssl.create_default_context(), timeout=10
        ) as response:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(response.read())

            logging.info(f"Downloaded {url} to {dest}")
            return True
    except (ssl.SSLError, urllib.error.URLError) as e:
        logging.info(
            f"downloading with urllib failed, will try curl instead. (exception: {e})"
        )

        try:
            subprocess.run(
                ["curl", "-fLo", str(dest), "--create-dirs", "--connect-timeout", "10", url],
                capture_output=True,
                check=True,
            )

            logging.info(f"Downloaded {url} to {dest} with curl")
            return True
        except subprocess.CalledProcessError as curl_error:
            stderr = curl_error.stderr.decode().strip() if curl_error.stderr else ""
            logging.exception(f"Failed to download {url} with curl: {stderr}")
            return False
        except FileNotFoundError:
            logging.exception("`curl` was not found. Please install it")
            return False


@functools.cache
def _has_internet() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def download_files(
    urls: list[tuple[str, Path]],
    dry_run: bool,
    skip_if_dest_exists: bool = True,
) -> None:
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping downloads")
        return

    for url, target in urls:
        target = Path(target)

        if skip_if_dest_exists and target.exists():
            logging.info(f"{dry_text}{target} already exists - skipping download")
        else:
            download_file(url=url, dest=target, dry_run=dry_run)


def git_clone(url: str, dest: Path, dry_run: bool, depth: int | None = None) -> bool:
    """
    Clone a git repository to a destination path.

    Args:
        url: Git repository URL to clone.
        dest: Destination directory for the cloned repository.
        dry_run: Print the action but don't actually do it.
        depth: If specified, create a shallow clone with this history depth.

    Returns:
        True if clone succeeded, False otherwise.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    cmd = ["git", "clone"]
    if depth is not None:
        cmd += ["--depth", str(depth)]
    cmd += [url, str(dest)]

    logging.info(f"{dry_text}Cloning {url} to {dest}")

    if not dry_run:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clone {url}: {e.stderr.decode().strip()}")
            return False

    return True


def git_clone_repos(
    repos: list[tuple[str, Path]],
    dry_run: bool,
    skip_if_dest_exists: bool = True,
    depth: int | None = None,
) -> None:
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping git clones")
        return

    for url, dest in repos:
        dest = Path(dest)

        if skip_if_dest_exists and dest.exists():
            logging.info(f"{dry_text}{dest} already exists - skipping clone")
        else:
            git_clone(url=url, dest=dest, dry_run=dry_run, depth=depth)
