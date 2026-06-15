# Changelog

User-visible changes to dotfiles. Reverse-chronological. See
`CLAUDE.md` "Migration / backwards-compat policy" for the format and the
philosophy ("bootstrap adds and overwrites-with-backup; never deletes or
moves user data — cleanup is opt-in").

Entry format:

```
## YYYY-MM-DD
- **Moved** old/path → new/path. Old location orphaned; `bin/dotfiles-cleanup` removes it.
- **Added** new/path. No action needed.
- **Removed** support for X. Safe to `rm path/to/x` locally.
```

## 2026-06-15
- **Fixed** `bin/claude-status` (Claude Code status line) reporting session duration as `<1min` forever on Linux — it derived elapsed time from a BSD-only `stat -f` call. Duration now comes from the status-line payload (`cost.total_duration_ms`) and is correct on all platforms.
- **Changed** `bin/claude-status` to show the real session cost (`cost.total_cost_usd`) instead of a guess from a hard-coded price table, render large token counts as `1.2m` (not `1200k`), and label the working dir with the git branch *or* Sapling bookmark plus a live `+/-` diffstat. If your `~/.claude/settings.json` `statusLine` points at a custom script, set its command to `claude-status` to pick this up.
- **Added** `CLAUDE_STATUS_MONOREPOS` env var: space/comma-separated repo basenames whose deep paths collapse to `~/<repo>/.../<dir>` in the status line. Unset by default (no collapsing); set it in `~/.config/dotfiles/my_shell_profile.sh`.

## 2026-06-05
- **Fixed** `bootstrap.py` cloning powerlevel10k from `gitee.com`, which is unreachable from most networks (and CI), leaving zsh without the powerlevel10k prompt theme. Now clones from `github.com/romkatv/powerlevel10k` (canonical source, matching `tools/install_powerlevel10k.sh`). Existing installs with a populated `~/.local/share/powerlevel10k` are untouched — bootstrap skips clones when the destination exists; installs where the gitee clone had failed get the theme on the next `./bootstrap.py`.
- **Fixed** `.bash_profile` not sourcing `xdg.sh`/`env.sh` in non-interactive login shells (e.g. `bash -lc`). `.bashrc`'s non-interactive early-return runs before it exports `S_DOTFILE_ROOT`, so the subsequent `$S_DOTFILE_ROOT`-based sources silently no-op'd; `.bash_profile` now sets `S_DOTFILE_ROOT` itself first. Effect: env vars like `EDITOR` and `WEATHER_LOCATION` are now set in `bash -lc` login shells. No action needed.
- **Fixed** shell-helper bugs in `shell_profile/functions.sh`: `is_cygwin` regex (`^CYGWIN*` matched `CYGWI`), `mkd` failing on multiple args, `mktmp` leaking a `type` error to stderr, and fragile macOS `sysctl` column slicing (now `sysctl -n`). No action needed.

## 2026-05-29
- **Fixed** `detect_os()` not recognizing 64-bit ARM on Linux. `uname -m` reports `aarch64` there (macOS reports `arm64`); the unmatched case printed `WARN: Could not detect architecture via 'uname -m'!` at every shell startup and left `DOT_ARCH=0`. Both now map to `DOT_ARCH=arm64`. Affects Linux ARM machines (incl. containers on Apple Silicon); no action needed beyond re-sourcing your shell.
- **Fixed** `bootstrap.py` running `:PlugInstall` for plain vim, which printed `E492: Not an editor command` on every run — `init.vim` only configures vim-plug under `has('nvim')`, so vim has no `PlugInstall` command. Bootstrap now initializes plugins for nvim only (vim still gets `plug.vim` downloaded, in case you add plugins manually). No action needed.

## 2026-05-22
- **Moved** `~/.vim/autoload/plug.vim` (which symlinked into `~/.dotfiles/.vim/autoload/`) → `$XDG_DATA_HOME/vim/site/autoload/plug.vim`. Re-running bootstrap downloads it to the new location. Old file orphaned inside the repo tree; safe to `rm ~/.dotfiles/.vim/autoload/plug.vim` (and the empty `autoload/` dir) when ready — a future `bin/dotfiles-cleanup` will automate. nvim's plug.vim location is unchanged.
- **Added** runtimepath entry in `settings/nvim/init.vim` so vim auto-loads plug.vim from the new XDG path. nvim already had `$XDG_DATA_HOME/nvim/site` on its default runtimepath via `stdpath('data')` — no nvim change.
- **Fixed** `bootstrap.py` silently skipping `:PlugInstall` for nvim due to shell-vs-subprocess quoting (`+'PlugInstall --sync'` was passed to vim with literal single quotes; vim parsed `'P` as a mark reference and no-op'd the install). Existing installs: run `nvim +PlugInstall +qa` once to populate `~/.local/share/nvim/plugged/`, or re-run `./bootstrap.py`.
