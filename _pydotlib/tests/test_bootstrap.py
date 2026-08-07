import importlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

tomllib: Any
try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:
    tomllib = None

TOMLLIB_AVAILABLE = tomllib is not None

from _pydotlib.bootstrap import (
    _CTS,
    CLAUDE_TMUX_STATE_HOOKS,
    CLAUDE_TMUX_STATE_MARKER,
    CODEX_STATUS_LINE,
    _ConfigMergeError,
    _ConfigWriteError,
    _detect_real_editor,
    _merge_claude_tmux_hooks,
    _merge_codex_config,
    _write_config_text,
    configure_claude_code,
    configure_codex,
    configure_vcs_author,
    configure_weather_location,
    create_backup_filename,
    create_dirs,
    download_file,
    download_files,
    find_dotfiles_root,
    git_clone,
    git_clone_repos,
    initialize_vim_plugin_manager,
    is_dotfiles_root,
    resolve_codex_config_path,
    safe_symlink,
)


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


class TestFindDotfilesRoot(unittest.TestCase):
    def test_returns_path_when_marker_in_start_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".__dotfiles_root__").touch()
            self.assertEqual(find_dotfiles_root(root), root.resolve())

    def test_walks_up_to_find_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".__dotfiles_root__").touch()
            deep = root / "a" / "b" / "c"
            deep.mkdir(parents=True)
            self.assertEqual(find_dotfiles_root(deep), root.resolve())

    def test_returns_none_when_no_marker_in_ancestry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(find_dotfiles_root(Path(tmpdir)))

    def test_stops_at_filesystem_root_without_infinite_loop(self):
        # Sanity: a deeply nested path with no marker anywhere terminates.
        with tempfile.TemporaryDirectory() as tmpdir:
            deep = Path(tmpdir) / "x" / "y" / "z"
            deep.mkdir(parents=True)
            self.assertIsNone(find_dotfiles_root(deep))


class TestConfigureVcsAuthor(unittest.TestCase):
    @patch(
        "_pydotlib.bootstrap.input_field",
        side_effect=lambda *_, **kw: kw.get("default"),
    )
    def test_adds_missing_email_when_arg_provided(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".my_gitconfig"
            path.write_text("[user]\n\tname = Alice\n")

            configure_vcs_author(path, email="alice@example.com")

            content = path.read_text()
            self.assertIn("name = Alice", content)
            self.assertIn("email = alice@example.com", content)

    def test_creates_file_with_provided_args(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".my_gitconfig"

            configure_vcs_author(path, name="Bob", email="bob@example.com")

            content = path.read_text()
            self.assertIn("name = Bob", content)
            self.assertIn("email = bob@example.com", content)

    def test_dry_run_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".my_gitconfig"

            configure_vcs_author(path, name="Bob", email="bob@example.com", dry_run=True)

            self.assertFalse(path.exists())

    def test_dry_run_does_not_modify_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".my_gitconfig"
            original = "[user]\n\tname = Alice\n"
            path.write_text(original)

            configure_vcs_author(path, email="alice@example.com", dry_run=True)

            self.assertEqual(path.read_text(), original)


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


class TestCreateDirs(unittest.TestCase):
    def test_creates_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "nested" / "dir"
            create_dirs(dry_run=False, dirs=[target])
            self.assertTrue(target.is_dir())

    def test_noop_when_directory_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            mtime_before = target.stat().st_mtime
            create_dirs(dry_run=False, dirs=[target])
            self.assertEqual(target.stat().st_mtime, mtime_before)

    def test_logs_error_when_path_is_a_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "afile"
            target.touch()
            with self.assertLogs(level="ERROR") as logs:
                create_dirs(dry_run=False, dirs=[target])
            self.assertTrue(any("expected" in m for m in logs.output))
            self.assertTrue(target.is_file())

    def test_dry_run_does_not_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "nested" / "dir"
            create_dirs(dry_run=True, dirs=[target])
            self.assertFalse(target.exists())


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

    def test_creates_new_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            source.touch()
            target = tmp / "target"

            safe_symlink(source, target, dry_run=False)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())

    def test_noop_when_target_already_symlinked_to_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            source.touch()
            target = tmp / "target"
            target.symlink_to(source)
            mtime_before = target.lstat().st_mtime

            safe_symlink(source, target, dry_run=False)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.lstat().st_mtime, mtime_before)

    @patch("_pydotlib.bootstrap.confirm", return_value=True)
    def test_backs_up_existing_file_when_confirmed(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            source.write_text("new")
            target = tmp / "target"
            target.write_text("old")

            safe_symlink(source, target, dry_run=False)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())
            backup = tmp / "target.ORIGINAL"
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(), "old")

    @patch("_pydotlib.bootstrap.confirm", return_value=False)
    def test_skips_when_backup_declined(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            source.write_text("new")
            target = tmp / "target"
            target.write_text("old")

            safe_symlink(source, target, dry_run=False)

            # Target untouched, no symlink, no backup.
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_text(), "old")
            self.assertFalse((tmp / "target.ORIGINAL").exists())

    def test_raises_when_source_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with self.assertRaises(FileNotFoundError):
                safe_symlink(tmp / "nope", tmp / "target", dry_run=False)

    def test_dry_run_does_not_modify_filesystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source"
            source.touch()
            target = tmp / "subdir" / "target"

            safe_symlink(source, target, dry_run=True)

            # Neither the target nor its parent dir should have been created.
            self.assertFalse(target.exists())
            self.assertFalse(target.parent.exists())

    @patch("_pydotlib.bootstrap.confirm", return_value=True)
    def test_backs_up_existing_directory(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source_dir"
            source.mkdir()
            (source / "marker").write_text("from_source")

            target = tmp / "target_dir"
            target.mkdir()
            (target / "old_file").write_text("from_target")

            safe_symlink(source, target, dry_run=False)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())
            backup = tmp / "target_dir.ORIGINAL"
            self.assertTrue(backup.is_dir())
            self.assertEqual((backup / "old_file").read_text(), "from_target")

    @patch("_pydotlib.bootstrap.confirm")
    def test_auto_updates_stale_dotfiles_symlink(self, mock_confirm):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            dotfiles = tmp / "dotfiles"
            dotfiles.mkdir()
            old_source = dotfiles / "old_path"
            old_source.touch()
            new_source = dotfiles / "new_path"
            new_source.touch()
            target = tmp / "target"
            target.symlink_to(old_source)

            safe_symlink(new_source, target, dry_run=False, dotfiles_root=dotfiles)

            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), new_source.resolve())
            self.assertFalse((tmp / "target.ORIGINAL").exists())
            mock_confirm.assert_not_called()

    @patch("_pydotlib.bootstrap.confirm", return_value=True)
    def test_does_not_auto_update_when_symlink_points_outside_dotfiles(self, mock_confirm):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            dotfiles = tmp / "dotfiles"
            dotfiles.mkdir()
            source = dotfiles / "source"
            source.touch()

            external = tmp / "external"
            external.touch()
            target = tmp / "target"
            target.symlink_to(external)

            safe_symlink(source, target, dry_run=False, dotfiles_root=dotfiles)

            # Falls through to backup-prompt path (confirm called, .ORIGINAL created).
            mock_confirm.assert_called_once()
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())
            self.assertTrue((tmp / "target.ORIGINAL").is_symlink())

    @patch("_pydotlib.bootstrap.confirm", return_value=True)
    def test_does_not_auto_update_when_dotfiles_root_not_provided(self, mock_confirm):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            dotfiles = tmp / "dotfiles"
            dotfiles.mkdir()
            old_source = dotfiles / "old_path"
            old_source.touch()
            new_source = dotfiles / "new_path"
            new_source.touch()
            target = tmp / "target"
            target.symlink_to(old_source)

            # No dotfiles_root passed — falls back to backup prompt.
            safe_symlink(new_source, target, dry_run=False)

            mock_confirm.assert_called_once()
            self.assertTrue((tmp / "target.ORIGINAL").exists())


class TestDownloadFile(unittest.TestCase):
    def test_dry_run_returns_true_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out" / "file"
            self.assertTrue(download_file("https://example.com/x", dest, dry_run=True))
            self.assertFalse(dest.exists())
            self.assertFalse(dest.parent.exists())

    @patch("urllib.request.urlopen")
    def test_urllib_happy_path(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"payload"

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "nested" / "out"
            self.assertTrue(download_file("https://example.com/x", dest, dry_run=False))
            self.assertEqual(dest.read_bytes(), b"payload")

    @patch("subprocess.run")
    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("nope"))
    def test_falls_back_to_curl_on_urllib_error(self, _, mock_run):
        def curl_run(command, **_kwargs):
            Path(command[2]).write_bytes(b"payload")
            return MagicMock(returncode=0)

        mock_run.side_effect = curl_run
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            self.assertTrue(download_file("https://example.com/x", dest, dry_run=False))
            self.assertEqual(dest.read_bytes(), b"payload")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args[0], "curl")
            self.assertIn("https://example.com/x", args)
            self.assertNotIn(str(dest), args)

    @patch("subprocess.run")
    @patch("urllib.request.urlopen", side_effect=ssl.SSLError("bad cert"))
    def test_falls_back_to_curl_on_ssl_error(self, _, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            self.assertTrue(download_file("https://example.com/x", dest, dry_run=False))
            mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("nope"))
    def test_returns_false_when_curl_fails(self, _, mock_run):
        def curl_run(command, **_kwargs):
            Path(command[2]).write_bytes(b"partial")
            raise subprocess.CalledProcessError(
                22, command, stderr=b"server returned 404"
            )

        mock_run.side_effect = curl_run
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            dest.write_bytes(b"original")
            self.assertFalse(download_file("https://example.com/x", dest, dry_run=False))
            self.assertEqual(dest.read_bytes(), b"original")
            self.assertEqual(list(Path(tmpdir).iterdir()), [dest])

    @patch("subprocess.run", side_effect=FileNotFoundError("curl"))
    @patch("urllib.request.urlopen", side_effect=urllib.error.URLError("nope"))
    def test_returns_false_when_curl_missing(self, _urlopen, _run):
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "out"
            self.assertFalse(download_file("https://example.com/x", dest, dry_run=False))


class TestDownloadFiles(unittest.TestCase):
    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("_pydotlib.bootstrap.download_file")
    def test_skips_when_target_exists(self, mock_download, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out"
            target.touch()
            download_files([("https://x", target)], dry_run=False)
            mock_download.assert_not_called()

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("_pydotlib.bootstrap.download_file")
    def test_downloads_when_target_missing(self, mock_download, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out"
            download_files([("https://x", target)], dry_run=False)
            mock_download.assert_called_once_with(url="https://x", dest=target, dry_run=False)

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("_pydotlib.bootstrap.download_file")
    def test_redownloads_when_skip_disabled(self, mock_download, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out"
            target.touch()
            download_files(
                [("https://x", target)], dry_run=False, skip_if_dest_exists=False
            )
            mock_download.assert_called_once()

    @patch("_pydotlib.bootstrap._has_internet", return_value=False)
    @patch("_pydotlib.bootstrap.download_file")
    def test_skips_all_when_offline(self, mock_download, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            download_files([("https://x", Path(tmpdir) / "out")], dry_run=False)
            mock_download.assert_not_called()


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

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.run")
    def test_git_clone_repos_skips_existing_dest(self, mock_run, _):
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


class TestInitializeVimPluginManager(unittest.TestCase):
    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.check_call")
    @patch("shutil.which", return_value="/usr/bin/nvim")
    def test_runs_plug_install_for_nvim(self, _which, mock_check_call, _net):
        initialize_vim_plugin_manager(dry_run=False)
        mock_check_call.assert_called_once()
        cmd = mock_check_call.call_args[0][0]
        self.assertEqual(cmd[0], "nvim")
        self.assertIn("PlugInstall --sync", cmd)

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.check_call")
    @patch("shutil.which", return_value="/usr/bin/anything")
    def test_never_invokes_vim_even_when_present(self, _which, mock_check_call, _net):
        # Regression guard: vim has no plug#begin, so it must never be invoked
        # even though it's "installed". Catches reintroducing the editor loop.
        initialize_vim_plugin_manager(dry_run=False)
        invoked = [c.args[0][0] for c in mock_check_call.call_args_list]
        self.assertEqual(invoked, ["nvim"])

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.check_call")
    @patch("shutil.which", return_value="/usr/bin/nvim")
    def test_dry_run_does_not_invoke_editor(self, _which, mock_check_call, _net):
        initialize_vim_plugin_manager(dry_run=True)
        mock_check_call.assert_not_called()

    @patch("_pydotlib.bootstrap._has_internet", return_value=True)
    @patch("subprocess.check_call")
    @patch("shutil.which", return_value=None)
    def test_skips_when_nvim_not_installed(self, _which, mock_check_call, _net):
        initialize_vim_plugin_manager(dry_run=False)
        mock_check_call.assert_not_called()

    @patch("_pydotlib.bootstrap._has_internet", return_value=False)
    @patch("subprocess.check_call")
    @patch("shutil.which", return_value="/usr/bin/nvim")
    def test_skips_when_offline(self, _which, mock_check_call, _net):
        initialize_vim_plugin_manager(dry_run=False)
        mock_check_call.assert_not_called()


class TestWriteConfigText(unittest.TestCase):
    def test_creates_private_file_without_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "settings.json"

            changed = _write_config_text(
                path,
                "new\n",
                expected_content=None,
                dry_run=False,
                description="test settings",
            )

            self.assertTrue(changed)
            self.assertEqual(path.read_text(), "new\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(Path(str(path) + ".ORIGINAL").exists())
            self.assertEqual(
                {entry.name for entry in path.parent.iterdir()},
                {"settings.json"},
            )

    def test_existing_file_keeps_mode_and_one_time_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("original\n")
            path.chmod(0o640)

            _write_config_text(
                path,
                "first update\n",
                expected_content="original\n",
                dry_run=False,
                description="test settings",
            )
            _write_config_text(
                path,
                "second update\n",
                expected_content="first update\n",
                dry_run=False,
                description="test settings",
            )

            self.assertEqual(path.read_text(), "second update\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(
                Path(str(path) + ".ORIGINAL").read_text(),
                "original\n",
            )
            self.assertEqual(
                {entry.name for entry in path.parent.iterdir()},
                {"settings.json", "settings.json.ORIGINAL"},
            )

    def test_unchanged_file_does_not_touch_filesystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("same\n")
            before = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}

            with (
                patch("_pydotlib.bootstrap.os.replace") as replace,
                patch("_pydotlib.bootstrap.shutil.copy2") as copy2,
            ):
                changed = _write_config_text(
                    path,
                    "same\n",
                    expected_content="same\n",
                    dry_run=False,
                    description="test settings",
                )

            self.assertFalse(changed)
            replace.assert_not_called()
            copy2.assert_not_called()
            after = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}
            self.assertEqual(after, before)

    def test_dry_run_leaves_missing_tree_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "nested" / "settings.json"

            changed = _write_config_text(
                path,
                "new\n",
                expected_content=None,
                dry_run=True,
                description="test settings",
            )

            self.assertTrue(changed)
            self.assertEqual(list(root.iterdir()), [])

    def test_replace_failure_preserves_live_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("original\n")

            before_entries = {entry.name for entry in path.parent.iterdir()}
            with (
                patch(
                    "_pydotlib.bootstrap.os.replace",
                    side_effect=OSError("replace failed"),
                ) as replace,
                self.assertRaisesRegex(OSError, "replace failed"),
            ):
                _write_config_text(
                    path,
                    "updated\n",
                    expected_content="original\n",
                    dry_run=False,
                    description="test settings",
                )

            self.assertEqual(path.read_text(), "original\n")
            self.assertEqual(
                Path(str(path) + ".ORIGINAL").read_text(),
                "original\n",
            )
            temp_path = Path(replace.call_args.args[0])
            self.assertFalse(temp_path.exists())
            self.assertEqual(
                {entry.name for entry in path.parent.iterdir()} - before_entries,
                {"settings.json.ORIGINAL"},
            )

    def test_cleanup_failure_does_not_mask_replace_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("original\n")

            with (
                patch(
                    "_pydotlib.bootstrap.os.replace",
                    side_effect=OSError("primary replace failure"),
                ),
                patch.object(
                    Path,
                    "unlink",
                    side_effect=OSError("secondary cleanup failure"),
                ),
                self.assertLogs(level="WARNING") as logs,
                self.assertRaisesRegex(OSError, "primary replace failure"),
            ):
                _write_config_text(
                    path,
                    "updated\n",
                    expected_content="original\n",
                    dry_run=False,
                    description="test settings",
                )

            self.assertTrue(any("secondary cleanup failure" in line for line in logs.output))
            self.assertEqual(path.read_text(), "original\n")

    def test_stale_expected_content_is_not_overwritten_or_backed_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("concurrent update\n")
            before = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}

            with (
                patch("_pydotlib.bootstrap.os.replace") as replace,
                self.assertRaisesRegex(_ConfigWriteError, "changed"),
            ):
                _write_config_text(
                    path,
                    "generated update\n",
                    expected_content="stale original\n",
                    dry_run=False,
                    description="test settings",
                )

            replace.assert_not_called()
            after = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}
            self.assertEqual(after, before)

    def test_change_during_temp_write_is_not_overwritten_or_backed_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            path.write_text("original\n")
            before = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}

            with (
                patch.object(
                    Path,
                    "read_text",
                    side_effect=["original\n", "concurrent update\n"],
                ) as read_text,
                patch("_pydotlib.bootstrap.os.replace") as replace,
                self.assertRaisesRegex(_ConfigWriteError, "being written"),
            ):
                _write_config_text(
                    path,
                    "generated update\n",
                    expected_content="original\n",
                    dry_run=False,
                    description="test settings",
                )

            self.assertEqual(read_text.call_count, 2)
            replace.assert_not_called()
            after = {entry.name: entry.read_bytes() for entry in path.parent.iterdir()}
            self.assertEqual(after, before)

    def test_symlink_is_preserved_and_target_is_not_changed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "owned-elsewhere.toml"
            target.write_text("original\n")
            path = root / "config.toml"
            path.symlink_to(target)

            with self.assertRaisesRegex(_ConfigWriteError, "symlink"):
                _write_config_text(
                    path,
                    "updated\n",
                    expected_content="original\n",
                    dry_run=False,
                    description="test settings",
                )

            self.assertTrue(path.is_symlink())
            self.assertEqual(target.read_text(), "original\n")
            self.assertFalse(Path(str(path) + ".ORIGINAL").exists())


@unittest.skipUnless(TOMLLIB_AVAILABLE, "tomllib requires Python 3.11")
class TestMergeCodexConfig(unittest.TestCase):
    def test_empty_config_adds_valid_tui_table(self):
        updated, changed = _merge_codex_config("")

        self.assertTrue(changed)
        self.assertEqual(
            tomllib.loads(updated),
            {"tui": {"status_line": list(CODEX_STATUS_LINE)}},
        )

    def test_inserts_into_existing_tui_without_reformatting(self):
        source = (
            "# Keep this Unicode comment: café\n"
            'model = "example"\n'
            "\n"
            "[tui]\n"
            'alternate_screen = "auto"\n'
            "\n"
            "[projects.\"/tmp/example\"]\n"
            'trust_level = "trusted"\n'
        )

        updated, changed = _merge_codex_config(source)

        inserted = f"status_line = {json.dumps(list(CODEX_STATUS_LINE))}\n"
        self.assertTrue(changed)
        self.assertEqual(updated.replace(inserted, "", 1), source)
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed["tui"]["status_line"], list(CODEX_STATUS_LINE))
        self.assertEqual(parsed["model"], "example")
        self.assertEqual(
            parsed["projects"]["/tmp/example"]["trust_level"],
            "trusted",
        )

    def test_new_tui_table_is_not_nested_under_last_project(self):
        source = (
            "[projects.\"/tmp/example\"]\n"
            'trust_level = "trusted"\n'
        )
        inserted = (
            f"\n[tui]\nstatus_line = {json.dumps(list(CODEX_STATUS_LINE))}\n"
        )

        updated, changed = _merge_codex_config(source)

        self.assertTrue(changed)
        self.assertEqual(updated.replace(inserted, "", 1), source)
        self.assertEqual(
            tomllib.loads(updated),
            {
                "projects": {"/tmp/example": {"trust_level": "trusted"}},
                "tui": {"status_line": list(CODEX_STATUS_LINE)},
            },
        )

    def test_extends_root_dotted_tui_key_without_reformatting(self):
        source = (
            'tui.alternate_screen = "auto"\n'
            'model = "example"\n'
        )
        inserted = f"tui.status_line = {json.dumps(list(CODEX_STATUS_LINE))}\n"

        updated, changed = _merge_codex_config(source)

        self.assertTrue(changed)
        self.assertEqual(updated.removeprefix(inserted), source)
        self.assertEqual(
            tomllib.loads(updated),
            {
                "tui": {
                    "status_line": list(CODEX_STATUS_LINE),
                    "alternate_screen": "auto",
                },
                "model": "example",
            },
        )

    def test_extends_implicit_tui_parent_despite_fake_header_in_string(self):
        source = (
            'message = """\n'
            "[tui]\n"
            'not_a_real_table = true\n"""\n'
            "[tui.keymap]\n"
            'binding = "ctrl-a"\n'
        )
        inserted = f"tui.status_line = {json.dumps(list(CODEX_STATUS_LINE))}\n"

        updated, changed = _merge_codex_config(source)

        self.assertTrue(changed)
        self.assertEqual(updated.removeprefix(inserted), source)
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed["message"], "[tui]\nnot_a_real_table = true\n")
        self.assertEqual(parsed["tui"]["keymap"], {"binding": "ctrl-a"})
        self.assertEqual(parsed["tui"]["status_line"], list(CODEX_STATUS_LINE))

    def test_uses_real_tui_header_after_fake_header_in_string(self):
        source = (
            'message = """\n'
            "[tui]\n"
            'not_a_real_table = true\n"""\n'
            "[tui]\n"
            'alternate_screen = "auto"\n'
        )
        inserted = f"status_line = {json.dumps(list(CODEX_STATUS_LINE))}\n"

        updated, changed = _merge_codex_config(source)

        self.assertTrue(changed)
        self.assertEqual(updated.replace(inserted, "", 1), source)
        parsed = tomllib.loads(updated)
        self.assertEqual(parsed["message"], "[tui]\nnot_a_real_table = true\n")
        self.assertEqual(parsed["tui"]["alternate_screen"], "auto")
        self.assertEqual(parsed["tui"]["status_line"], list(CODEX_STATUS_LINE))

    def test_preserves_crlf_line_endings(self):
        source = "[tui]\r\nalternate_screen = \"auto\"\r\n"

        updated, changed = _merge_codex_config(source)

        self.assertTrue(changed)
        self.assertNotIn("\n", updated.replace("\r\n", ""))
        self.assertEqual(
            tomllib.loads(updated)["tui"]["status_line"],
            list(CODEX_STATUS_LINE),
        )

    def test_existing_table_status_line_is_exact_noop(self):
        source = '[tui]\nstatus_line = ["model"]\n'

        updated, changed = _merge_codex_config(source)

        self.assertFalse(changed)
        self.assertEqual(updated, source)

    def test_existing_dotted_status_line_is_exact_noop(self):
        source = (
            'tui.status_line = ["model"]\n'
            "\n"
            "[projects.\"/tmp/example\"]\n"
            'trust_level = "trusted"\n'
        )

        updated, changed = _merge_codex_config(source)

        self.assertFalse(changed)
        self.assertEqual(updated, source)

    def test_second_merge_is_byte_identical_noop(self):
        first, changed = _merge_codex_config('model = "example"\n')
        second, changed_again = _merge_codex_config(first)

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(second, first)

    def test_rejects_scalar_tui(self):
        with self.assertRaisesRegex(_ConfigMergeError, "not a table"):
            _merge_codex_config('tui = "custom"\n')

    def test_rejects_unsupported_inline_tui(self):
        with self.assertRaisesRegex(_ConfigMergeError, "unsupported TOML form"):
            _merge_codex_config('tui = { alternate_screen = "auto" }\n')

    def test_rejects_malformed_toml(self):
        with self.assertRaisesRegex(_ConfigMergeError, "invalid TOML"):
            _merge_codex_config("[tui\n")


class TestResolveCodexConfigPath(unittest.TestCase):
    def test_defaults_to_dot_codex_under_home(self):
        self.assertEqual(
            resolve_codex_config_path(Path("/home/example"), None),
            Path("/home/example/.codex/config.toml"),
        )

    def test_honors_custom_codex_home(self):
        self.assertEqual(
            resolve_codex_config_path(
                Path("/home/example"),
                "/tmp/custom-codex-home",
            ),
            Path("/tmp/custom-codex-home/config.toml"),
        )

    def test_empty_codex_home_uses_default(self):
        self.assertEqual(
            resolve_codex_config_path(Path("/home/example"), ""),
            Path("/home/example/.codex/config.toml"),
        )


class TestConfigureCodexWithoutTomllib(unittest.TestCase):
    def test_missing_tomllib_leaves_existing_config_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = 'model = "example"\n'
            config_path.write_text(original)

            with (
                patch.dict(sys.modules, {"tomllib": None}),
                self.assertLogs(level="WARNING") as logs,
            ):
                configure_codex(config_path, dry_run=False)

            self.assertTrue(any("Python 3.11" in line for line in logs.output))
            self.assertEqual(config_path.read_text(), original)
            self.assertFalse(Path(str(config_path) + ".ORIGINAL").exists())


@unittest.skipUnless(TOMLLIB_AVAILABLE, "tomllib requires Python 3.11")
class TestConfigureCodex(unittest.TestCase):
    def test_creates_config_from_scratch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".codex" / "config.toml"

            configure_codex(config_path, dry_run=False)

            config = tomllib.loads(config_path.read_text())
            self.assertEqual(config["tui"]["status_line"], list(CODEX_STATUS_LINE))
            self.assertFalse(Path(str(config_path) + ".ORIGINAL").exists())

    def test_existing_config_is_backed_up_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = '# user comment\nmodel = "example"\n'
            config_path.write_text(original)

            configure_codex(config_path, dry_run=False)

            self.assertEqual(Path(str(config_path) + ".ORIGINAL").read_text(), original)
            config = tomllib.loads(config_path.read_text())
            self.assertEqual(config["model"], "example")
            self.assertEqual(config["tui"]["status_line"], list(CODEX_STATUS_LINE))

    def test_custom_status_line_is_not_rewritten_or_backed_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = '[tui]\nstatus_line = ["model"]\n'
            config_path.write_text(original)

            with patch("_pydotlib.bootstrap._write_config_text") as write:
                configure_codex(config_path, dry_run=False)

            write.assert_not_called()
            self.assertEqual(config_path.read_text(), original)
            self.assertFalse(Path(str(config_path) + ".ORIGINAL").exists())

    def test_malformed_config_is_untouched_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = "[tui\n"
            config_path.write_text(original)
            before_entries = {entry.name for entry in config_path.parent.iterdir()}

            configure_codex(config_path, dry_run=False)

            self.assertEqual(config_path.read_text(), original)
            self.assertEqual(
                {entry.name for entry in config_path.parent.iterdir()},
                before_entries,
            )

    def test_invalid_utf8_config_is_untouched_without_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = b"model = \xff\n"
            config_path.write_bytes(original)
            before_entries = {entry.name for entry in config_path.parent.iterdir()}

            with self.assertLogs(level="WARNING") as logs:
                configure_codex(config_path, dry_run=False)

            self.assertTrue(any("Could not read" in line for line in logs.output))
            self.assertEqual(config_path.read_bytes(), original)
            self.assertEqual(
                {entry.name for entry in config_path.parent.iterdir()},
                before_entries,
            )

    def test_dry_run_leaves_existing_tree_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            original = 'model = "example"\n'
            config_path.write_text(original)
            before = {entry.name: entry.read_bytes() for entry in config_path.parent.iterdir()}

            configure_codex(config_path, dry_run=True)

            after = {entry.name: entry.read_bytes() for entry in config_path.parent.iterdir()}
            self.assertEqual(after, before)

    def test_second_run_does_not_reach_writer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            configure_codex(config_path, dry_run=False)

            with patch("_pydotlib.bootstrap._write_config_text") as write:
                configure_codex(config_path, dry_run=False)

            write.assert_not_called()

    def test_symlinked_config_and_target_are_untouched(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "managed-elsewhere.toml"
            original = 'model = "example"\n'
            target.write_text(original)
            config_path = root / "config.toml"
            config_path.symlink_to(target)

            with self.assertLogs(level="WARNING") as logs:
                configure_codex(config_path, dry_run=False)

            self.assertTrue(any("symlink" in line for line in logs.output))
            self.assertTrue(config_path.is_symlink())
            self.assertEqual(target.read_text(), original)
            self.assertFalse(Path(str(config_path) + ".ORIGINAL").exists())


class TestConfigureClaudeCode(unittest.TestCase):
    @patch("_pydotlib.bootstrap._detect_real_editor", return_value="test-editor")
    def test_creates_settings_from_scratch(self, _detect_editor):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")
            self.assertEqual(settings["env"]["REAL_EDITOR"], "test-editor")
            self.assertEqual(settings["statusLine"], {"type": "command", "command": "claude-status"})

    def test_preserves_existing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(
                json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "mine.sh"}]}]}})
            )

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            # The pre-existing Stop hook survives alongside our merged-in one.
            stop_cmds = [
                h["command"]
                for g in settings["hooks"]["Stop"]
                for h in g["hooks"]
            ]
            self.assertIn("mine.sh", stop_cmds)
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")

    def test_preserves_existing_env_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(json.dumps({"env": {"FOO": "bar"}}))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["FOO"], "bar")
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")

    def test_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            # First run fully configures (editor, statusLine, hooks)...
            configure_claude_code(settings_path, dry_run=False)
            first = settings_path.read_text()

            # ...a second run must not even reach the filesystem writer.
            with patch("_pydotlib.bootstrap._write_config_text") as write:
                configure_claude_code(settings_path, dry_run=False)

            write.assert_not_called()
            self.assertEqual(settings_path.read_text(), first)

    def test_sets_statusline_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            real_editor = _detect_real_editor()
            existing = {"env": {"EDITOR": "claude-editor", "REAL_EDITOR": real_editor}}
            settings_path.write_text(json.dumps(existing))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["statusLine"], {"type": "command", "command": "claude-status"})

    def test_does_not_overwrite_existing_statusline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            existing = {"statusLine": {"type": "command", "command": "my_custom_status"}}
            settings_path.write_text(json.dumps(existing))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["statusLine"]["command"], "my_custom_status")

    def test_skips_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text("{invalid json")

            configure_claude_code(settings_path, dry_run=False)

            self.assertEqual(settings_path.read_text(), "{invalid json")

    def test_skips_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            original = b'{"value": "\xff"}'
            settings_path.write_bytes(original)
            before_entries = {entry.name for entry in settings_path.parent.iterdir()}

            with self.assertLogs(level="WARNING") as logs:
                configure_claude_code(settings_path, dry_run=False)

            self.assertTrue(any("Could not read or parse" in line for line in logs.output))
            self.assertEqual(settings_path.read_bytes(), original)
            self.assertEqual(
                {entry.name for entry in settings_path.parent.iterdir()},
                before_entries,
            )

    def test_skips_non_object_top_level(self):
        # Valid JSON whose top level isn't an object must be left untouched, not crash.
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text("[1, 2, 3]")

            configure_claude_code(settings_path, dry_run=False)

            self.assertEqual(settings_path.read_text(), "[1, 2, 3]")

    def test_null_hooks_does_not_crash(self):
        # "hooks": null is valid JSON but the wrong shape; merge is skipped, other
        # config still applies, and the run does not raise.
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(json.dumps({"hooks": None}))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            # statusLine/env still get configured; the malformed hooks is left as-is.
            self.assertEqual(settings["statusLine"], {"type": "command", "command": "claude-status"})
            self.assertIsNone(settings["hooks"])

    def test_non_list_hook_event_is_skipped(self):
        # An event whose value isn't a list must be skipped, not crash; other
        # events still get their hooks merged.
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings_path.write_text(json.dumps({"hooks": {"Stop": "bogus"}}))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["hooks"]["Stop"], "bogus")  # left untouched
            # a different event still got its tmux hook merged
            self.assertIn("SessionStart", settings["hooks"])

    def test_backs_up_existing_settings_once(self):
        # First modification of an existing file captures the pre-dotfiles
        # original as <name>.ORIGINAL; later modifications never overwrite it.
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            original = json.dumps({"env": {"FOO": "bar"}})
            settings_path.write_text(original)
            backup = Path(str(settings_path) + ".ORIGINAL")

            configure_claude_code(settings_path, dry_run=False)
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(), original)

            # Clobber the live file and re-run: the one-time backup is preserved.
            settings_path.write_text(json.dumps({"env": {"FOO": "changed"}}))
            configure_claude_code(settings_path, dry_run=False)
            self.assertEqual(backup.read_text(), original)

    def test_no_backup_for_new_settings_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=False)

            self.assertTrue(settings_path.exists())
            self.assertFalse(Path(str(settings_path) + ".ORIGINAL").exists())

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=True)

            self.assertFalse(settings_path.exists())

    def test_dry_run_does_not_write_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            real_editor = _detect_real_editor()
            existing = {"env": {"EDITOR": "claude-editor", "REAL_EDITOR": real_editor}}
            settings_path.write_text(json.dumps(existing))
            before = {entry.name: entry.read_bytes() for entry in settings_path.parent.iterdir()}

            configure_claude_code(settings_path, dry_run=True)

            after = {entry.name: entry.read_bytes() for entry in settings_path.parent.iterdir()}
            self.assertEqual(after, before)

    @patch("shutil.which", return_value=None)
    @patch.dict(os.environ, {"EDITOR": "nano"})
    def test_writes_real_editor_from_env_when_no_vim(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["REAL_EDITOR"], "nano")


class TestMergeClaudeTmuxHooks(unittest.TestCase):
    def test_merges_all_specs_into_empty(self):
        settings: dict = {}
        changed = _merge_claude_tmux_hooks(settings)
        self.assertTrue(changed)
        commands = [
            h["command"]
            for groups in settings["hooks"].values()
            for g in groups
            for h in g["hooks"]
        ]
        self.assertEqual(len(commands), len(CLAUDE_TMUX_STATE_HOOKS))
        for spec in CLAUDE_TMUX_STATE_HOOKS:
            self.assertIn(spec.command, commands)

    def test_second_merge_is_noop(self):
        settings: dict = {}
        _merge_claude_tmux_hooks(settings)
        self.assertFalse(_merge_claude_tmux_hooks(settings))

    def test_preserves_unrelated_hooks(self):
        settings = {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "other.sh"}]}],
                "PostToolUse": [
                    {
                        "matcher": "Edit",
                        "hooks": [{"type": "command", "command": "fmt.sh"}],
                    }
                ],
            }
        }
        _merge_claude_tmux_hooks(settings)
        stop_cmds = [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("other.sh", stop_cmds)
        post_cmds = [
            h["command"] for g in settings["hooks"]["PostToolUse"] for h in g["hooks"]
        ]
        self.assertIn("fmt.sh", post_cmds)

    def test_notification_gets_only_permission_matcher_group(self):
        # idle_prompt no longer maps to a state; permission_prompt is the lone
        # Notification matcher left.
        settings: dict = {}
        _merge_claude_tmux_hooks(settings)
        matchers = {g.get("matcher") for g in settings["hooks"]["Notification"]}
        self.assertEqual(matchers, {"permission_prompt"})

    def test_ask_user_question_drives_needs_input(self):
        # needs-input is driven by the AskUserQuestion tool, not idle_prompt:
        # PreToolUse sets it and PostToolUse clears it back to busy.
        settings: dict = {}
        _merge_claude_tmux_hooks(settings)

        def cmds(event, matcher):
            return [
                h["command"]
                for g in settings["hooks"][event]
                if (g.get("matcher") or "") == matcher
                for h in g["hooks"]
            ]

        self.assertTrue(
            any(c.endswith("needs-input") for c in cmds("PreToolUse", "AskUserQuestion"))
        )
        self.assertTrue(
            any(c.endswith("busy") for c in cmds("PostToolUse", "AskUserQuestion"))
        )
        notif_matchers = {g.get("matcher") for g in settings["hooks"]["Notification"]}
        self.assertNotIn("idle_prompt", notif_matchers)

    def test_matcherless_events_omit_matcher_key(self):
        settings: dict = {}
        _merge_claude_tmux_hooks(settings)
        for group in settings["hooks"]["Stop"]:
            self.assertNotIn("matcher", group)

    def test_updates_changed_command_in_place(self):
        settings = {
            "hooks": {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"old/{CLAUDE_TMUX_STATE_MARKER} idle",
                            }
                        ]
                    }
                ]
            }
        }
        changed = _merge_claude_tmux_hooks(settings)
        self.assertTrue(changed)
        marker_cmds = [
            h["command"]
            for g in settings["hooks"]["Stop"]
            for h in g["hooks"]
            if CLAUDE_TMUX_STATE_MARKER in h["command"]
        ]
        self.assertEqual(len(marker_cmds), 1)
        self.assertTrue(marker_cmds[0].startswith("~/.dotfiles/bin/"))

    def test_prunes_orphaned_marker_hook(self):
        # An existing install with a now-removed mapping (the old
        # idle_prompt -> needs-input) must have that marker hook pruned on
        # re-merge, leaving no stale producer behind, then settle to a no-op.
        settings = {
            "hooks": {
                "Notification": [
                    {
                        "matcher": "idle_prompt",
                        "hooks": [
                            {
                                "type": "command",
                                "command": f"old/{CLAUDE_TMUX_STATE_MARKER} needs-input",
                            }
                        ],
                    }
                ]
            }
        }
        changed = _merge_claude_tmux_hooks(settings)
        self.assertTrue(changed)
        notif_matchers = {g.get("matcher") for g in settings["hooks"]["Notification"]}
        self.assertNotIn("idle_prompt", notif_matchers)
        self.assertFalse(_merge_claude_tmux_hooks(settings))

    def test_prune_keeps_foreign_hook_in_orphaned_group(self):
        # Only the marker hook is pruned from an orphaned (event, matcher); a
        # foreign hook sharing that group is preserved.
        settings = {
            "hooks": {
                "Notification": [
                    {
                        "matcher": "idle_prompt",
                        "hooks": [
                            {"type": "command", "command": "foreign.sh"},
                            {
                                "type": "command",
                                "command": f"old/{CLAUDE_TMUX_STATE_MARKER} needs-input",
                            },
                        ],
                    }
                ]
            }
        }
        _merge_claude_tmux_hooks(settings)
        idle_groups = [
            g
            for g in settings["hooks"]["Notification"]
            if g.get("matcher") == "idle_prompt"
        ]
        self.assertEqual(len(idle_groups), 1)
        self.assertEqual(
            [h["command"] for h in idle_groups[0]["hooks"]], ["foreign.sh"]
        )

    def test_full_upgrade_from_old_install_reconciles(self):
        # Headline path: a complete pre-change install (idle_prompt -> needs-input,
        # no AskUserQuestion groups) re-merges to BOTH add the AskUserQuestion
        # groups and prune idle_prompt in one pass, then settles to a no-op.
        def cmd(state):
            return {"hooks": [{"type": "command", "command": f"{_CTS} {state}"}]}

        def cmd_m(matcher, state):
            group = cmd(state)
            group["matcher"] = matcher
            return group

        settings = {
            "hooks": {
                "SessionStart": [cmd_m("startup", "present")],
                "UserPromptSubmit": [cmd("busy")],
                "PreToolUse": [cmd_m("Bash", "running")],
                "PostToolUse": [cmd_m("Bash", "busy")],
                "Notification": [
                    cmd_m("idle_prompt", "needs-input"),
                    cmd_m("permission_prompt", "needs-perm"),
                ],
                "Stop": [cmd("idle")],
                "StopFailure": [cmd("idle")],
                "SessionEnd": [cmd("clear")],
            }
        }
        self.assertTrue(_merge_claude_tmux_hooks(settings))

        def matchers(event):
            return {g.get("matcher") for g in settings["hooks"][event]}

        self.assertEqual(matchers("Notification"), {"permission_prompt"})
        self.assertEqual(matchers("PreToolUse"), {"Bash", "AskUserQuestion"})
        self.assertEqual(matchers("PostToolUse"), {"Bash", "AskUserQuestion"})
        self.assertFalse(_merge_claude_tmux_hooks(settings))

    def test_coexists_with_foreign_same_matcher_group_without_dupe(self):
        settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "audit.sh"}],
                    }
                ]
            }
        }
        _merge_claude_tmux_hooks(settings)
        _merge_claude_tmux_hooks(settings)
        bash_marker_cmds = [
            h["command"]
            for g in settings["hooks"]["PreToolUse"]
            if (g.get("matcher") or "") == "Bash"
            for h in g["hooks"]
            if CLAUDE_TMUX_STATE_MARKER in h["command"]
        ]
        self.assertEqual(len(bash_marker_cmds), 1)
        all_cmds = [
            h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]
        ]
        self.assertIn("audit.sh", all_cmds)


class TestConfigureWeatherLocation(unittest.TestCase):
    def test_writes_file_when_location_arg_provided(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dotfiles" / "weather_location"
            configure_weather_location(path, location="Seattle", dry_run=False)
            self.assertEqual(path.read_text(), "Seattle\n")

    @patch("_pydotlib.bootstrap.input_field", return_value="Portland")
    def test_writes_file_when_user_enters_value(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            configure_weather_location(path, dry_run=False)
            self.assertEqual(path.read_text(), "Portland\n")

    @patch("_pydotlib.bootstrap.input_field")
    def test_preserves_existing_value_when_input_blank(self, mock_input):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            path.write_text("Redmond\n")
            mtime_before = path.stat().st_mtime

            # input_field returns the default when input is blank — simulate that
            # by returning whatever default was passed.
            mock_input.side_effect = lambda message, default=None: default

            configure_weather_location(path, dry_run=False)

            self.assertEqual(path.read_text(), "Redmond\n")
            self.assertEqual(path.stat().st_mtime, mtime_before)

    @patch("_pydotlib.bootstrap.input_field", return_value=None)
    def test_skips_write_when_no_value_and_no_existing(self, _):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            configure_weather_location(path, dry_run=False)
            self.assertFalse(path.exists())

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dotfiles" / "weather_location"
            configure_weather_location(path, location="Seattle", dry_run=True)
            self.assertFalse(path.exists())

    @patch("_pydotlib.bootstrap.input_field")
    @patch.dict(os.environ, {"WEATHER_LOCATION": "FromEnv"}, clear=False)
    def test_falls_back_to_env_var_when_no_file(self, mock_input):
        captured = {}

        def capture_default(message, default=None):
            captured["default"] = default
            return default

        mock_input.side_effect = capture_default

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            configure_weather_location(path, dry_run=False)

            self.assertEqual(captured["default"], "FromEnv")
            self.assertEqual(path.read_text(), "FromEnv\n")

    def test_no_rewrite_when_arg_matches_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            path.write_text("Seattle\n")
            mtime_before = path.stat().st_mtime

            configure_weather_location(path, location="Seattle", dry_run=False)

            self.assertEqual(path.read_text(), "Seattle\n")
            self.assertEqual(path.stat().st_mtime, mtime_before)

    def test_empty_location_arg_skips_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            configure_weather_location(path, location="", dry_run=False)
            self.assertFalse(path.exists())

    def test_dry_run_does_not_modify_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "weather_location"
            path.write_text("Redmond\n")
            mtime_before = path.stat().st_mtime

            configure_weather_location(path, location="Seattle", dry_run=True)

            self.assertEqual(path.read_text(), "Redmond\n")
            self.assertEqual(path.stat().st_mtime, mtime_before)


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
