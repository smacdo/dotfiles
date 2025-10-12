import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


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
    def test_read_git_config(self):
        config_text = """
# my_key = incorrect_value
foo = bar
foobar =
blank =    
[hello]
my_key = correct_value
ignored = hello world
    indented_key = foobar
        """

        keys = read_git_config(
            config_text,
            ["foo", "foobar", "blank", "hello:my_key", "hello:indented_key"],
        )

        self.assertEqual(len(keys), 5)
        self.assertEqual(keys["foo"], "bar")
        self.assertEqual(keys["foobar"], "")
        self.assertEqual(keys["blank"], "")
        self.assertEqual(keys["hello:my_key"], "correct_value")
        self.assertEqual(keys["hello:indented_key"], "foobar")

    def test_update_git_config(self):
        config_text = """
# my_key = incorrect_value
foo = bar
foobar =
blank =    
[hello]
my_key = correct_value
ignored = hello world
    indented_key = foobar"""

        updated_config = update_git_config(
            config_text,
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