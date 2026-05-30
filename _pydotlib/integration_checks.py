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


def check_file_not_exists(path: str) -> Check:
    """Inverse of file/dir-existence checks. Useful for dry-run assertions."""
    name = f"path does not exist: {path}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        result = exec_fn(["test", "-e", path])
        if result.returncode == 0:
            return CheckResult(name, False, f"{path} exists but should not")
        return CheckResult(name, True)

    return _run


def check_dir_non_empty(path: str) -> Check:
    """Pass if `path` is a directory containing at least one entry. Stronger
    than `check_dir_exists` for cases where the directory must have been
    populated (e.g. `:PlugInstall` actually installed plugins)."""
    name = f"dir non-empty: {path}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        is_dir = exec_fn(["test", "-d", path])
        if is_dir.returncode != 0:
            return CheckResult(name, False, f"{path} is not a directory")

        # `find -mindepth 1 -maxdepth 1` lists immediate children (including
        # hidden) without shell quoting concerns.
        result = exec_fn(["find", path, "-mindepth", "1", "-maxdepth", "1"])
        if result.returncode != 0:
            return CheckResult(name, False, f"find {path} failed: {result.stderr.strip()}")
        if not result.stdout.strip():
            return CheckResult(name, False, f"{path} exists but is empty")
        return CheckResult(name, True)

    return _run


def check_command_succeeds(cmd: list[str]) -> Check:
    """Pass if `cmd` exits 0; fail otherwise. Use for `zsh -c 'source ~/.zshrc'`,
    `nvim --headless -c 'q'`, etc. — checks "does it load/run cleanly" without
    asserting on output."""
    name = f"`{' '.join(cmd)}` succeeds"

    def _run(exec_fn: ExecFn) -> CheckResult:
        result = exec_fn(cmd)
        if result.returncode != 0:
            return CheckResult(
                name,
                False,
                f"exit {result.returncode}: {result.stderr.strip()}",
            )
        return CheckResult(name, True)

    return _run


def check_command_silent(cmd: list[str]) -> Check:
    """Stricter variant of `check_command_succeeds`: also fails if anything is
    written to stdout or stderr. Use for init checks where any output is itself
    a bug (e.g. shell login should be silent)."""
    name = f"`{' '.join(cmd)}` succeeds silently"

    def _run(exec_fn: ExecFn) -> CheckResult:
        result = exec_fn(cmd)
        if result.returncode != 0:
            return CheckResult(
                name,
                False,
                f"exit {result.returncode}: {result.stderr.strip()}",
            )
        if result.stdout:
            return CheckResult(name, False, f"unexpected stdout: {result.stdout!r}")
        if result.stderr:
            return CheckResult(name, False, f"unexpected stderr: {result.stderr!r}")
        return CheckResult(name, True)

    return _run


def check_command_output_matches(cmd: list[str], expected_substring: str) -> Check:
    name = f"`{' '.join(cmd)}` output contains {expected_substring!r}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        result = exec_fn(cmd)
        if result.returncode != 0:
            return CheckResult(
                name,
                False,
                f"exit {result.returncode}: {result.stderr.strip()}",
            )
        if expected_substring not in result.stdout:
            return CheckResult(
                name,
                False,
                f"stdout did not contain {expected_substring!r}; got: {result.stdout!r}",
            )
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


def check_tmux_config(conf_path: str, socket: str = "dotfiles_ci_test") -> Check:
    """Pass if tmux loads `conf_path` without error.

    Loads the config via an explicit `source-file` against a detached server on
    a private `-L` socket. This matters two ways: `-L` never touches the user's
    real (default-socket) server, and `source-file` surfaces config errors that
    `tmux -f conf` at startup silently swallows (no attached client → errors
    discarded). Catches renamed/removed options across tmux versions, unknown
    commands, bad args/values, and missing `run-shell` binaries. Does NOT catch
    unterminated quotes or unmatched `#{` format braces — tmux validates formats
    lazily at render. See TODO.md for the gaps and helper-script coverage.
    """
    name = f"tmux loads {conf_path}"

    def _run(exec_fn: ExecFn) -> CheckResult:
        # Start with an empty config (`-f /dev/null`) so `source-file` is the
        # sole, error-surfacing load.
        start = exec_fn(
            ["tmux", "-L", socket, "-f", "/dev/null", "new-session", "-d", "-s", "probe"]
        )
        if start.returncode != 0:
            return CheckResult(
                name, False, f"tmux server failed to start: {start.stderr.strip()}"
            )

        try:
            res = exec_fn(["tmux", "-L", socket, "source-file", conf_path])
        finally:
            exec_fn(["tmux", "-L", socket, "kill-server"])

        if res.returncode != 0:
            return CheckResult(
                name,
                False,
                f"source-file exit {res.returncode}: {res.stderr.strip()}",
            )
        return CheckResult(name, True)

    return _run


# `/home/testuser` is the container user's home — set by every Dockerfile's
# `useradd -m testuser` and matched by the runner's bind mount of the repo at
# `/home/testuser/.dotfiles`. Keep these three in sync (see CLAUDE.md
# "Integration test policy").
_HOME = "/home/testuser"
_DOTFILES = f"{_HOME}/.dotfiles"

_XDG_DATA = f"{_HOME}/.local/share"

# Pre-bootstrap sentinel content the runner writes to ~/.bashrc before invoking
# bootstrap. After bootstrap, this content must appear in ~/.bashrc.ORIGINAL —
# the file safe_symlink() backs up before replacing. Anchors the "bootstrap
# never destroys user data" check below.
BACKUP_SENTINEL = "SENTINEL_BACKUP_TEST_PRE_BOOTSTRAP"


def build_native_checks(home: str, dotfiles: str, *, platform: str) -> list[Check]:
    """Build a check list for native (non-container) host testing.

    Unlike BOOTSTRAP_CHECKS, this list is parameterized by paths and uses
    structural assertions (e.g. "git config user.name exits 0") rather than
    value assertions (e.g. "git config user.name contains Testy McTestFace").
    This lets the same check list work for both CI (fresh bootstrap with test
    values) and local (user's real values).
    """
    xdg_data = f"{home}/.local/share"
    xdg_state = f"{home}/.local/state"

    checks: list[Check] = [
        check_symlink(f"{home}/.bashrc", f"{dotfiles}/.bashrc"),
        check_symlink(f"{home}/.bash_profile", f"{dotfiles}/.bash_profile"),
        check_symlink(f"{home}/.gitconfig", f"{dotfiles}/.gitconfig"),
        check_symlink(f"{home}/.tmux.conf", f"{dotfiles}/.tmux.conf"),
        check_symlink(f"{home}/.vimrc", f"{dotfiles}/settings/nvim/init.vim"),
        check_symlink(f"{home}/.vim", f"{dotfiles}/.vim"),
        check_dir_exists(f"{xdg_state}/vim/backups"),
        check_dir_exists(f"{xdg_state}/vim/tmp"),
        check_command_succeeds(["git", "config", "user.name"]),
        check_command_succeeds(["git", "config", "user.email"]),
        check_command_silent(
            ["env", "DOTFILE_CI_TEST_MODE=1", "bash", "-lc", "true"]
        ),
        check_file_contains(
            f"{xdg_data}/vim/site/autoload/plug.vim", "plug#begin"
        ),
        check_file_contains(
            f"{xdg_data}/nvim/site/autoload/plug.vim", "plug#begin"
        ),
        check_dir_exists(f"{xdg_data}/powerlevel10k/.git"),
        check_command_succeeds(["vim", "-e", "-s", "-c", "q"]),
        check_command_succeeds(["nvim", "--headless", "-c", "q"]),
        check_tmux_config(f"{home}/.tmux.conf"),
    ]

    if platform == "darwin":
        checks.extend([
            # DOTFILE_CI_TEST_MODE=1 bypasses .bashrc's non-interactive early
            # return so detect_os() actually runs (it's sourced after the guard;
            # .bash_profile doesn't load functions.sh). `env -u` clears any
            # inherited DOT_OS/DOT_DIST so the check passes only if detect_os set
            # them — otherwise an ambient value from the caller's shell masks a
            # broken detection.
            check_command_output_matches(
                ["env", "-u", "DOT_OS", "DOTFILE_CI_TEST_MODE=1",
                 "bash", "-lc", "echo $DOT_OS"],
                "macos",
            ),
            check_command_output_matches(
                ["env", "-u", "DOT_DIST", "DOTFILE_CI_TEST_MODE=1",
                 "bash", "-lc", "echo $DOT_DIST"],
                "darwin",
            ),
            # BSD script(1): -q suppresses banners but still emits control
            # characters, so use check_command_succeeds (not _silent). Exit
            # code propagation is default on BSD (no -e flag needed).
            check_command_succeeds(
                ["script", "-q", "/dev/null", "zsh", "-ilc", "true"]
            ),
        ])

    return checks


BOOTSTRAP_CHECKS: list[Check] = [
    # Symlinks (sample — same shape applies to the other dotfiles).
    check_symlink(f"{_HOME}/.bashrc", f"{_DOTFILES}/.bashrc"),
    # Backup safety: bootstrap must NEVER destroy user data. The runner seeds
    # ~/.bashrc with BACKUP_SENTINEL pre-bootstrap; verify safe_symlink()
    # moved the original content to ~/.bashrc.ORIGINAL before symlinking.
    check_file_contains(f"{_HOME}/.bashrc.ORIGINAL", BACKUP_SENTINEL),
    check_symlink(f"{_HOME}/.bash_profile", f"{_DOTFILES}/.bash_profile"),
    check_symlink(f"{_HOME}/.gitconfig", f"{_DOTFILES}/.gitconfig"),
    check_symlink(f"{_HOME}/.tmux.conf", f"{_DOTFILES}/.tmux.conf"),
    check_symlink(f"{_HOME}/.vimrc", f"{_DOTFILES}/settings/nvim/init.vim"),
    check_symlink(f"{_HOME}/.vim", f"{_DOTFILES}/.vim"),
    # XDG state dirs created by bootstrap.
    check_dir_exists(f"{_HOME}/.local/state/vim/backups"),
    check_dir_exists(f"{_HOME}/.local/state/vim/tmp"),
    # --git-name / --git-email values written to ~/.my_gitconfig...
    check_file_contains(f"{_HOME}/.my_gitconfig", "Testy McTestFace"),
    check_file_contains(f"{_HOME}/.my_gitconfig", "testy@test.com"),
    # ... and git reads them via the .gitconfig [include] chain. NOT using
    # `--global` here: `git config --global` defaults to `--no-includes`
    # ("--includes... Defaults to off when a specific file is given"), which
    # would correctly show the literal `include.path` directive but miss the
    # included user.name/email — the exact bug we hit before this fix.
    check_command_output_matches(["git", "config", "user.name"], "Testy McTestFace"),
    check_command_output_matches(["git", "config", "user.email"], "testy@test.com"),
    # --weather-location 'Seattle' → file written
    check_file_contains(f"{_HOME}/.config/dotfiles/weather_location", "Seattle"),
    # ... and the file propagates to $WEATHER_LOCATION via shell init.
    check_command_output_matches(["bash", "-lc", "echo $WEATHER_LOCATION"], "Seattle"),
    # Catch-all: bash login shell loads silently. DOTFILE_CI_TEST_MODE=1
    # bypasses .bashrc's "skip if not interactive" early-return so we actually
    # exercise the full .bash_profile → .bashrc → env.sh → xdg.sh chain.
    check_command_silent(
        ["env", "DOTFILE_CI_TEST_MODE=1", "bash", "-lc", "true"]
    ),
    # zsh interactive login: exercises the full .zshenv → .zshrc chain
    # (incl. p10k / fzf / iterm2 fragments). `script` wraps the call in a pty
    # so `-i` doesn't trip MONITOR / gitstatus on missing tty. `TERM=dumb` is
    # set because `podman exec` doesn't propagate it; some zsh / terminfo
    # paths emit "TERM environment variable not set" otherwise (Fedora).
    # Three `script` flags carry real weight here:
    #   - `-e` REQUIRED to propagate the inner zsh's exit code; without it
    #     `script` always exits 0 and the rc-branch of `check_command_silent`
    #     is dead.
    #   - `-q` REQUIRED to suppress `script`'s own "Script started/done"
    #     banners (they go to stderr and would trip the silent check).
    #   - `-c` runs the command; the trailing `/dev/null` is the typescript
    #     file we don't want.
    # `script` also merges the inner stdout+stderr into a single stream (which
    # we see as stdout). Total-silence is preserved, but a failure detail
    # saying "unexpected stdout: ..." may actually be the inner shell's stderr.
    # `script(1)` is provided by bsdutils (Essential) on debian/ubuntu and
    # util-linux on fedora — no explicit install needed in the Dockerfiles.
    check_command_silent(
        ["env", "TERM=dumb", "script", "-e", "-qc", "zsh -ilc true", "/dev/null"]
    ),
    # vim and nvim CRASH-ONLY smoke test: confirm the binary launches, parses
    # CLI flags, and quits without segfault. Does NOT meaningfully exercise
    # init.vim — both vim (`-e -s`) and nvim (`--headless`) silently swallow
    # init-time errors (verified: a `.vimrc` containing
    # `call ThisFunctionDoesNotExist()` still exits 0 with no output).
    # See TODO.md for the path to a real init-validation check.
    check_command_succeeds(["vim", "-e", "-s", "-c", "q"]),
    check_command_succeeds(["nvim", "--headless", "-c", "q"]),
    # tmux loads the config under this distro's tmux version (catches option
    # drift across versions). source-file surfaces errors that `tmux -f` swallows.
    check_tmux_config(f"{_HOME}/.tmux.conf"),
    # Downloaded artifacts (plug.vim for vim and nvim).
    check_file_contains(f"{_XDG_DATA}/vim/site/autoload/plug.vim", "plug#begin"),
    check_file_contains(f"{_XDG_DATA}/nvim/site/autoload/plug.vim", "plug#begin"),
    # Plugins were actually installed by `:PlugInstall` (catches the silent
    # no-op bug we hit when bootstrap was using `+'PlugInstall --sync'`).
    # Only nvim has plugins configured today (vim has no plug#begin block in
    # init.vim); add a vim check too if that ever changes.
    check_dir_non_empty(f"{_XDG_DATA}/nvim/plugged"),
    # powerlevel10k cloned — presence of .git confirms a real clone, not a stub dir.
    check_dir_exists(f"{_XDG_DATA}/powerlevel10k/.git"),
]
