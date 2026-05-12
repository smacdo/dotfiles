import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from _pydotlib.bootstrap import (
    _detect_real_editor,
    configure_claude_code,
    configure_vcs_author,
    configure_weather_location,
    create_backup_filename,
    git_clone,
    git_clone_repos,
    is_dotfiles_root,
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


class TestConfigureVcsAuthor(unittest.TestCase):
    def test_adds_missing_email_when_arg_provided(self):
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


class TestConfigureClaudeCode(unittest.TestCase):
    def test_creates_settings_from_scratch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / ".claude" / "settings.json"
            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["env"]["EDITOR"], "claude-editor")
            self.assertIn(settings["env"]["REAL_EDITOR"], ("nvim", "vim", "vi"))
            self.assertEqual(settings["statusLine"], {"type": "command", "command": "claude_status"})

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
            existing = {
                "env": {"EDITOR": "claude-editor", "REAL_EDITOR": real_editor},
                "statusLine": {"type": "command", "command": "claude_status"},
            }
            settings_path.write_text(json.dumps(existing))
            mtime_before = settings_path.stat().st_mtime

            configure_claude_code(settings_path, dry_run=False)

            mtime_after = settings_path.stat().st_mtime
            self.assertEqual(mtime_before, mtime_after)

    def test_sets_statusline_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            real_editor = _detect_real_editor()
            existing = {"env": {"EDITOR": "claude-editor", "REAL_EDITOR": real_editor}}
            settings_path.write_text(json.dumps(existing))

            configure_claude_code(settings_path, dry_run=False)

            settings = json.loads(settings_path.read_text())
            self.assertEqual(settings["statusLine"], {"type": "command", "command": "claude_status"})

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
            mtime_before = settings_path.stat().st_mtime

            configure_claude_code(settings_path, dry_run=True)

            mtime_after = settings_path.stat().st_mtime
            self.assertEqual(mtime_before, mtime_after)


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
