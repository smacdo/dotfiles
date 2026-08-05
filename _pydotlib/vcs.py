"""Cross-VCS repository discovery and lightweight status queries."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VcsKind = Literal["git", "sapling"]
CommandRunner = Callable[[Sequence[str], Path], str | None]

_GIT = ("git", "-c", "core.hooksPath=/dev/null")
_MAIN_REVISIONS = frozenset(("main", "master"))


@dataclass(frozen=True)
class Repository:
    """A version-control checkout found on disk."""

    kind: VcsKind
    root: Path


@dataclass(frozen=True)
class VcsStatus:
    """Compact version-control facts suitable for a status display."""

    repository: Repository
    display_revision: str = ""
    diffstat: str = ""


def _run_command(argv: Sequence[str], cwd: Path) -> str | None:
    """Run a short VCS query, returning stdout without trailing whitespace."""
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            check=False,
            errors="replace",
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    return result.stdout.rstrip() if result.returncode == 0 else None


def find_repository(path: str | Path) -> Repository | None:
    """Find the nearest Git or Sapling repository containing ``path``."""
    current = Path(path).absolute()
    while True:
        # .git can be a directory or a worktree marker file. Sapling commonly
        # uses .sl or .hg; both are queried through the public `sl` command.
        if current.joinpath(".git").exists():
            return Repository(kind="git", root=current)
        if current.joinpath(".sl").exists() or current.joinpath(".hg").exists():
            return Repository(kind="sapling", root=current)
        if current.parent == current:
            return None
        current = current.parent


def parse_diffstat(summary: str) -> str:
    """Convert a Git/Sapling shortstat summary to ``+added -removed``."""
    added = removed = 0
    for part in summary.split(","):
        words = part.strip().split()
        if not words:
            continue
        if "insertion" in part:
            added = int(words[0])
        elif "deletion" in part:
            removed = int(words[0])
    parts: list[str] = []
    if added:
        parts.append(f"+{added}")
    if removed:
        parts.append(f"-{removed}")
    return " ".join(parts)


def select_sapling_display_revision(log_output: str) -> str:
    """Choose a non-main bookmark, or the hash of a local draft commit."""
    lines = log_output.split("\n")
    bookmarks = lines[0].split() if lines else []
    phase = lines[1] if len(lines) > 1 else ""
    short_hash = lines[2] if len(lines) > 2 else ""
    for bookmark in bookmarks:
        if bookmark not in _MAIN_REVISIONS:
            return bookmark
    if phase == "draft" and short_hash:
        return short_hash
    return ""


def _git_status(repository: Repository, run_command: CommandRunner) -> VcsStatus:
    branch = run_command((*_GIT, "branch", "--show-current"), repository.root) or ""
    display_revision = branch if branch not in _MAIN_REVISIONS else ""
    if not display_revision:
        return VcsStatus(repository=repository)
    summary = run_command(
        (*_GIT, "diff", "--no-color", "--shortstat", "HEAD"),
        repository.root,
    )
    return VcsStatus(
        repository=repository,
        display_revision=display_revision,
        diffstat=parse_diffstat(summary) if summary else "",
    )


def _sapling_status(repository: Repository, run_command: CommandRunner) -> VcsStatus:
    output = run_command(
        ("sl", "log", "-r", ".", "-T", "{bookmarks}\n{phase}\n{node|short}"),
        repository.root,
    )
    display_revision = select_sapling_display_revision(output) if output else ""
    if not display_revision:
        return VcsStatus(repository=repository)
    output = run_command(("sl", "diff", "--stat"), repository.root)
    if not output:
        return VcsStatus(repository=repository, display_revision=display_revision)
    summary = next(
        (line for line in reversed(output.split("\n")) if "changed" in line),
        "",
    )
    return VcsStatus(
        repository=repository,
        display_revision=display_revision,
        diffstat=parse_diffstat(summary),
    )


def collect_vcs_status(
    path: str | Path,
    *,
    run_command: CommandRunner | None = None,
) -> VcsStatus | None:
    """Collect the current revision and diffstat for the checkout at ``path``."""
    repository = find_repository(path)
    if repository is None:
        return None
    runner = run_command or _run_command
    if repository.kind == "git":
        return _git_status(repository, runner)
    return _sapling_status(repository, runner)
