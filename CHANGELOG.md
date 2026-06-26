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

## 2026-06-25
- **Fixed** `bin/claude-status` showing a context percentage and token bracket that disagreed (e.g. `◑ 47% [2k/1.00m]`). The bracket was rebuilt from `current_usage`'s input + cache-read tokens, which collapses right after a cache write; it now derives from the authoritative `used_percentage`, so the two always agree. No action needed.
- **Fixed** `bin/claude-status` flashing a bogus `◑ 0%` / `↓0 ↑0` while Claude Code feeds the status line an all-zero payload during `/compact`. Token usage is now suppressed and the context slot shows a quiet `◑ …` placeholder until the rebuilt percentage arrives on your next turn. No action needed.
- **Changed** the Claude Code tmux state icon: the red "needs input" question mark is now driven by the `AskUserQuestion` tool — it appears only when Claude actually asks you something and clears when you answer — instead of the `idle_prompt` notification, which fired ~60s after *every* idle turn (even while a background workflow was still running), falsely flagging walked-away sessions as needing input. Re-run `./bootstrap.py` to update the hooks in `~/.claude/settings.json`; takes effect in a new Claude Code session.

## 2026-06-18
- **Fixed** tmux window tabs rendering with inverted soft-divider caps and swapped colors whenever a window had a pending bell — most visibly when a Claude Code session rang the terminal bell on going idle — clearing only when you focused that window. tmux's default `window-status-bell-style` (and `window-status-activity-style`) is `reverse`, which inverts this status bar's per-tab colors; both are now set to `default`. No action needed beyond reloading tmux.
- **Fixed** truecolor never reaching the terminal under Ghostty. The old `terminal-overrides ",xterm-256color:Tc"` targeted `xterm-256color`, but the Ghostty client's TERM is `xterm-ghostty`, so tmux advertised no RGB capability and quantized colors to 256. Replaced with `terminal-features ",xterm*:RGB"`, matched against the real client TERM. Re-attach tmux (detach + `tmux attach`) or restart the server to pick it up.
- **Changed** `prefix + h` / `prefix + v` splits to open in the current pane's directory (`-c "#{pane_current_path}"`) instead of tmux's startup directory. No action needed.
- **Changed** `bootstrap.py` to back up an existing Claude Code `settings.json` to `settings.json.ORIGINAL` once before its first modification, and to write updates atomically (temp file + rename) so an interrupted run can't truncate it. Safe to `rm settings.json.ORIGINAL` if you don't want the backup.

## 2026-06-17
- **Added** `bin/claude-tmux-state` plus a Claude Code state-icon chain in `.tmux.conf`. Each tmux window tab now shows a small colored Nerd Font icon for what Claude Code is doing in that window — *working* (thinking or running a command) as a bolt that shifts cyan → orange once it passes 30s, *needs your input* (red question), *needs tool approval* (magenta lock), *waiting* on an external event (blue clock, opt-in), and a muted grey crescent when a session is present but idle; a window with no Claude session shows nothing. The glyph carries the category and the color carries the urgency. It's hook-driven (no polling, near-zero idle cost). **Activate:** reload tmux (`prefix + r` or `tmux source ~/.tmux.conf`) for the rendering, then run `./bootstrap.py` to merge the `claude-tmux-state` hooks into `~/.claude/settings.json` (idempotent; your other hooks are left untouched). Icons appear once you start a *new* Claude session. Tweak glyphs/colors via the `@CL_*` options near the top of the status-bar config. See README "Claude Code state icons in tmux".

## 2026-06-15
- **Fixed** `bin/claude-status` (Claude Code status line) reporting session duration as `<1min` forever on Linux — it derived elapsed time from a BSD-only `stat -f` call. Duration now comes from the status-line payload (`cost.total_duration_ms`) and is correct on all platforms.
- **Changed** `bin/claude-status` to show the real session cost (`cost.total_cost_usd`) instead of a guess from a hard-coded price table, render token counts to three significant figures with a k/m suffix (`1.25k`, `1.50m`), and label the working dir with the git branch *or* Sapling bookmark plus a live `+/-` diffstat. If your `~/.claude/settings.json` `statusLine` points at a custom script, set its command to `claude-status` to pick this up.
- **Added** `CLAUDE_STATUS_MONOREPOS` env var: space/comma-separated repo basenames whose deep paths collapse to `~/<repo>/.../<dir>` in the status line. Unset by default (no collapsing); set it in `~/.config/dotfiles/my_shell_profile.sh`.
- **Changed** `bin/ccopy`/`bin/cpaste` to work over SSH and inside tmux. Locally they still use the native clipboard tool, but on a remote host (or any session without a local clipboard) `ccopy` now emits an OSC 52 escape sequence so your *local* terminal's clipboard is updated — no X11 forwarding needed. Logic moved into `_pydotlib/clipboard.py` (unit-tested); the scripts are now thin Python wrappers. Also adds Wayland (`wl-copy`/`wl-paste`) and `xclip` support, a targeted tmux misconfig warning, mutually-exclusive `--native`/`--osc52` overrides, a `--clear` flag, richer `--help`, and the `CLIPBOARD_BACKEND` / `CLIPBOARD_PASTE_TIMEOUT_MS` env vars. Paste over SSH is best-effort (most terminals disable OSC 52 reads; tmux never forwards them) and fails fast with a hint. Minor behavior changes: `cpaste -h` now exits 0 (was 1); `ccopy` with no input on an interactive terminal prints usage instead of waiting on EOF; copying empty input is refused (it would clear the clipboard); `ccopy <text>` no longer appends a trailing newline (it copies the space-joined arguments verbatim, matching the byte-exact stdin/`-f` paths); `-V` now prints `--version` and verbose moved to `-v` (the old script used `-V` for verbose); WSL paste uses `powershell.exe` (was `pwsh`). See README "Clipboard".

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
