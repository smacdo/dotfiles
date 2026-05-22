"""Post-bootstrap integration checks that run inside a test container.

Each check is a pure function `(exec_fn: ExecFn) -> CheckResult`, where
`exec_fn` is a closure the runner provides that runs a shell command
inside a specific container (e.g. `podman exec <name> <cmd...>`).

IMPORTANT: This module must NOT import from `_pydotlib.bootstrap` or any
other module under test. It only observes container state via the
provided `exec_fn` plus stdlib types.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


ExecFn = Callable[[list[str]], subprocess.CompletedProcess]
Check = Callable[[ExecFn], CheckResult]


def check_symlink(target: str, expected_link: str) -> Check:
    name = f"symlink {target} -> {expected_link}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        is_link = exec_fn(["test", "-L", target])
        if is_link.returncode != 0:
            return CheckResult(name, False, f"{target} is not a symlink")

        readlink = exec_fn(["readlink", target])
        if readlink.returncode != 0:
            return CheckResult(
                name, False, f"readlink {target} failed: {readlink.stderr.strip()}"
            )

        actual = readlink.stdout.strip()
        if actual != expected_link:
            return CheckResult(
                name, False, f"{target} -> {actual!r}, expected {expected_link!r}"
            )
        return CheckResult(name, True)

    return _run


def check_dir_exists(path: str) -> Check:
    name = f"dir exists: {path}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        result = exec_fn(["test", "-d", path])
        if result.returncode != 0:
            return CheckResult(name, False, f"{path} is not a directory")
        return CheckResult(name, True)

    return _run


def check_file_contains(path: str, expected: str) -> Check:
    name = f"{path} contains {expected!r}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        is_file = exec_fn(["test", "-f", path])
        if is_file.returncode != 0:
            return CheckResult(name, False, f"{path} is not a regular file")

        cat = exec_fn(["cat", path])
        if cat.returncode != 0:
            return CheckResult(
                name, False, f"cat {path} failed: {cat.stderr.strip()}"
            )

        if expected not in cat.stdout:
            return CheckResult(
                name, False, f"{path} does not contain {expected!r}"
            )
        return CheckResult(name, True)

    return _run


# `/home/testuser` is the container user's home — set by every Dockerfile's
# `useradd -m testuser` and matched by the runner's bind mount of the repo at
# `/home/testuser/.dotfiles`. Keep these three in sync (see CLAUDE.md
# "Integration test policy").
_HOME = "/home/testuser"
_DOTFILES = f"{_HOME}/.dotfiles"

BOOTSTRAP_CHECKS: list[Check] = [
    check_symlink(f"{_HOME}/.bashrc", f"{_DOTFILES}/.bashrc"),
    check_symlink(f"{_HOME}/.bash_profile", f"{_DOTFILES}/.bash_profile"),
    check_symlink(f"{_HOME}/.gitconfig", f"{_DOTFILES}/.gitconfig"),
    check_symlink(f"{_HOME}/.tmux.conf", f"{_DOTFILES}/.tmux.conf"),
    check_symlink(f"{_HOME}/.vimrc", f"{_DOTFILES}/settings/nvim/init.vim"),
    check_symlink(f"{_HOME}/.vim", f"{_DOTFILES}/.vim"),
    check_dir_exists(f"{_HOME}/.local/state/vim/backups"),
    check_dir_exists(f"{_HOME}/.local/state/vim/tmp"),
    check_file_contains(f"{_HOME}/.my_gitconfig", "Testy McTestFace"),
    check_file_contains(f"{_HOME}/.my_gitconfig", "testy@test.com"),
]
