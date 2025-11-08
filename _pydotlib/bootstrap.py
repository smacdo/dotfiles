import logging
import os.path
import shutil
from datetime import datetime
from pathlib import Path

from _pydotlib.colors import Colors
from _pydotlib.cli import confirm


def is_dotfiles_root(path: Path) -> bool:
    return path.joinpath(".__dotfiles_root__").is_file()


def create_backup_filename(target: Path) -> Path:
    backup_path = Path(str(target) + ".ORIGINAL")

    if backup_path.exists():
        name, ext = os.path.splitext(backup_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")[
            :-3
        ]  # First three millisecond digits.
        backup_path = Path(f"{name}_{timestamp}.{ext}")

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

        logging.info(f"{dry_text}Created dir {target}")

    # Skip if the target is already symlinked to source.
    if target.is_symlink() and target.resolve() == source.resolve():
        logging.info(f"{dry_text}{target} is already symlinked to {source}")
        return

    # Does the target file name already exist on the disk?
    if target.exists():
        # Ask user if they would like to "back up" the file by renaming before replacing it with a
        # symlink.
        # TODO: Add cancel option, which is to skip.
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
        logging.info(f"{source} already exists")
        return False

    if not source.exists():
        raise ValueError(f"{source} does not exist")

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

    logging.info(f"Cloned config {source} to {target}")

    return True