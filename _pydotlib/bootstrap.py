"""
Utility functions for the bootstrap.py program.
"""

import copy
import functools
import json
import logging
import os
import re
import shutil
import socket
import ssl
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from _pydotlib.cli import confirm, input_field
from _pydotlib.colors import Colors
from _pydotlib.git import (
    read_git_config_file,
    update_git_config_file,
)

VCS_MISSING_NAME = "TODO_SET_USER_NAME"
VCS_MISSING_EMAIL = "TODO_SET_EMAIL_ADDRESS"

# Closest native Codex equivalent to the useful, portable parts of
# bin/claude-status. Existing user choices are always preserved.
CODEX_STATUS_LINE: tuple[str, ...] = (
    "model-with-reasoning",
    "context-remaining",
    "used-tokens",
    "five-hour-limit",
    "weekly-limit",
    "current-dir",
    "git-branch",
)

_TUI_TABLE_HEADER_RE = re.compile(
    r"(?m)^[ \t]*\[[ \t]*(?:tui|'tui'|\"tui\")[ \t]*\]"
    r"[ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)"
)


class _ConfigMergeError(ValueError):
    """A config is valid but cannot be edited without risking user content."""


class _ConfigWriteError(RuntimeError):
    """A config cannot be replaced without risking a user-owned file."""


@dataclass(frozen=True)
class HookSpec:
    """One Claude Code hook we own: an (event, matcher, command) triple."""

    event: str
    matcher: str | None
    command: str


# Marker that identifies hooks owned by these dotfiles, so the merge only ever
# adds/updates its own entries and never touches unrelated hooks.
CLAUDE_TMUX_STATE_MARKER = "claude-tmux-state"

# ~/-prefixed because Claude Code runs command hooks in a minimal non-interactive
# shell, so bin/ is not on PATH (the shell expands ~).
_CTS = "~/.dotfiles/bin/claude-tmux-state"

# Hooks that drive bin/claude-tmux-state -> the tmux window state icon. Matchers
# follow Claude Code semantics: tool name for Pre/PostToolUse, notification type
# for Notification, session source for SessionStart. present is scoped to a fresh
# startup so a mid-session compact/resume can't reset an in-progress icon.
# needs-input is driven by the AskUserQuestion tool -- PreToolUse sets it (Claude
# is genuinely asking you something), PostToolUse clears it back to busy when you
# answer. It is deliberately NOT driven by Notification idle_prompt, which fires
# ~60s after *every* idle turn (even while a background workflow is still running)
# and so falsely flagged any walked-away session as needing input. (A subagent's
# own AskUserQuestion fires the parent's PreToolUse too, but the paired PostToolUse
# self-clears it, so it only flashes briefly.) See
# docs/claude-code-hooks-and-statusline.md.
CLAUDE_TMUX_STATE_HOOKS: tuple[HookSpec, ...] = (
    HookSpec("SessionStart", "startup", f"{_CTS} present"),
    HookSpec("UserPromptSubmit", None, f"{_CTS} busy"),
    HookSpec("PreToolUse", "Bash", f"{_CTS} running"),
    HookSpec("PreToolUse", "AskUserQuestion", f"{_CTS} needs-input"),
    HookSpec("PostToolUse", "Bash", f"{_CTS} busy"),
    HookSpec("PostToolUse", "AskUserQuestion", f"{_CTS} busy"),
    HookSpec("Notification", "permission_prompt", f"{_CTS} needs-perm"),
    HookSpec("Stop", None, f"{_CTS} idle"),
    HookSpec("StopFailure", None, f"{_CTS} idle"),
    HookSpec("SessionEnd", None, f"{_CTS} clear"),
)


def configure_vcs_author(
    gitconfig_path: Path | str,
    name: str | None = None,
    email: str | None = None,
    dry_run: bool = False,
) -> None:
    """Ensure `gitconfig_path` has user.name and user.email set.

    If the file doesn't exist, it's created with `TODO_SET_*` placeholder
    values that subsequent prompts will overwrite.  For each of name and
    email, if the corresponding `name`/`email` argument is provided, it's
    written directly; otherwise the user is prompted (current value shown
    as the default — Enter to keep, type to change).
    """
    gitconfig_path = Path(gitconfig_path)
    dry_text = "[DRY RUN] " if dry_run else ""

    if gitconfig_path.exists():
        if dry_run:
            logging.info(f"{dry_text}{gitconfig_path} already exists")
            return
    else:
        if dry_run:
            logging.info(f"{dry_text}Would create {gitconfig_path} with git author config")
            return
        gitconfig_path.write_text(
            f"""[user]
  name = {VCS_MISSING_NAME}
  email = {VCS_MISSING_EMAIL}
"""
        )
    def try_update_key(
        keys: dict[str, str],
        key: str,
        placeholder: str,
        default: str | None,
        prompt: str,
    ) -> None:
        # CLI arg always wins.
        if default is not None:
            keys[key] = default
            return

        # Always prompt, showing the current value as the default (if any).
        # Treat "missing" and "placeholder" the same way: no useful default.
        current = keys.get(key)
        real_default = current if current and current != placeholder else None

        new_value = input_field(
            prompt,
            default_message=(real_default if real_default else "leave blank to skip"),
            default=real_default,
        )

        if new_value:
            keys[key] = new_value
        elif key in keys:
            del keys[key]

    git_keys = read_git_config_file(gitconfig_path, ["user:name", "user:email"])

    try_update_key(git_keys, "user:name", VCS_MISSING_NAME, name, "Enter your git name")
    try_update_key(
        git_keys, "user:email", VCS_MISSING_EMAIL, email, "Enter your git email"
    )

    update_git_config_file(gitconfig_path, git_keys)


def _detect_real_editor() -> str:
    if shutil.which("nvim"):
        return "nvim"
    if shutil.which("vim"):
        return "vim"
    env_editor = os.environ.get("EDITOR")
    if env_editor:
        return env_editor
    return "vi"


def _write_config_text(
    path: Path,
    content: str,
    *,
    expected_content: str | None,
    dry_run: bool,
    description: str,
) -> bool:
    """Safely replace a generated config while preserving the original once.

    Returns whether the requested content differs from the live file. Writes use
    a unique same-directory temporary file so ``os.replace`` stays atomic. An
    existing file's permission bits are retained, and any temporary file is
    removed if writing or replacement fails.
    """
    def read_live_file() -> str | None:
        if path.is_symlink():
            raise _ConfigWriteError(f"{path} is a symlink")
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as exc:
            raise _ConfigWriteError(f"could not read {path}: {exc}") from exc

    current = read_live_file()
    if current == content:
        return False
    if current != expected_content:
        raise _ConfigWriteError(f"{path} changed while its update was being prepared")

    dry_text = "[DRY RUN] " if dry_run else ""
    if dry_run:
        logging.info(f"{dry_text}Would update {description} at {path}")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)

        current = read_live_file()
        if current != expected_content:
            raise _ConfigWriteError(f"{path} changed while its update was being written")

        original_mode: int | None = None
        if path.exists():
            original_mode = stat.S_IMODE(path.stat().st_mode)
            backup = Path(str(path) + ".ORIGINAL")
            if not backup.exists():
                shutil.copy2(path, backup)
                logging.info(f"Backed up {path} to {backup}")

        if original_mode is not None:
            temp_path.chmod(original_mode)

        if read_live_file() != expected_content:
            raise _ConfigWriteError(f"{path} changed before it could be replaced")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError as exc:
                logging.warning(f"Could not clean up temporary config {temp_path}: {exc}")

    return True


def _merge_codex_config(config_text: str) -> tuple[str, bool]:
    """Add the native Codex status line without reserializing user TOML."""
    try:
        import tomllib
    except ModuleNotFoundError as exc:
        raise _ConfigMergeError("Codex config updates require Python 3.11 or newer") from exc

    try:
        config = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as exc:
        raise _ConfigMergeError("invalid TOML") from exc

    tui = config.get("tui")
    if tui is not None and not isinstance(tui, dict):
        raise _ConfigMergeError("'tui' is not a table")
    if isinstance(tui, dict) and "status_line" in tui:
        return config_text, False

    newline = "\r\n" if "\r\n" in config_text else "\n"
    status_line = f"status_line = {json.dumps(list(CODEX_STATUS_LINE))}{newline}"

    expected = copy.deepcopy(config)
    expected_tui = expected.setdefault("tui", {})
    expected_tui["status_line"] = list(CODEX_STATUS_LINE)

    if tui is None:
        prefix = config_text
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += newline
        if prefix and not prefix.endswith(newline * 2):
            prefix += newline
        candidates = [f"{prefix}[tui]{newline}{status_line}"]
    else:
        candidates = []
        for table_header in _TUI_TABLE_HEADER_RE.finditer(config_text):
            insert_at = table_header.end()
            prefix = config_text[:insert_at]
            if not prefix.endswith(("\n", "\r")):
                prefix += newline
            candidates.append(f"{prefix}{status_line}{config_text[insert_at:]}")

        # A root dotted key safely extends an implicit `tui` table created by
        # `tui.other = ...` or `[tui.child]`. It cannot extend an inline table;
        # semantic validation below rejects that form without touching it.
        candidates.append(f"tui.{status_line}{config_text}")

    for candidate in candidates:
        try:
            parsed_candidate = tomllib.loads(candidate)
        except tomllib.TOMLDecodeError:
            continue
        if parsed_candidate == expected:
            return candidate, True

    raise _ConfigMergeError("'tui' uses an unsupported TOML form")


def _merge_claude_tmux_hooks(settings: dict[str, Any]) -> bool:
    """Idempotently merge the `CLAUDE_TMUX_STATE_HOOKS` into `settings["hooks"]`.

    Only hooks carrying `CLAUDE_TMUX_STATE_MARKER` are added or updated; every
    other hook (notifications, permission logging, etc.) is left untouched. Each
    (event, matcher) pair gets its own group, identified across runs by the
    marker, so re-running never duplicates and a changed command updates in
    place. A marker hook whose (event, matcher) is no longer in the spec list is
    pruned (and its emptied group dropped), so removing a mapping reconciles an
    existing install. Returns True if anything changed.
    """
    if "hooks" not in settings:
        hooks: dict[str, Any] = {}
        settings["hooks"] = hooks
    elif isinstance(settings["hooks"], dict):
        hooks = settings["hooks"]
    else:
        logging.warning("Claude Code settings 'hooks' is not an object; skipping tmux hook merge")
        return False

    changed = False

    for spec in CLAUDE_TMUX_STATE_HOOKS:
        if spec.event not in hooks:
            groups: list[Any] = []
            hooks[spec.event] = groups
        elif isinstance(hooks[spec.event], list):
            groups = hooks[spec.event]
        else:
            logging.warning(f"Claude Code settings hooks[{spec.event!r}] is not a list; skipping")
            continue
        want_matcher = spec.matcher or ""

        ours: dict[str, Any] | None = None
        for group in groups:
            if not isinstance(group, dict):
                continue
            if (group.get("matcher") or "") != want_matcher:
                continue
            group_hooks = group.get("hooks", [])
            if not isinstance(group_hooks, list):
                continue
            for hook in group_hooks:
                if isinstance(hook, dict) and CLAUDE_TMUX_STATE_MARKER in hook.get("command", ""):
                    ours = hook
                    break
            if ours is not None:
                break

        if ours is None:
            new_group: dict[str, Any] = {
                "hooks": [{"type": "command", "command": spec.command}]
            }
            if spec.matcher is not None:
                new_group["matcher"] = spec.matcher
            groups.append(new_group)
            changed = True
        elif ours.get("command") != spec.command:
            ours["command"] = spec.command
            changed = True

    # Prune marker-owned hooks whose (event, matcher) is no longer in the spec
    # list (e.g. a mapping we removed), so re-running bootstrap reconciles an
    # existing install instead of leaving an orphan behind. Foreign hooks are
    # never touched; a group emptied of its marker hook is dropped.
    wanted = {(spec.event, spec.matcher or "") for spec in CLAUDE_TMUX_STATE_HOOKS}
    for event in list(hooks.keys()):
        if not isinstance(hooks[event], list):
            continue
        prune_groups: list[Any] = hooks[event]
        for group in list(prune_groups):
            if not isinstance(group, dict):
                continue
            if (event, group.get("matcher") or "") in wanted:
                continue
            group_hooks = group.get("hooks", [])
            if not isinstance(group_hooks, list):
                continue
            kept = [
                hook
                for hook in group_hooks
                if not (
                    isinstance(hook, dict)
                    and CLAUDE_TMUX_STATE_MARKER in hook.get("command", "")
                )
            ]
            if len(kept) == len(group_hooks):
                continue
            changed = True
            if kept:
                group["hooks"] = kept
            else:
                prune_groups.remove(group)

    return changed


def configure_claude_code(settings_path: Path, dry_run: bool) -> None:
    """Ensure Claude Code's `settings.json` is wired up to the dotfiles helpers.

    Sets `env.EDITOR` to `claude-editor` and `env.REAL_EDITOR` to whatever
    `_detect_real_editor()` resolves to, adds a `statusLine` pointing at the
    `claude-status` script, and merges the `claude-tmux-state` window-icon hooks.
    Existing keys (including a custom `statusLine`) and unrelated hooks are
    preserved.  Malformed JSON, a non-object top level, or wrong-shaped
    `env`/`hooks` values are left untouched rather than crashing the bootstrap.
    On modification the shared config writer backs up the prior file once and
    atomically replaces it without changing its permission bits.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    original_text: str | None = None
    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            original_text = settings_path.read_text(encoding="utf-8")
            settings = json.loads(original_text)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logging.warning(
                f"Could not read or parse {settings_path}, "
                f"skipping Claude Code configuration: {exc}"
            )
            return
        if not isinstance(settings, dict):
            logging.warning(f"{settings_path} is not a JSON object, skipping Claude Code configuration")
            return

    changed = False

    env = settings.get("env", {})
    desired_editor = "claude-editor"
    desired_real_editor = _detect_real_editor()

    if not isinstance(env, dict):
        logging.warning(f"{dry_text}{settings_path} has a non-object 'env'; leaving editor config untouched")
    elif env.get("EDITOR") != desired_editor or env.get("REAL_EDITOR") != desired_real_editor:
        env["EDITOR"] = desired_editor
        env["REAL_EDITOR"] = desired_real_editor
        settings["env"] = env
        logging.info(f"{dry_text}Setting Claude Code EDITOR={desired_editor}, REAL_EDITOR={desired_real_editor}")
        changed = True
    else:
        logging.debug(f"{dry_text}Claude Code editor already configured")

    if "statusLine" not in settings:
        settings["statusLine"] = {"type": "command", "command": "claude-status"}
        logging.info(f"{dry_text}Setting Claude Code statusLine to claude-status")
        changed = True
    else:
        logging.debug(f"{dry_text}Claude Code statusLine already configured")

    if _merge_claude_tmux_hooks(settings):
        logging.info(f"{dry_text}Merging Claude Code tmux state-icon hooks")
        changed = True
    else:
        logging.debug(f"{dry_text}Claude Code tmux state-icon hooks already configured")

    if changed:
        try:
            _write_config_text(
                settings_path,
                json.dumps(settings, indent=2) + "\n",
                expected_content=original_text,
                dry_run=dry_run,
                description="Claude Code settings",
            )
        except (OSError, _ConfigWriteError) as exc:
            logging.warning(f"Could not safely update {settings_path}: {exc}")


def configure_codex(config_path: Path, dry_run: bool) -> None:
    """Add the native Codex status line while preserving user-owned TOML."""
    try:
        original_text = (
            config_path.read_text(encoding="utf-8") if config_path.exists() else None
        )
    except (OSError, UnicodeError) as exc:
        logging.warning(f"Could not read {config_path}, skipping Codex configuration: {exc}")
        return
    try:
        updated_text, changed = _merge_codex_config(original_text or "")
    except _ConfigMergeError as exc:
        logging.warning(f"Could not safely update {config_path}: {exc}")
        return

    if not changed:
        logging.debug("Codex status line already configured")
        return

    dry_text = "[DRY RUN] " if dry_run else ""
    logging.info(f"{dry_text}Setting Codex native status line")
    try:
        _write_config_text(
            config_path,
            updated_text,
            expected_content=original_text,
            dry_run=dry_run,
            description="Codex configuration",
        )
    except (OSError, _ConfigWriteError) as exc:
        logging.warning(f"Could not safely update {config_path}: {exc}")


def resolve_codex_config_path(home_dir: Path, codex_home: str | None) -> Path:
    """Return Codex's config path, honoring an explicit ``CODEX_HOME``."""
    config_dir = Path(codex_home) if codex_home else home_dir / ".codex"
    return config_dir / "config.toml"


def configure_weather_location(
    location_path: Path | str,
    location: str | None = None,
    dry_run: bool = False,
) -> None:
    """Prompt for and persist the WEATHER_LOCATION value to `location_path`.

    If `location` is provided, it's used directly without prompting (mirrors
    `configure_vcs_author`'s `name`/`email` args).  Otherwise the user is
    shown the current value (from the file if it exists, falling back to
    $WEATHER_LOCATION) and prompted; an empty answer keeps the current value.
    Writes the file only if the resulting value is non-empty and differs from
    what's on disk.
    """
    location_path = Path(location_path)
    dry_text = "[DRY RUN] " if dry_run else ""

    on_disk: str | None = None
    if location_path.exists():
        on_disk = location_path.read_text().strip() or None

    current = on_disk or os.environ.get("WEATHER_LOCATION") or None

    if location is not None:
        new_value: str | None = location.strip() or None
    else:
        new_value = input_field("Enter your weather location", default=current)

    if not new_value:
        logging.info(f"{dry_text}No weather location set, skipping")
        return

    if new_value == on_disk:
        logging.info(f"{dry_text}Weather location already set to {new_value!r}")
        return

    if dry_run:
        logging.info(f"{dry_text}Would write weather location {new_value!r} to {location_path}")
        return

    location_path.parent.mkdir(parents=True, exist_ok=True)
    location_path.write_text(new_value + "\n")
    logging.info(f"Wrote weather location {new_value!r} to {location_path}")


def initialize_vim_plugin_manager(dry_run: bool) -> None:
    """
    Initializes the vim-plug plugin manager for neovim, if it is installed.

    Only nvim is handled: init.vim sets up vim-plug under `has('nvim')`, so plain
    vim has no `plug#begin` block and no plugins to install — running PlugInstall
    there errors with `E492: Not an editor command`. (plug.vim is still
    downloaded for vim so it's available if plugins are added manually.) Add vim
    here if it ever gets a `plug#begin` block.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping vim plugin install")
        return

    if shutil.which("nvim") is None:
        logging.info(f"{dry_text}nvim not installed - skip initializing vim-plug")
        return

    logging.info(f"{dry_text}Initializing vim-plug for nvim")

    if not dry_run:
        # Use `-c "CMD"` per Ex command, not `+'CMD'`. The `+'CMD'` form works in
        # a shell (which strips the single quotes) but via `subprocess` the
        # literal quotes are passed to nvim, which parses `'P` as a mark
        # reference and silently no-ops the install.
        subprocess.check_call(["nvim", "-c", "PlugInstall --sync", "-c", "qa"])


def is_dotfiles_root(path: Path) -> bool:
    """Check if a path is the root of a dotfiles repository."""
    return path.joinpath(".__dotfiles_root__").is_file()


def find_dotfiles_root(start: Path) -> Path | None:
    """Walk up from `start` looking for the `.__dotfiles_root__` marker file.

    Returns the first ancestor (or `start` itself) containing the marker, or
    `None` if no marker is found before reaching the filesystem root.
    """
    current = start.resolve()
    while True:
        if is_dotfiles_root(current):
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def create_backup_filename(target: Path) -> Path:
    backup_path = Path(str(target) + ".ORIGINAL")

    if backup_path.exists():
        name, ext = os.path.splitext(backup_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")[
            :-3
        ]  # First three millisecond digits.
        backup_path = Path(f"{name}_{timestamp}{ext}")

    return backup_path


def _under(child: Path, parent: Path) -> bool:
    """True if `child` (resolved) lives inside `parent` (resolved)."""
    try:
        return child.resolve().is_relative_to(parent.resolve())
    except (OSError, ValueError):
        return False


def safe_symlink(
    source: Path,
    target: Path,
    dry_run: bool,
    dotfiles_root: Path | None = None,
) -> None:
    """
    Create a symlink at `target` pointing to `source`, taking precautions against
    overwriting the user's existing files.

    Behavior by target state:
      - already symlinked to `source` → no-op
      - missing → create the symlink (and its parent dir if needed)
      - broken symlink → unlink and replace
      - symlink to another file inside `dotfiles_root` (when provided) → silently
        re-point to `source` (handles repo-internal moves without prompting)
      - regular file or directory → prompt to back up to `.ORIGINAL`; if the
        user declines, skip this file entirely (we never overwrite without a
        backup)

    Args:
        source: A dotfiles file to symlink to.
        target: Path in the user's home directory that will be symlinked to `source`.
        dry_run: Print the action but don't actually do it.
        dotfiles_root: If provided, enables the auto-update behavior for stale
            dotfiles-managed symlinks. Pass the repo root.

    Raises:
        FileNotFoundError: if `source` doesn't exist.
    """
    if not source.exists():
        raise FileNotFoundError(f"{source} does not exist")

    dry_text = "[DRY RUN] " if dry_run else ""

    # Create the directory leading up to the target if it doesn't exist.
    if not target.parent.exists():
        if dry_run:
            logging.info(f"{dry_text}Would create dir {target.parent}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created dir {target.parent}")

    # Skip if the target is already symlinked to source.
    if target.is_symlink() and target.resolve() == source.resolve():
        logging.info(f"{dry_text}{target} is already symlinked to {source}")
        return

    # Auto-update a symlink that points elsewhere inside the dotfiles repo
    # (e.g., the file moved within the repo since the user last bootstrapped).
    # Both the existing target and the new source must be inside dotfiles_root —
    # the paranoia guard ensures we only do this for managed-by-us links.
    if (
        dotfiles_root is not None
        and target.is_symlink()
        and _under(target, dotfiles_root)
        and _under(source, dotfiles_root)
    ):
        if not dry_run:
            target.unlink()
        logging.info(f"{dry_text}Updating stale dotfiles symlink at {target}")
        # Fall through to symlink creation.

    # Remove broken symlinks so we can replace them.
    elif target.is_symlink() and not target.exists():
        if not dry_run:
            target.unlink()
        logging.info(f"{dry_text}Removed broken symlink {target}")

    # Does the target file name already exist on the disk?
    if target.exists():
        # Ask the user if we should back the file up (renaming to .ORIGINAL)
        # before replacing it with a symlink.  Declining skips this file
        # entirely — we never overwrite without a backup.
        backup_path = create_backup_filename(target)

        if not confirm(
            message=f"{Colors.BOLD}Rename {target} to {backup_path.name} before replacing with symlink?{Colors.RESET}",
            default=True,
        ):
            logging.info(f"{dry_text}Skipping {target} (declined backup)")
            return

        if not dry_run:
            target.rename(backup_path)

        logging.info(f"{dry_text}Renamed {target} to {backup_path}")

    # Create the symlink.
    if not dry_run:
        target.symlink_to(source)

    logging.info(f"{dry_text}Symlinked {target} to {source}")


def create_dirs(dry_run: bool, dirs: list[str | Path]) -> None:
    """Create each directory in `dirs` if it doesn't already exist.

    No-op if the path already exists as a directory; logs an error if it
    exists as a file.  Parent directories are created as needed.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    for d in dirs:
        d = Path(d)

        if d.exists() and not d.is_dir():
            logging.error(f"{dry_text}expected {d} to be a directory, but it is not")
        elif d.exists():
            logging.info(f"{dry_text}{d} already exists")
        else:
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

            logging.info(f"{dry_text}Created dir {d}")


def download_file(url: str, dest: Path, dry_run: bool) -> bool:
    """
    Download a file from URL to a destination path.
    Tries urllib first, falls back to curl if SSL issues occur.

    Args:
        url: URL to download from.
        dest: Destination path for the downloaded file.
        dry_run: Print the action but don't actually download anything.

    Returns:
        True if download succeeded (or was skipped under dry-run), False otherwise.
    """
    if dry_run:
        logging.info(f"[DRY RUN] Would download {url} to {dest}")
        return True

    try:
        with urllib.request.urlopen(
            url, context=ssl.create_default_context(), timeout=10
        ) as response:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(response.read())

            logging.info(f"Downloaded {url} to {dest}")
            return True
    except (ssl.SSLError, urllib.error.URLError) as e:
        logging.info(
            f"downloading with urllib failed, will try curl instead. (exception: {e})"
        )

        try:
            subprocess.run(
                ["curl", "-fLo", str(dest), "--create-dirs", "--connect-timeout", "10", url],
                capture_output=True,
                check=True,
            )

            logging.info(f"Downloaded {url} to {dest} with curl")
            return True
        except subprocess.CalledProcessError as curl_error:
            stderr = curl_error.stderr.decode().strip() if curl_error.stderr else ""
            logging.exception(f"Failed to download {url} with curl: {stderr}")
            return False
        except FileNotFoundError:
            logging.exception("`curl` was not found. Please install it")
            return False


@functools.cache
def _has_internet() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def download_files(
    urls: list[tuple[str, Path]],
    dry_run: bool,
    skip_if_dest_exists: bool = True,
) -> None:
    """Download a batch of (url, dest) pairs via `download_file`.

    Short-circuits the whole batch when `_has_internet()` is False (logs a
    warning and returns).  Targets that already exist on disk are skipped
    when `skip_if_dest_exists` is True (the default).
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping downloads")
        return

    for url, target in urls:
        target = Path(target)

        if skip_if_dest_exists and target.exists():
            logging.info(f"{dry_text}{target} already exists - skipping download")
        else:
            download_file(url=url, dest=target, dry_run=dry_run)


def git_clone(url: str, dest: Path, dry_run: bool, depth: int | None = None) -> bool:
    """
    Clone a git repository to a destination path.

    Args:
        url: Git repository URL to clone.
        dest: Destination directory for the cloned repository.
        dry_run: Print the action but don't actually do it.
        depth: If specified, create a shallow clone with this history depth.

    Returns:
        True if clone succeeded, False otherwise.
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    cmd = ["git", "clone"]
    if depth is not None:
        cmd += ["--depth", str(depth)]
    cmd += [url, str(dest)]

    logging.info(f"{dry_text}Cloning {url} to {dest}")

    if not dry_run:
        # Let any OSError from mkdir propagate — a broken parent directory
        # means the user's environment needs attention, not a silent skip.
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clone {url}: {e.stderr.decode().strip()}")
            return False

    return True


def git_clone_repos(
    repos: list[tuple[str, Path]],
    dry_run: bool,
    skip_if_dest_exists: bool = True,
    depth: int | None = None,
) -> None:
    """Clone a batch of (url, dest) repos via `git_clone`.

    Short-circuits the whole batch when `_has_internet()` is False (logs a
    warning and returns).  Destinations that already exist are skipped when
    `skip_if_dest_exists` is True (the default).
    """
    dry_text = "[DRY RUN] " if dry_run else ""

    if not dry_run and not _has_internet():
        logging.warning("No internet connectivity detected - skipping git clones")
        return

    for url, dest in repos:
        dest = Path(dest)

        if skip_if_dest_exists and dest.exists():
            logging.info(f"{dry_text}{dest} already exists - skipping clone")
        else:
            git_clone(url=url, dest=dest, dry_run=dry_run, depth=depth)
