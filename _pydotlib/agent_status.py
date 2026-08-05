"""Reusable working-directory status helpers for coding-agent displays."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from _pydotlib import vcs


@dataclass(frozen=True)
class DirectoryStatus:
    """Display-ready directory and version-control facts."""

    display_path: str
    vcs_kind: vcs.VcsKind | None = None
    display_revision: str = ""
    diffstat: str = ""


def shorten_monorepo_path(display_path: str, repos: Sequence[str]) -> str:
    """Collapse deep paths under configured repository basenames."""
    if not repos or not display_path.startswith("~/"):
        return display_path
    parts = display_path[2:].split("/")
    if parts[0].rstrip("0123456789") not in repos:
        return display_path
    tail = parts[1:]
    if len(tail) <= 3:
        return display_path
    return f"~/{parts[0]}/.../" + "/".join(tail[-2:])


def format_display_path(
    cwd: str,
    *,
    home: str | None = None,
    monorepos: Sequence[str] = (),
) -> str:
    """Abbreviate the home directory and any configured deep monorepo path."""
    home_dir = home if home is not None else os.path.expanduser("~")
    if cwd == home_dir:
        display_path = "~"
    elif cwd.startswith(home_dir + os.sep):
        display_path = "~" + cwd[len(home_dir):]
    else:
        display_path = cwd
    return shorten_monorepo_path(display_path, monorepos)


def collect_directory_status(
    cwd: str,
    *,
    home: str | None = None,
    monorepos: Sequence[str] = (),
) -> DirectoryStatus:
    """Collect display path, branch/bookmark, and diffstat for ``cwd``."""
    vcs_status = vcs.collect_vcs_status(cwd)
    return DirectoryStatus(
        display_path=format_display_path(cwd, home=home, monorepos=monorepos),
        vcs_kind=vcs_status.repository.kind if vcs_status else None,
        display_revision=vcs_status.display_revision if vcs_status else "",
        diffstat=vcs_status.diffstat if vcs_status else "",
    )
