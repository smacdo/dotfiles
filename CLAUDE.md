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

# Lint all shell and Python files
python3 lint_all.py         # requires: shellcheck, uv (for ruff + ty)

# Run unit tests + Docker integration tests
python3 run_tests.py
```

## Workflow

- **Always run `python3 lint_all.py` after finishing a change and before every commit.** Do not commit if lint fails. (`lint_all.py` discovers files itself — no need to track which paths it covers.)
- Run `python3 run_tests.py` after changes to `bootstrap.py` or `_pydotlib/`.
- If your environment routes external HTTP through a forward proxy, set `HTTP_PROXY` and `HTTPS_PROXY` in a per-machine override (e.g., `~/.config/dotfiles/my_shell_profile.sh`) before running `lint_all.py` or `bootstrap.py`. `uv` and `pip` honor those env vars; without them, package fetches will fail with DNS errors.

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
- **`_pydotlib/`** — Python utility library for repo scripts (top-level `bootstrap.py`, `lint_all.py`, `run_tests.py`, and `tools/`). See *`bin/` script policy* below for when `bin/` scripts may use it.
- **`.vim/`** — Vim configs (colorschemes, ftplugins, spell files, native packages)
- **`tools/`** — Post-bootstrap install scripts for external dependencies (Nerd Fonts, uv, p10k, VS Code)
- **`tests/docker/`** — Container-based integration tests exercising `bootstrap.py` on debian/ubuntu/fedora/alpine. `Dockerfile.<flavor>` per distro; post-bootstrap verification lives in `_pydotlib/integration_checks.py`. See *Integration test policy* below.
- **`vendor/`** — Vendored third-party shell integrations (iterm2, bash, zsh completions); do not edit
- **`fonts/`** — Local font files installed by `tools/install_nerd_fonts.sh`

### Bootstrap System

`bootstrap.py` creates symlinks from repo files into `$HOME` and `~/.config/`. Uses `_pydotlib/bootstrap.py`:`safe_symlink()`, which backs up existing files to `.ORIGINAL`. The repo root is identified by `.__dotfiles_root__`; `S_DOTFILE_ROOT` (defaults to `~/.dotfiles`) is used throughout configs to locate the repo.

### Per-Machine Overrides

Not checked in. Loaded automatically at shell startup:
- `~/.config/dotfiles/my_shell_profile.sh` or `~/.my_shell_profile.sh` — post-load, both shells
- `~/.config/dotfiles/0_my_shell_profile.sh` or `~/.0_my_shell_profile.sh` — pre-load, both shells
- `~/.config/dotfiles/my_bashrc.sh` or `~/.my_bashrc.sh` — bash-specific post-load
- `~/.config/dotfiles/my_zshrc.sh` or `~/.my_zshrc.sh` — zsh-specific post-load
- `~/.my_gitconfig` — machine-specific git author name/email

### Platform Detection

`shell_profile/functions.sh`:`detect_os()` sets `DOT_OS` (macos/linux/unknown), `DOT_DIST` (ubuntu/debian/redhat/fedora/darwin), and `DOT_ARCH`. Predicate helpers: `is_osx`, `is_linux`, `is_wsl`, etc.

**Supported platforms.** This repo targets recent versions of macOS, Windows (via WSL), and the Linux distros Red Hat / Fedora / Debian / Ubuntu. Don't add branches for distros outside that list (Arch, openSUSE, Alpine for runtime use, etc.) — file a TODO instead. Also skip platforms where a feature doesn't make sense (e.g., installing VS Code under WSL — users install it on the Windows side and connect via Remote).

## Policies

### `bin/` script policy

Scripts in `bin/` should be **portable** — written so someone could copy a single file out of this repo into their own setup and have it work. That means:

- Default to standalone: no imports from `_pydotlib/` or other repo-local modules.
- Short commands and one-liners may be POSIX sh; reach for Python once logic is non-trivial. Python scripts use only the standard library (no `pip` deps).
- Only reach for `_pydotlib/` when 2+ `bin/` scripts share genuinely non-trivial logic (e.g., weather data fetching, shared logging setup). One-off helpers belong inline in the script.
- When in doubt, duplicate a few lines rather than introducing a shared dependency — readability and portability beat DRY here.

Naming and form:

- **No file suffixes** (`.py`, `.sh`) — invoke as `weather`, not `weather.py`. Use a shebang to declare the interpreter.
- **Kebab-case** filenames (`next-meeting`, not `next_meeting` or `nextMeeting`).
- **Always `chmod +x`** — scripts must be directly executable from `$PATH`.

### Integration test policy

Container integration tests live in `tests/docker/` plus
`_pydotlib/integration_checks.py`. The runner (`run_tests.py`) builds one
container per `tests/docker/Dockerfile.<flavor>`, execs `bootstrap.py`
inside it, then runs the Python check suite from
`integration_checks.BOOTSTRAP_CHECKS`.

Rules for `_pydotlib/integration_checks.py`:

- **Must NOT import from `_pydotlib.bootstrap`** (or any other module the
  tests are validating). It only observes container state via a provided
  `exec_fn` plus stdlib types. The reason: checks must reflect what an
  external observer sees, not what the implementation thinks it did.
- **Each check is a pure function `(exec_fn: ExecFn) -> CheckResult`.**
  Use the `check_symlink` / `check_dir_exists` / `check_file_contains`
  helpers as templates when adding new ones. A check returns a
  `CheckResult` with a descriptive `name` and (on failure) a `detail`
  string showing expected vs. actual.
- **Register new checks in `BOOTSTRAP_CHECKS`** — that's the canonical
  post-bootstrap suite the runner iterates.
- **Add unit tests in `_pydotlib/tests/test_integration_checks.py`** for
  every new check function. Mock `exec_fn` with `MagicMock` returning
  crafted `subprocess.CompletedProcess` values; cover the pass path and
  each distinct failure path.

Rules for `tests/docker/`:

- One `Dockerfile.<flavor>` per distro, flat in `tests/docker/`. No
  per-target subdirectory. Container user is `testuser`; repo is
  read-only mounted at `/home/testuser/.dotfiles`.
- New distros: drop in `Dockerfile.<name>` and the runner picks it up
  automatically via `discover_flavors()`. Match the existing
  Dockerfiles' shape (install `git python3`, create `testuser`,
  `USER testuser`, `WORKDIR /home/testuser`).

### Top-level docs

- `README.md` — public-facing setup/forking guide; don't duplicate setup steps from CLAUDE.md here.
- `NOTES.md` — personal scratch notes; don't reorganize without asking.
- `TODO.md` — personal backlog; confirm before checking off items unless the user explicitly tasked you with addressing a TODO.

## Conventions

- New shell scripts: generate from `bin/mksh <name>` (POSIX sh skeleton with `set -eu` and pipefail).
- `.bashrc` and `.zshrc` have an end-of-config sentinel line; never add content below it (lint enforces this).
- Vim/Neovim share `settings/nvim/init.vim`, symlinked to both `~/.vimrc` and `~/.config/nvim/init.vim`.
