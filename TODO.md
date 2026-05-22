# Top Level Scripts
## Bootstrap
- [x] Replace occurrences of .dotfiles with a environment variable
- [x] Add option to cancel (skip) the backup/delete interactive prompt.
- Add a `choose()` helper in `_pydotlib/cli.py` for multi-option prompts (e.g. backup / skip / overwrite-without-backup). Then revisit `safe_symlink`'s prompt UX. Want to iterate on copy and option set.
- [x] Check if target exists, is a symlink and was symlinked somewhere in dotfiles repo for safe_symlink.
- download_file: Download to temporary location, and compare to dest. Prompt user if there is mismatch.
- `initialize_vim_plugin_manager`: appears to be misbehaving — investigate. Also add test coverage; either unit tests (mock `subprocess.check_call` and the `shutil.which` lookups) or a docker integration test that runs bootstrap end-to-end and verifies plugins were installed (e.g. check `~/.vim/plugged/` contents).
- Move `~/.my_gitconfig` into `$XDG_CONFIG_HOME/dotfiles/my_gitconfig` so it lives next to `weather_location` and the other XDG-managed state. Needs a migration plan for existing users (detect the legacy path and either move it or warn). Also update the `[include]` entry in the committed `.gitconfig`. While we're at it, audit other `$HOME` dotfiles (`.my_*`, `.config/dotfiles/0_my_*`, etc.) and figure out a general migration strategy before doing one-off moves.
- Initialize ~/.config/dotfiles/... (the path to the my shell env file)
  - Interactive prompt for weather location
  - other vars that need to be set? can't remember...
- Add a doctor mode that checks for common problems and (sometimes) auto-fixes them
  - check if common programs are installed (especially ones used by the dotfiles)
  - check if expected env vars are set
  - etc
  - Check for MacOS Python SSL misconfiguration
- After landing the vim → XDG migration, teach bootstrap to detect known-stale paths (e.g. `~/.dotfiles/.vim/autoload/plug.vim`, `~/.dotfiles/.vim/plugged/`) and log a one-line warning naming the new location + suggesting `bin/dotfiles-cleanup`. See CLAUDE.md "Migration / backwards-compat policy".
- Symlink-write hygiene: `~/.vim`, `~/.zsh`, and `~/.local/share/nvim/site/plugin` are directory symlinks into the repo, so any subpath write under them lands in `~/.dotfiles/`. Audit candidates: vim/nvim runtime artifacts (netrw history, swap, undo) that default to `~/.vim/`; if any escape into the repo, configure them to write to `$XDG_STATE_HOME/vim/` instead. Same caution applies to `~/.zsh/` and the nvim plugin dir if anything ever starts writing there.
- `bin/dotfiles-cleanup`: opt-in script that removes orphaned files left over from past migrations. Each migration adds a stanza that prompts before removing. Pairs with the "bootstrap never deletes" rule in CLAUDE.md.
- Offline install: `bundled/` directory (gitignored, populated by `bin/export-dotfiles`) carrying pre-downloaded artifacts (`plug.vim`, `powerlevel10k`, vim plugins). Bootstrap checks `bundled/<name>` before falling back to network. Add `--offline` flag to force-prefer bundled. Pairs with the existing "Export dotfiles as a tarball/zip" item under Misc.

### MacOS Python SSL Misconfiguration
error: ` urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer 
 certificate (_ssl.c:1020)>` when running `urllib.request.urlopen(...)`

problem is the python installed via homebrew or standalone doesn't use the system's certificates.

## Linting
- [x] Lint shell scripts with shellcheck
- Suppress the "All checks passed!" output from mypy. 
- Print out a summary of the files with failing lints at the end.
- Lint `run_tests.py`
- Expand lint scope to include `tools/` shell scripts (currently only `shell_profile/`, root configs, and `bin/` are linted).

## Testing
- [x] Add script to automate dotfile updating, syncing
- [x] Support podman instead of docker (auto-detect, --runtime flag)
- ~~Finish post init scripts~~
- Discover and run python unit tests in bin/ scripts
- run_pydotlib_tests: Search for pydotlib modules without having to hardcode the names.
- ColoredLogFormatter: figure out how to test the actual ANSI escape codes are emitted (or not). Today's test only checks that level/message round-trip — color output is coupled to the import-time `Colors` singleton, which depends on the `should_use_colors()` cache.
- [x] Print container runtime output when a test run fails
- Extract container runtime ops (detect_runtime, discover_flavors, build_image, run_exec, remove_container) into `_pydotlib/container.py` with unit tests.
- Install zsh, neovim, tmux in all test containers; add functional post-bootstrap checks (`zsh -nc 'source ~/.zshrc'`, `nvim --headless -c 'q'`, `tmux -f ~/.tmux.conf -C kill-server`).
- Upgrade-path tests under `tests/docker/upgrade_from_v<N>/`: pre-populate the prior-layout state, run bootstrap, assert clean completion + new artifacts exist in their new homes. Same suite covers idempotency: run bootstrap twice from clean → second run is no-op-or-quiet. See CLAUDE.md "Migration / backwards-compat policy".
- Dry-run test: run bootstrap with --dry-run; assert no symlinks/files were created.
- Backup-behavior test: pre-create ~/.bashrc with custom content; bootstrap must preserve original in .bashrc.ORIGINAL.
- Per-machine override test: write `~/.config/dotfiles/my_shell_profile.sh` exporting a var; `bash -lc 'echo $VAR'` should print it.
- Parallelize distro runs (ThreadPoolExecutor over `discover_flavors`).
- CI: matrix-test against both podman and docker via `--runtime`.
- Optional `--keep-containers` flag for debugging failed runs.

## Misc
- Export dotfiles as a tarball/zip for machines that cannot connect to internet. The archive should include out of tree files, and be made to expand in user home dir, eg
  - ./.dotfiles/...
  - ./.config/neovim
  - ...
- Export the _pydotlib so python bin scripts can use them.

# Configs
## Neovim
- Create crontab script to nuke backups after ~ 90 days?

# Bugs
- neovim not detecting BUCK file type
- neovim should detect hg commit message, and then not hard linebreak on them

## Shell Profile Bugs (from code review)

- **`functions.sh:167` `is_cygwin` broken regex**: `expr "$(uname -s)" : '^CYGWIN*'` uses BRE where
  `*` means "zero or more of the preceding char", so `CYGWIN*` matches "CYGWI" + zero-or-more "N"s.
  Fix: change to `'^CYGWIN.*'`.

- **`functions.sh:227` `mkd` passes multiple args to `cd`**: `mkdir -p "$@" && cd "$@"` fails when
  called with more than one argument since `cd` accepts exactly one. Fix: `cd "$1"` or `cd "${1:-.}"`.

- **`functions.sh:238` `mktmp`: `type pushd` leaks stderr**: In POSIX sh environments where `pushd`
  doesn't exist, `type pushd >/dev/null` may still emit an error on stderr. Fix: `>/dev/null 2>&1`.

- **`.bash_profile:24` hardcoded `$HOME/.dotfiles` path**: Line 21 correctly uses `$S_DOTFILE_ROOT`
  but line 24 hardcodes `$HOME/.dotfiles/shell_profile/env.sh`. Breaks non-default install paths.
  Fix: use `$S_DOTFILE_ROOT/shell_profile/env.sh`.

- **`.bashrc:40` unquoted variable in `[ -z ]`**: `[ -z ${S_DOTFILE_ROOT+x} ]` should be
  `[ -z "${S_DOTFILE_ROOT+x}" ]`. Inconsistent with the correctly-quoted version in `.zshrc:29`.

## Shell Profile Potential Issues (from code review)

- **`env.sh:18-29` `which` is not portable**: `which` is not POSIX, not universally available, and on
  some systems prints "no nvim in ..." to stdout (not stderr). Fix: replace all `which <cmd>` with
  `command -v <cmd> >/dev/null 2>&1`.

- **`xdg.sh:15-24` global variable leak**: `ENV_NAME`, `CURRENT_VAL`, `DEFAULT_DIR`, and `ACTUAL_VAL`
  are set inside `xdg_define()` but never cleaned up — they persist in the shell environment after the
  function returns. Fix: declare them `local`, or `unset` them at the end of the function.

- **`aliases.sh:18-22` `ls_color_flag` leaks into environment**: The variable is set globally and
  never `unset`. The aliases reference it at invocation time (single quotes), so it must stay set
  forever. Fix: either `unset ls_color_flag` after defining the aliases and hardcode the flag value
  directly into each alias, or keep the variable but document the dependency.

- **`.bashrc:114` `HOSTFILE` points to wrong-format file**: `export HOSTFILE=${HOME}/.ssh/known_hosts`
  — bash `HOSTFILE` expects one hostname per line, but `known_hosts` uses a completely different format
  (key type, hostname, public key). Hostname completion almost certainly doesn't work as intended.
  Fix: either remove this line or point to a proper hostfile.

- **`functions.sh:27-31` `lsb_release` command not checked before use**: Checks if `/etc/lsb-release`
  file exists but doesn't verify the `lsb_release` command is installed. On systems where the file
  exists but the package isn't installed, `DOT_DIST` silently becomes empty.
  Fix: add `&& command -v lsb_release >/dev/null 2>&1` to the condition.

- **`.zshrc:167` `BREW_PREFIX` may be unset when fzf loads**: `BREW_PREFIX` is only set if
  `type brew` succeeded inside the p10k block (lines 130–137). If brew wasn't found, `BREW_PREFIX` is
  unset and `"${BREW_PREFIX}/opt/fzf/..."` silently expands to `/opt/fzf/...`. Fix: guard with
  `[[ -n "${BREW_PREFIX:-}" ]]` or re-check `type brew` before loading fzf.

- **`.zshrc:162` iTerm2 script sourced without existence check**: Unlike other `source` calls in the
  file, `source "${S_DOTFILE_ROOT}/vendor/iterm2/zsh"` has no `-f`/`-r` guard — if the file doesn't
  exist zsh prints an error. Fix: `[[ -f "${S_DOTFILE_ROOT}/vendor/iterm2/zsh" ]] && source ...`.

## Shell Profile Minor Issues (from code review)

- **`.zshrc:72-74` redundant history setopts**: `SHARE_HISTORY` implies `INC_APPEND_HISTORY`, making
  both `APPEND_HISTORY` and `INC_APPEND_HISTORY` redundant. Only `SHARE_HISTORY`, `HIST_FIND_NO_DUPS`,
  and `HIST_REDUCE_BLANKS` are needed.

- **`aliases.sh:96-100` `egrep`/`fgrep` are deprecated**: Removed from POSIX.1-2017. Prefer
  `grep -E` (for `egrep`) and `grep -F` (for `fgrep`).

- **`aliases.sh:107` `echo -e` not POSIX, duplicates `show_path`**: `alias printpath='echo -e
  ${PATH//:/\\n}'` uses a bash/zsh-ism and is a near-duplicate of the `show_path` function in
  `functions.sh` which uses portable `tr`. Consider removing `printpath` and documenting `show_path`,
  or keeping only one.

- **`env.sh:44-47` missing `/usr/bin/lesspipe` (no `.sh`) for Debian/Ubuntu**: The `LESSOPEN` setup
  only checks `lesspipe.sh` variants, but Debian/Ubuntu installs it as `/usr/bin/lesspipe`.
  `.zshrc:149` separately handles this with `eval "$(lesspipe)"`, creating two overlapping code paths
  that could conflict. Consolidate into one approach.

- **`functions.sh:66-69` fragile `sysctl` character-offset parsing on macOS**: Uses hardcoded column
  offsets (`cut -c 17-`, `cut -c 18-`) to strip the `kern.osrelease: ` prefix. Fix: use
  `sysctl -n kern.osrelease` and `sysctl -n kern.osrevision` which print only the value.

- **`.zshenv:5-6` unquoted variables in `source` calls**: `source ${S_DOTFILE_ROOT}/shell_profile/paths.sh`
  should be `source "${S_DOTFILE_ROOT}/shell_profile/paths.sh"` to handle paths with spaces.

# Misc
- Github action to run linter
- Github action to run tests

# Tools (`tools/`)

## VS Code installer
- Add macOS support (`brew install --cask visual-studio-code`). Currently Linux-only (Debian/Ubuntu, Fedora/RHEL/CentOS). On WSL, VS Code is installed on the Windows side and accessed via Remote — no Linux install needed.

# Bin Scripts
- Script that line breaks excessively long command lines
- backup: Simple script that creates foo.bak_N while avoiding race conditions
- mksh:
  - source the author name for an dotfile envvar $S_DEFAULT_AUTHOR
