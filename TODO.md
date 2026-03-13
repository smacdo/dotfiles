# Top Level Scripts
## Bootstrap
- [x] Replace occurrences of .dotfiles with a environment variable
- Add option to cancel (skip) the backup/delete interactive prompt.
- Check if target exists, is a symlink and was symlinked somewhere in dotfiles repo for safe_symlink.
- download_file: Download to temporary location, and compare to dest. Prompt user if there is mismatch.

## Linting
- [x] Lint shell scripts with shellcheck
- Suppress the "All checks passed!" output from mypy. 
- Print out a summary of the files with failing lints at the end.
- Lint `run_tests.py`

## Testing
- [x] Add script to automate dotfile updating, syncing
- ~~Finish post init scripts~~
- Discover and run python unit tests in bin/ scripts
- run_pydotlib_tests: Search for pydotlib modules without having to hardcode the names.
- Print docker output when a docker test run fails
- Refactor docker script code into pydotlib module.
- Docker test: Run bootstrap.py to validate functionality for debian, fedora and ubuntu
- Docker test: post bootstrap, check if bash OK
- Docker test: post bootstrap, check if ZSH OK
- Docker test: post bootstrap, check if vim OK
- Docker test: post bootstrap, check if neovim OK
- Docker test: post bootstrap, check if tmux OK
- Docker test: post bootstrap, check if git OK

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

# Bin Scripts
- Script that line breaks excessively long command lines
- backup: Simple script that creates foo.bak_N while avoiding race conditions
- mksh:
  - source the author name for an dotfile envvar $S_DEFAULT_AUTHOR
