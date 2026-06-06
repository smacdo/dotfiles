# Top Level Scripts
## Bootstrap
- [x] Replace occurrences of .dotfiles with a environment variable
- [x] Add option to cancel (skip) the backup/delete interactive prompt.
- Add a `choose()` helper in `_pydotlib/cli.py` for multi-option prompts (e.g. backup / skip / overwrite-without-backup). Then revisit `safe_symlink`'s prompt UX. Want to iterate on copy and option set.
- [x] Check if target exists, is a symlink and was symlinked somewhere in dotfiles repo for safe_symlink.
- download_file: Download to temporary location, and compare to dest. Prompt user if there is mismatch.
- [x] `initialize_vim_plugin_manager`: fixed silent no-op (`+'PlugInstall --sync'` → `-c "PlugInstall --sync" -c qa`); nvim's `plugged/` is now integration-checked. Vim has no `plug#begin` yet — add a vim-side check if that changes.
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
- [x] Install zsh, neovim in all test containers; add functional post-bootstrap checks (`zsh -ilc true`, `vim --not-a-term -c q`, `nvim --headless -c q`).
- [x] tmux config load check (`check_tmux_config`): `source-file` on a private `-L` socket (native + containers). Catches option drift across tmux versions; `-f conf` at startup was crash-only (swallows all config errors).
- tmux check follow-ups:
  - **Helper-script coverage.** `.tmux.conf` shells out to `bin/` scripts (`shostname`, `print-status os/ssh`, `tmux-right-status`). `source-file` does NOT catch a missing one — they're wrapped in `$(...)` inside `tmux set`, so the outer `tmux set` succeeds regardless. Add a separate check that these resolve on PATH (or a generic `bin/` smoke check).
  - **`source-file` blind spots.** It misses unterminated quotes and unmatched `#{` format braces (tmux validates formats lazily at render, not parse). If these bite, a render-time check would need an attached client (pty) — heavier.
- Integration test: bootstrap completes cleanly with **no** shells/editors installed. Today every test image bundles zsh/vim/nvim; need a "bare" image variant (e.g. `Dockerfile.<distro>.bare`) so we catch regressions where bootstrap silently relies on an optional binary being present.
- Integration test: post-bootstrap "actually works" coverage when shells/editors are installed. bash/zsh should run a representative command cleanly; nvim is expected to *partially* work (init.vim loads, but `:PlugInstall` hasn't been run so plugins are absent). Decide what's worth asserting beyond "loads and quits".
- Integration test: meaningful vim/nvim init validation. Today's `vim -e -s -c q` and `nvim --headless -c q` are crash-only — both silently swallow init errors in Ex/headless mode (verified: a `.vimrc` containing `call ThisFunctionDoesNotExist()` still exits 0 with no output). Real detection works via `vim -u NONE -es -c 'try | source ~/.vimrc | catch | cq | endtry' -c q`, but our real `init.vim`'s vim path errors when plugins aren't installed. Need either (a) wire `:PlugInstall` into the test fixture so plugin-dependent code paths can be exercised, or (b) split `init.vim` so the no-plugin path is independently testable.
- [x] Idempotency: container tests now re-run bootstrap a second time and assert rc=0 (`run_tests.py:run_container_test`). Catches "symlink-already-exists", "download overwrites valid state", "interactive prompt fires on re-run".
- Idempotency, stricter: after the second bootstrap run, also assert no fresh writes happened (e.g., diff the FS state pre/post second run, or check bootstrap's stdout for "creating/downloading" markers). The exit-code check catches crashes but not silent re-work.
- Upgrade-path tests under `tests/docker/upgrade_from_v<N>/`: pre-populate the prior-layout state, run bootstrap, assert clean completion + new artifacts exist in their new homes. See CLAUDE.md "Migration / backwards-compat policy".
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

## Shell Profile Minor Issues (from code review)

- **`env.sh:44-47` `/usr/bin/lesspipe` (no `.sh`) handled per-shell, not in shared env.sh**: env.sh
  only checks the `lesspipe.sh` variants; Debian/Ubuntu's `/usr/bin/lesspipe` is handled separately in
  `.bashrc` and `.zshrc` via `eval "$(lesspipe)"`. Works (no real conflict), but the logic is
  duplicated across three files. Consolidate into env.sh if it ever drifts. (Left as-is intentionally.)

# Misc
- [x] Github action to run linter
- [x] Github action to run tests

# CI workflow improvements

- Container runtime decay coverage: add a SINGLE extra integration job pinned to the non-default runtime (e.g. `--runtime docker` while auto-detect prefers podman). Catches "we silently regressed to runtime-X-only" without doubling CI cost. Don't full-matrix runtime×distro — overkill for what's basically a regression-detection problem.
- Secret scanning: add `gitleaks-action` (or equivalent) on every PR. Enforces the confidentiality clause in CLAUDE.md. Should be one-line addition to the workflow.
- Cache `uv` install: `actions/cache` on `~/.cache/uv`. Saves ~20s/run, basically free.
- Markdown link checker (e.g. `lychee-action`) on `README.md`, `CHANGELOG.md`, `TODO.md`. Catches link/file rot.
- Performance budget: emit unit-test runtime + image build time as job summary. Visibility-only, no fail threshold. Defer until something starts feeling slow.
- Coverage report: `coverage.py` run + summary. Visibility-only, no threshold. Helps spot under-tested modules.
- macOS partial-bootstrap test: GHA `macos-latest` runs only lint+unit today. Real macOS code paths (`is_osx`, `pmset`, `pbcopy/pbpaste`, sysctl parsing) have zero coverage. Approach: run `python3 bootstrap.py --dry-run` on the macOS runner to exercise platform-detected orchestration without modifying the runner's `$HOME`. Requires bootstrap's `--dry-run` to be trustworthy (already is for symlinks/dirs; verify for downloads/clones too). Bonus: `-h` smoke-test on every `bin/` script.
- CHANGELOG enforcement (deferred — needs design): a CI check that fails if a PR touches `bootstrap.py` / `_pydotlib/bootstrap.py` substantively without adding a `CHANGELOG.md` line. Problem: not every change is user-visible (lint fix, internal refactor, comment-only). Options: (a) require manual opt-in/out via PR-description tag like `[no-changelog]`; (b) heuristic on which files changed (brittle); (c) skip automation, rely on CLAUDE.md policy + reviewer discipline. (c) is fine for a solo repo; revisit if oversight happens.
- Python version matrix (deferred — likely not needed): could matrix-test 3.10/3.11/3.12/3.13 on the unit job. Counterpoint: the docker integration job already exercises whatever Python ships on debian/fedora/ubuntu (currently 3.11–3.13), which covers the "does it actually run on my machines" question more honestly than a synthetic matrix. Skip unless we adopt new-version-only syntax.

# Tools (`tools/`)

## VS Code installer
- Add macOS support (`brew install --cask visual-studio-code`). Currently Linux-only (Debian/Ubuntu, Fedora/RHEL/CentOS). On WSL, VS Code is installed on the Windows side and accessed via Remote — no Linux install needed.

# Bin Scripts
- Script that line breaks excessively long command lines
- backup: Simple script that creates foo.bak_N while avoiding race conditions
- mksh:
  - source the author name for an dotfile envvar $S_DEFAULT_AUTHOR
