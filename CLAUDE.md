# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Confidentiality

This is a personal, publicly-visible repository. It must never contain proprietary or confidential information from any employer, past or present. When generating, editing, or copying content into this repo, refuse to include:

- Source code, configs, or documentation from internal repositories
- Secrets, credentials, tokens, API keys, or private SSH/GPG material
- Internal hostnames, URLs, network topology, or infrastructure details
- Names of internal tools, services, systems, or codenames
- Internal repository paths, build targets, or directory layouts
- Project codenames, team names, or org structure
- Coworker names, employee usernames, or internal contact info
- Customer, employee, or business data of any kind

If a task would require committing any of the above, stop and warn the user before writing anything to disk. For machine- or work-specific content that legitimately needs to exist locally, use the per-machine override files (`~/.config/dotfiles/`, `~/.my_*`) or a gitignored `CLAUDE.local.md` — never the tracked repo.

### Enforcement

Before writing any file, staging changes, or creating a commit in this repo, audit the diff against the rules above. If anything matches — even ambiguously — you must:

1. **Stop.** Do not write, stage, or commit.
2. **Show the exact violation.** Quote the offending lines with file path and line number, and name which category they fall under.
3. **Wait for explicit permission.** Do not proceed on implicit consent or general task approval. The user must explicitly say to include the flagged content.

This check applies to every write, not just commits — content can leak through `Write`, `Edit`, generated scripts, comments, commit messages, and PR descriptions alike. Err on the side of flagging: a false positive costs a sentence; a false negative is unrecoverable once pushed.

## Commands

```bash
# Install/bootstrap (symlinks configs, sets up vim plugins, configures git author)
./bootstrap.py              # --dry-run and --verbose supported

# Install system packages (Homebrew on macOS, dnf on Redhat/Fedora)
# DEPRECATED — should be moved into bootstrap.py
./_setup.sh -p core         # -H flag for user-local Homebrew on macOS

# Lint all shell and Python files
python3 lint_all.py         # requires: shellcheck, uv (for ruff + ty)

# Run unit tests + Docker integration tests
python3 run_tests.py
```

## Workflow

- **Run `python3 lint_all.py` after any change** to a shell script, Python script, or config file (`shell_profile/`, `zsh_files/`, `bin/`, `.bashrc`, `.zshrc`, `.bash_profile`, `_setup.sh`, `bootstrap.py`, `lint_all.py`).
- **Run `python3 lint_all.py` before every commit.** Do not commit if lint fails.
- Run `python3 run_tests.py` after changes to `bootstrap.py` or `_pydotlib/`.

### What lint_all.py checks

- Shell scripts: `shellcheck` (SC1090, SC1091 suppressed globally)
- Python files: `ty` (type checking) + `ruff` (linting), both via `uvx`
- `.bashrc` and `.zshrc`: no content after the end-of-config sentinel line

## Architecture

### Shell Configuration Loading

Supports **zsh** (primary) and **bash**. Shared vendor-neutral modules live in `shell_profile/`; zsh-specific config in `zsh_files/`.

**Zsh:** `.zshenv` (sets `S_DOTFILE_ROOT`, loads `paths.sh`, `env.sh`) → `.zshrc` (loads `xdg.sh`, all `shell_profile/*.sh`, all `zsh_files/*.zsh`, then p10k/fzf/iterm2)

**Bash:** `.bash_profile` (sources `.bashrc`) → `.bashrc` (loads all `shell_profile/*.sh`)

### Key Directories

- **`shell_profile/`** — Vendor-neutral modules shared by bash and zsh: `paths.sh`, `env.sh`, `functions.sh`, `aliases.sh`, `xdg.sh`
- **`zsh_files/`** — Zsh-only config (symlinked to `~/.zsh/`): keybindings, zsh functions
- **`bin/`** — Custom scripts on `$PATH` via `shell_profile/paths.sh`
- **`settings/`** — Editor/tool configs (nvim, VSCode, Ghostty, Wezterm, clang-format)
- **`_pydotlib/`** — Python utility library used by `bootstrap.py`, `lint_all.py`, `run_tests.py`, and `bin/`
- **`.vim/`** — Vim configs (colorschemes, ftplugins, spell files, native packages)
- **`sh/`** — Deprecated shell library (`cli.sh`, `git.sh`); new scripts should use Python

### Bootstrap System

`bootstrap.py` creates symlinks from repo files into `$HOME` and `~/.config/`. Uses `_pydotlib/bootstrap.py`:`safe_symlink()`, which backs up existing files to `.ORIGINAL`. The repo root is identified by `.__dotfiles_root__`; `S_DOTFILE_ROOT` (defaults to `~/.dotfiles`) is used throughout configs to locate the repo.

### Per-Machine Overrides

Not checked in. Loaded automatically at shell startup:
- `~/.config/dotfiles/my_shell_profile.sh` or `~/.my_shell_profile.sh` — post-load, both shells
- `~/.config/dotfiles/0_my_shell_profile.sh` or `~/.0_my_shell_profile.sh` — pre-load, both shells
- `~/.my_bashrc.sh`, `~/.my_zshrc.sh` — shell-specific post-load
- `~/.my_gitconfig` — machine-specific git author name/email

### Platform Detection

`shell_profile/functions.sh`:`detect_os()` sets `DOT_OS` (macos/linux/unknown), `DOT_DIST` (ubuntu/debian/redhat/fedora/darwin), and `DOT_ARCH`. Predicate helpers: `is_osx`, `is_linux`, `is_wsl`, etc.

## Conventions

- New shell scripts must use the skeleton from `bin/mksh`:
  ```sh
  #!/bin/sh
  #==============================================================================#
  # Author: Scott MacDonald
  # Purpose: <description>
  # Usage: ./<script_name>
  #==============================================================================#
  # vim: set filetype=sh :
  set -e
  set -u

  # shellcheck disable=SC3040
  (set -o pipefail 2> /dev/null) && set -o pipefail
  ```
- Shell scripts use POSIX sh, not bash
- Non-trivial scripts should be Python; Python scripts use only builtin modules
- Do not source `sh/cli.sh` (deprecated) — define helpers inline
- Vim/Neovim share `settings/nvim/init.vim`, symlinked to both `~/.vimrc` and `~/.config/nvim/init.vim`
