import os
import re
import subprocess
import tempfile
from collections.abc import Mapping
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
    """Extract specific keys from a gitconfig-format string.

    `keys` are written as `section:name` for sectioned values (e.g.
    `user:email`) or just `name` for top-level values.  Returns a dict
    mapping each *found* key to its value; missing keys are simply omitted.
    """
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


def update_git_config(config_text: str, keys: Mapping[str, str | None]) -> str:
    """Apply key→value updates to a gitconfig-format string and return the result.

    Keys present in the input are replaced in place, preserving their original
    indentation.  Keys *not* present are appended at the end, grouped by
    section — git tolerates duplicate section headers (merges them) so we
    don't splice into existing sections.  A `None` value writes an empty
    value (i.e. `key = `), which git treats as "unset for boolean keys" /
    empty string elsewhere.

    Output is LF-only and ends with exactly one newline.
    """
    new_lines: list[str] = []
    section: str | None = None
    matched: set[str] = set()

    for line in config_text.splitlines():
        replaced = False

        if match := re.match(r"^\s*\[(.+)]\s*$", line):
            section = match[1]

        if match := re.match(r"^(\s*)(\w+)\s*=.*$", line):
            key_padding = match[1]
            raw_key = match[2].strip()
            git_key = f"{section}:{raw_key}" if section else raw_key

            if git_key in keys:
                new_lines.append(
                    f"{key_padding}{raw_key} = {keys[git_key] if keys[git_key] is not None else ''}"
                )
                matched.add(git_key)
                replaced = True

        if not replaced:
            new_lines.append(line)

    # Append requested-but-missing keys, grouped by section. Git tolerates
    # duplicate section headers (it merges them), so we don't need to splice
    # into existing sections.
    unmatched: dict[str | None, list[tuple[str, str | None]]] = {}
    for git_key, value in keys.items():
        if git_key in matched:
            continue
        sec, sep, raw_key = git_key.rpartition(":")
        unmatched.setdefault(sec if sep else None, []).append((raw_key, value))

    for sec, kvs in unmatched.items():
        if sec is not None:
            new_lines.append(f"[{sec}]")
        for raw_key, value in kvs:
            new_lines.append(f"\t{raw_key} = {value if value is not None else ''}")

    # Git config files are LF-only and POSIX text files end with a newline.
    return "\n".join(new_lines) + "\n"


def read_git_config_file(path: Path, keys: list[str]) -> dict[str, str]:
    """File-backed wrapper around `read_git_config`."""
    with open(path, encoding="utf-8") as f:
        return read_git_config(f.read(), keys)


def update_git_config_file(path: Path, keys: Mapping[str, str | None]) -> None:
    """Apply `update_git_config` to the file at `path`, atomically.

    Writes the result to a temporary file in the same directory, then
    `os.replace`s it over the original.  On failure the temporary file is
    best-effort cleaned up without masking the original exception.
    """
    # Generate an updated configuration and write it to a temporary file.
    with open(path, encoding="utf-8") as f:
        updated_config = update_git_config(f.read(), keys)

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, dir=os.path.dirname(path), encoding="utf-8"
    ) as temp_file:
        temp_filepath = temp_file.name
        temp_file.write(updated_config)

    try:
        os.replace(temp_filepath, path)
    except BaseException:
        # Best-effort cleanup; suppress so the original exception isn't masked.
        try:
            os.remove(temp_filepath)
        except OSError:
            pass
        raise
