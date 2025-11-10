import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch


def get_repo_root(path: Path) -> Path | None:
    """
    Get the root directory of a git checkout for the provided path.

    :param path: A path inside a git checkout.
    :return: The root directory for the git checkout.
    """
    # Use the git command to find the top level directory for the repo.
    try:
        git_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
        )
    except CalledProcessError as e:
        if e.stderr.startswith("fatal: not a git repository"):
            return None

        raise

    # Read the directory from stdout, and verify that it's a valid directory before returning.
    root_dir = Path(git_result.stdout.strip()).resolve()

    return root_dir


def read_git_config(config_text: str, keys: list[str]) -> dict[str, str]:
    matched_keys: dict[str, str] = {}
    section: str | None = None

    for line in config_text.splitlines():
        if match := re.match(r"^\s*\[(.+)]\s*$", line):
            section = match[1]

        if match := re.match(r"^\s*(\w+)\s*=\s*(.*)\s*$", line):
            raw_key = match[1].strip()
            git_key = f"{section}:{raw_key}" if section else raw_key
            git_value = match[2].strip()

            for key in keys:
                if key == git_key:
                    matched_keys[git_key] = git_value

    return matched_keys


def update_git_config(config_text: str, keys: dict[str, str]) -> str:
    new_lines: list[str] = []
    section: str | None = None

    for line in config_text.splitlines():
        replaced = False

        if match := re.match(r"^\s*\[(.+)]\s*$", line):
            section = match[1]

        if match := re.match(r"^(\s*)(\w+)\s*=.*$", line):
            key_padding = match[1]
            raw_key = match[2].strip()
            git_key = f"{section}:{raw_key}" if section else raw_key

            for key in keys:
                if key == git_key:
                    new_lines.append(
                        f"{key_padding}{raw_key} = {keys[key] if keys[key] is not None else ''}"
                    )
                    replaced = True

        if not replaced:
            new_lines.append(line)

    return os.linesep.join(new_lines)


def read_git_config_file(path: Path, keys: list[str]) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        return read_git_config(f.read(), keys)


def update_git_config_file(path: Path, keys: dict[str, str]) -> None:
    # Generate an updated configuration and write it to a temporary file.
    with open(path, encoding="utf-8") as f:
        updated_config = update_git_config(f.read(), keys)

    temp_dir = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=temp_dir) as temp_file:
        temp_filepath = temp_file.name
        temp_file.write(updated_config)

    # Replace the old config file with the new one.
    try:
        os.replace(temp_filepath, path)
    except Exception as e:
        os.remove(temp_filepath)
        raise e


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
        mock_result = MagicMock()
        mock_result.stdout = "/home/user/repo\n"
        mock_run.return_value = mock_result

        result = get_repo_root(Path("/home/user/repo/subdir"))

        self.assertEqual(result, Path("/home/user/repo").resolve())
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_returns_none_for_non_git_directory(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=["git", "rev-parse", "--show-toplevel"],
            stderr="fatal: not a git repository",
        )

        result = get_repo_root(Path("/home/user/notrepo"))


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