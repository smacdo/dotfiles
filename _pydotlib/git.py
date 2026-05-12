import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def get_repo_root(path: Path) -> Path | None:
    """
    Get the root directory of a git checkout for the provided path.

    :param path: A path inside a git checkout.
    :return: The root directory for the git checkout, or None if `path` is not
        inside one.
    :raises RuntimeError: if `git` is not installed, or if `git rev-parse`
        fails for a reason other than "not a git repository".
    """
    try:
        git_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("`git` is not installed or not on PATH") from e

    if git_result.returncode != 0:
        if "not a git repository" in git_result.stderr:
            return None
        raise RuntimeError(
            f"git rev-parse failed (exit {git_result.returncode}): "
            f"{git_result.stderr.strip()}"
        )

    return Path(git_result.stdout.strip()).resolve()


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
