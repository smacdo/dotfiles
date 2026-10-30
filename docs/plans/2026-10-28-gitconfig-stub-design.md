# Design: `~/.gitconfig` as a local stub

**Status:** short design, revised after design review rounds 1 and 2; approved 2026-10-29 (captured 2026-10-28).
**Goal:** Tools that write to `~/.gitconfig` (`git config --global`, credential-helper setup,
login-time setup scripts) write to an untracked local file instead of the tracked, public
repo `.gitconfig`, while shared settings still come from the repo. `~/.my_gitconfig` folds
into that local file, so there is one place for per-machine git settings.

## Why

`~/.gitconfig` is a symlink into the repo, so every `git config --global` writes into the
tracked file. On work devservers a login-shell hook rewrites cert/proxy settings on every
login (it checks with `git config --global --get`, which ignores `[include]`, so it never sees
the copies in `~/.my_gitconfig`), and a file-sync tool then spreads the newest copy between
machines. Cleaning the tracked file does not stick. This is the `.gitconfig` slice of the
"stub files instead of symlinks" item in `TODO.md`; `.bashrc`/`.zshrc` stay there.

## Goals / non-goals / anti-goals

- **Goals:** tool writes land locally; repo settings still apply everywhere; one local file for
  per-machine git settings; bootstrap migrates existing installs without data loss; idempotent.
- **Non-goals:** `.bashrc`/`.zshrc`/`.profile` stubs; a generic stub installer (see Decisions);
  cleaning other machines' files beyond what bootstrap or the sync tool does on its own.
- **Anti-goals:** a failure mode that silently writes into the repo again; losing a user's
  existing `~/.gitconfig` or `~/.my_gitconfig` content; a recursive include that breaks git.

## Approaches considered

1. **Local stub with `[include]` of the repo file (chosen).** Fails safe: if the stub is
   deleted, git creates a fresh local file (repo settings visibly missing, nothing leaks).
2. **Repo file at `~/.config/git/config`, `~/.gitconfig` a plain local file.** No include, but
   if `~/.gitconfig` ever goes missing, `git config --global` writes to the XDG file, i.e. the
   repo again. Fails unsafe (confirmed in review).
3. **Keep the symlink, set `GIT_CONFIG_GLOBAL`.** Only applies where the shell profile ran;
   login hooks run before user rc files and would still write through the symlink.

## Decisions

**Stub content.** Comment header, then the include, so anything below overrides repo settings
(git applies later values last):

```
# Local git config for this machine. Not tracked: tools such as `git config --global`
# write here, and so can you. Shared settings come from the dotfiles repo via the include.
[include]
	path = ~/.dotfiles/.gitconfig
```

The include path is written as `~/...` whenever the repo `.gitconfig` resolves to the same file
as `~/<relative path>`, trying the path relative to `Path.home()` and to `Path.home().resolve()`
(compare resolved paths, so a symlinked home or checkout still gets the
portable form, which matters because the stub syncs to other machines); otherwise absolute.
Precedence: repo settings, then everything in the stub.

**Hermetic git helper.** Bootstrap inspects config files by running git with a clean
environment: `HOME=<stub dir>`, `GIT_CONFIG_GLOBAL=/dev/null` (git 2.32+; older git falls back
to `HOME` isolation alone), `GIT_CONFIG_NOSYSTEM=1`, `XDG_CONFIG_HOME` unset. That keeps a broken or self-including global config from breaking the
check, and keeps tests from touching the real home. Uses:
- `_gitconfig_includes(path, repo_file) -> bool`: `git config --file <path> --type=path
  --get-all include.path` (handles case-insensitive names, inline comments, `~`, and multiple
  values); relative entries resolved against the file's directory; compared with `resolve()`.
- Post-write validation: `git config --file <stub> --includes --list` must succeed (catches
  cycles and syntax errors) **and** `_gitconfig_includes(stub, repo_file)` must be True (git
  silently ignores a missing include file). Runs on every branch that leaves a stub, including
  the one that writes nothing.

**Bootstrap: `install_gitconfig_stub(stub_path, repo_gitconfig, legacy_local, dry_run) -> StubResult`**
in `_pydotlib/bootstrap.py`, replacing the `.gitconfig` entry in the symlink list and running
before `configure_vcs_author`. `StubResult` is an enum: `READY` (a regular stub that includes
the repo file), `SKIPPED` (user declined, or a foreign/broken symlink: bootstrap carries on but
skips `configure_vcs_author`), `FAILED` (recursion guard or validation failure: `bootstrap.py`
exits non-zero before any later git-dependent step).

0. **Recursion guard first:** if `_gitconfig_includes(repo_gitconfig, repo_gitconfig)`, log an
   error with the working fix (`GIT_CONFIG_GLOBAL=/dev/null git -C <repo> checkout --
   .gitconfig`), make no changes, and return `FAILED`.

| `~/.gitconfig` is | Action |
|---|---|
| missing | write the stub |
| a symlink to the repo `.gitconfig` | replace with the stub (the symlink holds no data) |
| a regular file that already includes the repo file | leave it, except for the legacy fold-in below |
| a regular file without the include | prompt (default yes, like `safe_symlink`); on yes, convert as below; on no, return `SKIPPED` |
| a symlink elsewhere, or a broken symlink | warn, leave it, return `SKIPPED` |

- **Converting a regular file** (interruption-safe order): read the old content;
  `shutil.copy2` it to the `.ORIGINAL` backup (`create_backup_filename`); render the stub with
  the old content appended; atomically `os.replace` it over `~/.gitconfig`. Every appended block
  is separated by a newline even if its source lacks a trailing one.
- **Legacy fold-in** (any branch that leaves a regular stub): fold `legacy_local` when it
  exists and the stub has no line `# migrated from ~/.my_gitconfig sha256=<H>` where `<H>` is
  the SHA-256 of the legacy file's current bytes. Folding appends that marker line followed by
  the file's content, after a prompt (default yes). A content hash, not a plain marker or a
  settings comparison: a stub synced from another machine carries a different hash, so this
  machine still folds its own file; and later rewrites of folded values (identity updates,
  login-hook `--replace-all`) don't change the hash, so they never trigger a re-fold that would
  resurrect old values. If the legacy file itself changes later, it is folded again (a new
  block, last wins), which is the desired behavior for a file the user edited. When converting
  an old `~/.gitconfig` that already includes `~/.my_gitconfig`, the legacy content is still
  folded (with its marker) and the now-redundant include line is left in place (it is
  harmless and removed by nobody). Never deletes the legacy file.
- **Legacy log line:** while `~/.my_gitconfig` exists and its current hash is marked in the
  stub, log one quiet line that it is no longer used and `bin/dotfiles-cleanup` can remove it.
- **Backups and validation:** every write to an existing regular `~/.gitconfig` (conversion or
  fold-in) first copies it to a `.ORIGINAL` backup via `create_backup_filename`. After any
  write, post-write validation must pass; on failure, restore the previous file (from that
  backup, or recreate the prior symlink), log the error, and return `FAILED`.
- Writes are atomic; every branch honors `--dry-run` and logs one line.
- Structure for later reuse: git-specific parts stay in `_render_gitconfig_stub(include_path)
  -> str` and the helpers above, so the `.bashrc`/`.zshrc` follow-up can extract a generic
  installer once its own open questions are answered. No generic API now.

**`configure_vcs_author`** targets `~/.gitconfig` and runs only when `install_gitconfig_stub`
returned `READY`. It also refuses on its own if the path `is_symlink()` (defense in depth), so it
can never turn a foreign symlink into a regular file or create a broken link's target.
`bootstrap.py`'s `MY_GITCONFIG_PATH` and `--git-name`/`--git-email` help text change to match.

**Repo `.gitconfig`** drops its trailing `[include] path = ~/.my_gitconfig`. Both commits ship
together: there are no forks, and the only gap (a machine that pulls before re-running
bootstrap shows "Please tell me who you are") is closed by re-running bootstrap right after
pulling.

**Committing the repo `.gitconfig` change** starts from a clean copy of the file: the working
copy on this devserver contains injected work-internal sections. Run
`git checkout -- .gitconfig` (or stage only the include-removal hunk with `git add -p`) before
editing/committing, then audit `git diff --cached` per the repo's confidentiality policy.

**`bin/dotfiles-cleanup`** (new, POSIX sh from `bin/mksh`, per the migration policy): lists
known orphaned paths, starting with `~/.my_gitconfig`, and removes each only after a per-path
confirmation; with no TTY the answer defaults to no. Skips paths that don't exist; `--dry-run`
prints what it would remove. For `~/.my_gitconfig` it refuses unless `~/.gitconfig` contains the marker line
with the legacy file's current SHA-256 (`sha256sum` on Linux, `shasum -a 256` on macOS), and
says to re-run bootstrap otherwise.

**This devserver after migration.** Bootstrap never edits the repo file. Afterwards the user
first checks `git diff .gitconfig` and copies anything worth keeping into `~/.gitconfig`, then
runs `git checkout -- .gitconfig` once to drop the injected sections from the working copy.
Until the login hook next runs (re-login), its cert settings may be missing from the effective
config.

**Other devservers and the sync tool (verified from its source).** The sync tool syncs both
the `~/.gitconfig` path and the repo directory, and stores symlinks as link entries (no content
captured twice). On pull, an incoming regular file *replaces* a local symlink: the copy path
removes a destination symlink before copying, and the rename path uses rename(2), which never
follows a destination symlink. It never writes through. It overwrites only when the local copy
is unchanged since the last sync; when both sides changed, the local copy stays and the remote
one goes to a conflicts directory. So after migrating one devserver, the stub reaches the
others on their next sync without running bootstrap there, and the repo `.gitconfig` is never
overwritten by the stub. The synced stub carries this machine's folded identity, which is
intended (same identity on all synced machines). Note that the stub is therefore shared, not
per-machine, across the sync group: the last machine to fold or edit it wins everywhere. That
is acceptable here because those machines share an identity and cert settings. Rollout spot-check on one other devserver
after the next sync: `~/.gitconfig` is a regular file with the include; `git config user.name`
works; `git -C ~/.dotfiles status --short .gitconfig` is clean; the sync tool's conflicts
directory holds nothing for these paths. A later bootstrap run there folds that machine's own
`~/.my_gitconfig` if it differs.

**Docs.** CHANGELOG entry: `~/.gitconfig` is now a local stub and `~/.my_gitconfig` is folded
into it; re-run bootstrap right after pulling (machines that receive the change by file sync
need no action if their `~/.my_gitconfig` matches the one folded in; otherwise re-run bootstrap
there to fold in their own); first check `git diff .gitconfig` and copy anything worth keeping
into `~/.gitconfig`, then `git checkout -- .gitconfig`; the old file is removable via the opt-in
`bin/dotfiles-cleanup`, which asks before removing. CLAUDE.md: "Bootstrap System" and
"Per-Machine Overrides" (drop `~/.my_gitconfig`, add `~/.gitconfig`); migration policy step 5 names the runner's pre-seed
mechanism instead of `tests/docker/upgrade_from_v<N>/` (which conflicts with the flat
`tests/docker/` rule). README references. `TODO.md`: stub item narrowed to `.bashrc`/`.zshrc`
with a note that the stub logic is ready to extract; "move `~/.my_gitconfig` into XDG" removed
as obsolete; the `bin/dotfiles-cleanup` item updated to point at the new script.

## Testing

All tests that run git use the hermetic environment above (`HOME=<tmp>`,
`GIT_CONFIG_NOSYSTEM=1`, `XDG_CONFIG_HOME` unset).

- `_pydotlib/tests/test_bootstrap.py`, new `TestInstallGitconfigStub`: one test per table row;
  idempotency (second run is a no-op); dry-run (nothing written); declined prompt (file
  untouched); `~` vs absolute include path, including a symlinked home; appended content
  preserves every original line and newline separation; interruption order (backup exists
  before the original is replaced); legacy fold-in when entries are missing, skipped when
  marked with the current hash, still performed when the stub carries another machine's
  marker (different hash), not repeated after `configure_vcs_author` or a `--replace-all`
  rewrites a folded value (old values are not resurrected; second run is a no-op), and repeated
  once when the legacy file itself changes; recursion guard returns `FAILED` with no changes;
  validation failure (cycle, or include path pointing at a missing file) restores the previous
  file from the backup; declined prompt and foreign symlink return `SKIPPED`.
- `configure_vcs_author`: new target path; leaves a foreign symlink and a broken symlink
  untouched (no file created at the link target).
- `bin/dotfiles-cleanup`: shellcheck via `lint_all.py`; manual runs: path absent, unfolded
  hash marker missing or stale (refuses), current marker (prompts), no TTY (defaults to no).
- Integration: `build_native_checks` and `BOOTSTRAP_CHECKS` replace `check_symlink(~/.gitconfig)`
  with `check_command_output_matches(["git", "config", "--global", "--includes", "--get",
  "log.date"], "relative")` (proves the include resolves; `log.date` is defined only in the repo
  file). The two existing `~/.my_gitconfig` content checks repoint to `~/.gitconfig`.
- Upgrade path: the runner pre-seeds (in every flavor) `~/.gitconfig` as a symlink to the repo
  file and a `~/.my_gitconfig` containing a sentinel key (`[dotfilestest] migrated = yes`;
  `--git-name` would overwrite a seeded identity). Checks: the sentinel resolves from
  `~/.gitconfig`, and `~/.my_gitconfig` still exists. A second seeded line uses a key that
  `configure_vcs_author` rewrites (`user.name`), so the runner's second bootstrap pass proves
  no re-fold resurrects the old value. Unit tests cover the
  fresh-install row. The read-only repo mount makes any write-through bug fail loudly.
- Manual on this devserver: after bootstrap, a tool-style write
  (`git config --global http.https://example.invalid.proxy ""`) lands in the stub, not the repo.

## My calls (flag any you disagree with)

- Reuse the runner's pre-seed mechanism instead of a new `tests/docker/upgrade_from_v<N>/` tree,
  and update the CLAUDE.md migration policy to say so.
- Prompt before converting an existing regular `~/.gitconfig`, matching `safe_symlink`.
- `bin/dotfiles-cleanup` ships minimal: one stanza, per-path confirmation, `--dry-run`.

## Changes from design review (round 1)

All made as my calls; none changes a decision you made.
- `configure_vcs_author` gated on the stub result and refuses symlinks (review #1).
- Legacy fold-in by content comparison in every regular-stub branch, plus a cleanup guard
  (review #2; the review's marker-based fix would skip machines that received a synced stub).
- Recursion guard: working recovery command, bootstrap exits non-zero, plus general post-write
  validation (review #3).
- Clean-copy-then-audit step for the repo `.gitconfig` commit (review #4).
- Suggestions adopted: hermetic git parsing; interruption-safe conversion order; resolved-path
  `~` detection; sentinel-based upgrade test on one flavor; drop the exact-text include check;
  test hermeticity; extended spot-check; CHANGELOG wording for synced machines; CLAUDE.md policy
  text; legacy log line; cleanup defaults to no without a TTY.

## Changes from design review (round 2)

All made as my calls; none changes a decision you made.
- Fold-in detection switched from a settings-subset comparison to a content-hash marker, which
  stops repeated re-folds that resurrected old values (review 2, critical). Cleanup uses the
  same marker.
- `install_gitconfig_stub` returns an enum (`READY`/`SKIPPED`/`FAILED`) so declines don't fail
  bootstrap but guard and validation failures do.
- Validation also checks the include resolves to an existing repo file and runs on the
  no-write branch; fold-ins back up first.
- Legacy-include conversion rule made consistent with the marker; doc notes the synced stub is
  shared across the sync group; home-path candidates and the git 2.32 note spelled out.
- Tests extended to cover rewrite-then-rerun and a CI seed key that bootstrap rewrites.
