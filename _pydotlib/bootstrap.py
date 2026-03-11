"""
Utility functions for the bootstrap.py program.
"""

import json
import logging
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import unittest
import urllib.request
import urllib.error
from unittest.mock import MagicMock, patch

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

    env = settings.get("env", {})
    desired_editor = "claude-editor"
    desired_real_editor = _detect_real_editor()

    if env.get("EDITOR") == desired_editor and env.get("REAL_EDITOR") == desired_real_editor:
        logging.info(f"{dry_text}Claude Code editor already configured")
        return

    env["EDITOR"] = desired_editor
    env["REAL_EDITOR"] = desired_real_editor
    settings["env"] = env

    logging.info(f"{dry_text}Setting Claude Code EDITOR={desired_editor}, REAL_EDITOR={desired_real_editor}")

    if not dry_run:
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


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
    dry_text = "[DRY RUN] " if dry_run else ""

    # Try to download the file using Python's builtin urllib module.
    try:
        with urllib.request.urlopen(
            url, context=ssl.create_default_context(), timeout=10
        ) as response:
            # Create destination directory if it does not already exist.
            dest_dir = dest.parent

            if not dest_dir.exists():
                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)

                logging.info(f"{dry_text}Created dir {dest_dir}")

            # Write the downloaded bytes to the destination directory.
            if not dry_run:
                dest.write_bytes(response.read())

            logging.info(f"{dry_text}Downloaded {url} to {dest}")
            return True
    # Fallback to curl if exceptions are encountered.
    except (ssl.SSLError, urllib.error.URLError) as e:
        logging.info(
            f"{dry_text}downloading with urllib failed, will try curl instead. (exception: {e})"
        )

        try:
            result = subprocess.run(
                ["curl", "-fLo", str(dest), "--create-dirs", "--connect-timeout", "10", url],
                capture_output=True,
                check=True,
            )

            logging.info(f"{dry_text}Downloaded {url} to {dest} with curl")
            return True
        except subprocess.CalledProcessError as curl_error:
            logging.exception(f"Failed to download {url} with curl", exc_info=e)
            return False
        except FileNotFoundError:
            logging.exception(f"`curl` was not found. Please install it", exc_info=e)
            return False

    except Exception as e:
        logging.exception(f"Unexpected error downloading {url}", exc_info=e)
        return False


def _has_internet(timeout: float = 5) -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=timeout).close()
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


class TestIsDotfilesRoot(unittest.TestCase):
    def test_returns_true_when_marker_file_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            marker = tmp_path / ".__dotfiles_root__"
            marker.touch()

            self.assertTrue(is_dotfiles_root(tmp_path))

    def test_returns_false_when_marker_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            self.assertFalse(is_dotfiles_root(tmp_path))


class TestCreateBackupFilename(unittest.TestCase):
    def test_creates_original_suffix(self):
        target = Path("/home/user/.bashrc")
        backup = create_backup_filename(target)

        self.assertEqual(backup, Path("/home/user/.bashrc.ORIGINAL"))

    def test_adds_timestamp_if_original_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            target = tmp_path / ".bashrc"
            original = tmp_path / ".bashrc.ORIGINAL"
            original.touch()

            backup = create_backup_filename(target)

            self.assertTrue(str(backup).startswith(str(tmp_path / ".bashrc_")))
            self.assertTrue(str(backup).endswith(".ORIGINAL"))
            self.assertNotEqual(backup, original)

            filename = backup.name
            self.assertRegex(filename, r"\.bashrc_\d+\.ORIGINAL")


class TestSafeSymlink(unittest.TestCase):
    def test_replaces_broken_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source = tmp_path / "source"
            source.touch()
            target = tmp_path / "target"

            target.symlink_to(tmp_path / "nonexistent")
            self.assertTrue(target.is_symlink())
            self.assertFalse(target.exists())

            safe_symlink(source, target, dry_run=False)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())


class TestGitClone(unittest.TestCase):
    @patch("subprocess.run")
    def test_clones_repo_to_dest(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            result = git_clone("https://example.com/repo.git", dest, dry_run=False)

            self.assertTrue(result)
            mock_run.assert_called_once_with(
                ["git", "clone", "https://example.com/repo.git", str(dest)],
                check=True,
                capture_output=True,
            )

    @patch("subprocess.run")
    def test_clones_with_depth(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            result = git_clone(
                "https://example.com/repo.git", dest, dry_run=False, depth=1
            )

            self.assertTrue(result)
            mock_run.assert_called_once_with(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "https://example.com/repo.git",
                    str(dest),
                ],
                check=True,
                capture_output=True,
            )

    @patch("subprocess.run")
    def test_dry_run_skips_clone(self, mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            result = git_clone("https://example.com/repo.git", dest, dry_run=True)

            self.assertTrue(result)
            mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_returns_false_on_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "clone"],
            stderr=b"fatal: repository not found",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"
            result = git_clone("https://example.com/repo.git", dest, dry_run=False)

            self.assertFalse(result)

    @patch("subprocess.run")
    def test_git_clone_repos_skips_existing_dest(self, mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "existing"
            dest.mkdir()

            git_clone_repos(
                [("https://example.com/repo.git", dest)], dry_run=False
            )

            mock_run.assert_not_called()

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.run")
    def test_git_clone_repos_clones_when_dest_missing(self, mock_run, _):
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "repo"

            git_clone_repos(
                [("https://example.com/repo.git", dest)], dry_run=False
            )

            mock_run.assert_called_once()


class TestConfigureClaudeCode(unittest.TestCase):
    def test_creates_settings_from_scratch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")
            self.assertIn(settings["env"]["REAL_EDITOR"], ("nvim", "vim", "vi"))

    def test_preserves_existing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(json.dumps({"hooks": {"some": "hook"}}))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["hooks"], {"some": "hook"})
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")

    def test_preserves_existing_env_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(json.dumps({"env": {"FOO": "bar"}}))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["FOO"], "bar")
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")

    def test_noop_when_already_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            real_editor = _detect_real_editor()
            existing = {"env": {"EDITOR": "claude-editor", "REAL_EDITOR": real_editor}}
            settings_path.write_text(json.dumps(existing))
            mtime_before = settings_path.stat().st_mtime

            configure_claude_code(settings_path, dry_run=False)

            mtime_after = settings_path.stat().st_mtime
            self.assertEqual(mtime_before, mtime_after)

    def test_skips_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text("{invalid json")

            configure_claude_code(settings_path, dry_run=False)

            self.assertEqual(settings_path.read_text(), "{invalid json")

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=True)

            self.assertFalse(settings_path.exists())


class TestDetectRealEditor(unittest.TestCase):
    @patch("shutil.which", side_effect=lambda cmd: "/usr/bin/nvim" if cmd == "nvim" else None)
    def test_prefers_nvim(self, _):
        self.assertEqual(_detect_real_editor(), "nvim")

    @patch("shutil.which", side_effect=lambda cmd: "/usr/bin/vim" if cmd == "vim" else None)
    def test_falls_back_to_vim(self, _):
        self.assertEqual(_detect_real_editor(), "vim")

    @patch("shutil.which", return_value=None)
    @patch.dict(os.environ, {"EDITOR": "nano"})
    def test_falls_back_to_env_editor(self, _):
        self.assertEqual(_detect_real_editor(), "nano")

    @patch("shutil.which", return_value=None)
    @patch.dict(os.environ, {}, clear=True)
    def test_falls_back_to_vi(self, _):
        self.assertEqual(_detect_real_editor(), "vi")
