import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from _pydotlib.git import (
    get_repo_root,
    read_git_config,
    read_git_config_file,
    update_git_config,
    update_git_config_file,
)


class GitConfigTests(unittest.TestCase):
    CONFIG_TEXT = """
# my_key = incorrect_value
foo = bar
foobar =
blank =    
[hello]
my_key = correct_value
ignored = hello world
    indented_key = foobar"""

    def test_read_git_config(self):
        keys = read_git_config(
            GitConfigTests.CONFIG_TEXT,
            ["foo", "foobar", "blank", "hello:my_key", "hello:indented_key"],
        )

        self.assertEqual(len(keys), 5)
        self.assertEqual(keys["foo"], "bar")
        self.assertEqual(keys["foobar"], "")
        self.assertEqual(keys["blank"], "")
        self.assertEqual(keys["hello:my_key"], "correct_value")
        self.assertEqual(keys["hello:indented_key"], "foobar")

    def test_handles_nonexistent_keys(self):
        keys = read_git_config(
            GitConfigTests.CONFIG_TEXT,
            ["foo", "does_not_exist"],
        )

        self.assertEqual(len(keys), 1)
        self.assertEqual(keys["foo"], "bar")
        self.assertTrue("does_not_exist" not in keys)

    def test_update_git_config(self):
        updated_config = update_git_config(
            GitConfigTests.CONFIG_TEXT,
            {
                "foobar": "barfoo",
                "hello:my_key": "updated_value",
                "hello:indented_key": "hello!",
            },
        )

        self.assertEqual(
            updated_config,
            """
# my_key = incorrect_value
foo = bar
foobar = barfoo
blank =    
[hello]
my_key = updated_value
ignored = hello world
    indented_key = hello!""",
        )

    def test_update_drops_none_values(self):
        updated_config = update_git_config(
            GitConfigTests.CONFIG_TEXT,
            {
                "foobar": None,
                "hello:my_key": None,
                "hello:indented_key": "hello!",
            },
        )

        self.assertEqual(
            updated_config,
            """
# my_key = incorrect_value
foo = bar
foobar = 
blank =    
[hello]
my_key = 
ignored = hello world
    indented_key = hello!""",
        )


class TestGetRepoRoot(unittest.TestCase):
    @patch("subprocess.run")
    def test_returns_repo_root_path(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="/home/user/repo\n")

        result = get_repo_root(Path("/home/user/repo/subdir"))

        self.assertEqual(result, Path("/home/user/repo").resolve())
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_returns_none_for_non_git_directory(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: not a git repository (or any of the parent directories): .git\n",
        )

        result = get_repo_root(Path("/home/user/notrepo"))

        self.assertIsNone(result)

    @patch("subprocess.run", side_effect=FileNotFoundError("git"))
    def test_raises_when_git_not_installed(self, mock_run):
        with self.assertRaises(RuntimeError) as cm:
            get_repo_root(Path("/home/user/anywhere"))
        self.assertIn("git", str(cm.exception).lower())

    @patch("subprocess.run")
    def test_raises_for_other_git_failures(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=2,
            stderr="fatal: bad revision 'HEAD'\n",
        )

        with self.assertRaises(RuntimeError) as cm:
            get_repo_root(Path("/home/user/repo"))
        self.assertIn("exit 2", str(cm.exception))


class TestReadGitConfigFile(unittest.TestCase):
    def test_reads_config_from_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".gitconfig"
        ) as f:
            f.write("[user]\n")
            f.write("name = Test User\n")
            f.write("email = test@example.com\n")
            f.flush()

            config_path = Path(f.name)

            try:
                result = read_git_config_file(config_path, ["user:name", "user:email"])

                self.assertEqual(result["user:name"], "Test User")
                self.assertEqual(result["user:email"], "test@example.com")
            finally:
                config_path.unlink()


class TestUpdateGitConfigFile(unittest.TestCase):
    def test_updates_config_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".gitconfig"
        ) as f:
            f.write("[user]\n")
            f.write("name = Old Name\n")
            f.write("email = old@example.com\n")
            f.flush()

            config_path = Path(f.name)

            try:
                update_git_config_file(
                    config_path,
                    {"user:name": "New Name", "user:email": "new@example.com"},
                )

                content = config_path.read_text()

                self.assertIn("New Name", content)
                self.assertIn("new@example.com", content)
                self.assertNotIn("Old Name", content)
                self.assertNotIn("old@example.com", content)
            finally:
                config_path.unlink()
