# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install/bootstrap (symlinks configs, sets up vim plugins, configures git author)
./bootstrap.py              # --dry-run and --verbose supported

# Install system packages (Homebrew on macOS, dnf on Redhat/Fedora)
# **THIS IS DEPRECATED, AND SHOULD BE MOVED TO BOOTSTRAP!**
./_setup.sh -p core         # -H flag for user-local Homebrew on macOS

# Lint all shell and Python files
python3 lint_all.py         # requires: shellcheck, uv (for ruff + ty)

# Run tests (unit tests + Docker integration tests)
python3 run_tests.py
```

## Architecture

### Shell Configuration Loading

The repo supports both **zsh** (primary) and **bash**. Both shells share vendor-neutral config modules in `shell_profile/`, while zsh-specific config lives in `zsh_files/`.

**Zsh load order:** `.zshenv` (sets `S_DOTFILE_ROOT`, loads `paths.sh`, `env.sh`) -> `.zshrc` (loads `xdg.sh`, then all `shell_profile/*.sh` modules, then `zsh_files/*.zsh`, then p10k/fzf/iterm2 integrations).

**Bash load order:** `.bash_profile` (sources `.bashrc`) -> `.bashrc` (loads all `shell_profile/*.sh` modules).

### Key Directories

- **`shell_profile/`** -- Vendor-neutral shell modules shared between bash and zsh: `paths.sh`, `env.sh`, `functions.sh`, `aliases.sh`, `xdg.sh`
- **`zsh_files/`** -- Zsh-only config (symlinked to `~/.zsh/`): keybindings, zsh functions
- **`sh/`** -- Shell script library (`cli.sh`, `git.sh`) sourced by bin scripts
- **`bin/`** -- Custom scripts added to `$PATH` via `shell_profile/paths.sh`
- **`settings/`** -- Editor/tool configs (nvim, VSCode, Ghostty, Wezterm, clang-format)
- **`_pydotlib/`** -- Python utility library used by `bootstrap.py`, `lint_all.py`, `run_tests.py`, and `bin/dotfiles`
- **`.vim/`** -- Vim runtime (colorschemes, ftplugins, spell files, native packages)

### Bootstrap System

`bootstrap.py` creates symlinks from repo files into `$HOME` and `~/.config/`. It uses `_pydotlib/bootstrap.py` for `safe_symlink()` which backs up existing files to `.ORIGINAL`. The repo root is identified by the `.__dotfiles_root__` marker file, and the environment variable `S_DOTFILE_ROOT` (defaults to `~/.dotfiles`) is used throughout all configs to locate the repo.

### Per-Machine Overrides

Local customizations (not checked in) are loaded from:
- `~/.config/dotfiles/my_shell_profile.sh` or `~/.my_shell_profile.sh` (post-load, both shells)
- `~/.config/dotfiles/0_my_shell_profile.sh` or `~/.0_my_shell_profile.sh` (pre-load, both shells)
- `~/.my_bashrc.sh`, `~/.my_zshrc.sh` (shell-specific post-load)
- `~/.my_gitconfig` (machine-specific git author name/email)

### Linting Rules

- Shell scripts are linted with `shellcheck` (SC1090 and SC1091 suppressed globally)
- Python files are type-checked with `ty` and linted with `ruff`, both invoked via `uvx`
- Linted paths: `shell_profile/`, `bin/`, `.bash_profile`, `.bashrc`, `_setup.sh`, `bootstrap.py`, `lint_all.py`

### Platform Detection

`shell_profile/functions.sh` provides `detect_os()` which sets `DOT_OS` (macos/linux/unknown), `DOT_DIST` (ubuntu/debian/redhat/fedora/darwin), and `DOT_ARCH`. Predicate functions (`is_osx`, `is_linux`, `is_wsl`, etc.) are available for platform-conditional logic.

### Conventions

- New shell scripts in `bin/` should source `$S_DOTFILE_ROOT/sh/cli.sh` for error handling helpers (`error()`, `exit_with_message()`, `set_verbose()`)
- The `mksh` script generates new shell scripts from a template
- Vim/Neovim share a single `init.vim` (at `settings/nvim/init.vim`) symlinked to both `~/.vimrc` and `~/.config/nvim/init.vim`
