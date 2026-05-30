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

## 2026-05-29
- **Fixed** `detect_os()` not recognizing 64-bit ARM on Linux. `uname -m` reports `aarch64` there (macOS reports `arm64`); the unmatched case printed `WARN: Could not detect architecture via 'uname -m'!` at every shell startup and left `DOT_ARCH=0`. Both now map to `DOT_ARCH=arm64`. Affects Linux ARM machines (incl. containers on Apple Silicon); no action needed beyond re-sourcing your shell.

## 2026-05-22
- **Moved** `~/.vim/autoload/plug.vim` (which symlinked into `~/.dotfiles/.vim/autoload/`) → `$XDG_DATA_HOME/vim/site/autoload/plug.vim`. Re-running bootstrap downloads it to the new location. Old file orphaned inside the repo tree; safe to `rm ~/.dotfiles/.vim/autoload/plug.vim` (and the empty `autoload/` dir) when ready — a future `bin/dotfiles-cleanup` will automate. nvim's plug.vim location is unchanged.
- **Added** runtimepath entry in `settings/nvim/init.vim` so vim auto-loads plug.vim from the new XDG path. nvim already had `$XDG_DATA_HOME/nvim/site` on its default runtimepath via `stdpath('data')` — no nvim change.
- **Fixed** `bootstrap.py` silently skipping `:PlugInstall` for nvim due to shell-vs-subprocess quoting (`+'PlugInstall --sync'` was passed to vim with literal single quotes; vim parsed `'P` as a mark reference and no-op'd the install). Existing installs: run `nvim +PlugInstall +qa` once to populate `~/.local/share/nvim/plugged/`, or re-run `./bootstrap.py`.
