VERDICT: NEEDS_REVISION

## Summary Assessment

The stub-plus-include architecture is sound, and the git semantics it relies on check out against real git. Four gaps need fixing before implementation. Three are in bootstrap's handling of states the table doesn't fully cover. The fourth is a commit-sequencing risk on the public `.gitconfig`.

## Critical Issues (must fix)

### 1. `configure_vcs_author` will undo the "warn and leave it" rows and can write into the repo

Today `configure_vcs_author` targets `~/.my_gitconfig`, which is never a symlink. Pointed at `~/.gitconfig`, it runs after `install_gitconfig_stub` on every branch, including the ones the table says to leave alone:

- **Symlink elsewhere:** `update_git_config_file` writes a temp file and `os.replace`s it over the path. That replaces the user's symlink with a regular-file copy, with no backup and no prompt. This contradicts both "warn and leave it" and `safe_symlink`'s "never overwrite without a backup".
- **Broken symlink:** `gitconfig_path.exists()` is False for a dangling link, so `write_text` follows the link and creates its target. If the link points at an old path inside the repo (after a file moves within the repo), this creates a new untracked file in the working tree containing `[user]` name/email. The sync tool then copies it everywhere, and one `git add -A` would commit it. That hits the "silently writes into the repo" anti-goal.
- **Recursion guard fired ("make no changes"):** `configure_vcs_author` still reads through the symlink and `os.replace`s it. The result is a half-migrated regular file that still includes the self-including repo file.

Fix: `install_gitconfig_stub` returns whether `~/.gitconfig` is now a regular file it manages. `configure_vcs_author` runs only in that case, or refuses symlinks itself via `is_symlink()`. Add unit tests for the symlink-elsewhere and broken-symlink rows that assert `configure_vcs_author` leaves them untouched.

### 2. The "already migrated" row silently drops other machines' `~/.my_gitconfig`, and that row is the default path on every other devserver

Per the updated rollout section, the stub reaches other devservers by sync, not by bootstrap. That stub contains *this* machine's folded `~/.my_gitconfig`. On every other machine:

- Bootstrap later sees "a regular file that already includes the repo file" and leaves it alone, so that machine's own `~/.my_gitconfig` is never folded in.
- The repo `.gitconfig` no longer includes `~/.my_gitconfig`.
- So any machine-specific content in it stops applying, with no log line. The design says one machine holds cert settings there, so if that isn't this devserver, they vanish.
- `bin/dotfiles-cleanup` then offers to delete the file.

The file stays on disk, but its content stops applying. That is the "losing a user's existing `~/.my_gitconfig` content" anti-goal in practice.

Fix: in the already-migrated branch, if `legacy_local` exists and the stub lacks the `# migrated from ~/.my_gitconfig` marker, act on it: fold it in (with the same prompt as the regular-file row) or log a warning naming the file. Also make `bin/dotfiles-cleanup` check for that marker in `~/.gitconfig` and refuse or warn before removing `~/.my_gitconfig` without it.

### 3. The recursion guard's named fix does not work, and the guard doesn't stop later steps

I tested this with real git (a temp `HOME`, a repo `.gitconfig` overwritten with stub content, `~/.gitconfig` a symlink to it). Every git command fails with:

```
fatal: exceeded maximum include depth (10) while including
	<repo>/.gitconfig
from
	<repo>/.gitconfig
This might be due to circular includes.
```

The failing commands include `git status`, `git checkout -- .gitconfig`, `git config --global --get`, `git config --file <other>`, `git clone`, and (on the 2.53 build tested) `git --version`. So the error message's fix, `git checkout -- .gitconfig`, fails the same way. What worked: `GIT_CONFIG_GLOBAL=/dev/null git -C <repo> checkout -- .gitconfig` (requires git 2.32 or later). `HOME=/nonexistent git ...` also works on older git.

Two more problems:

- "Make no changes" covers only this step. Bootstrap goes on to `git_clone_repos` and `configure_vcs_author` (see #1), both of which hit the broken config. The guard should make bootstrap exit non-zero, or at least skip the git-dependent steps.
- The guard only catches a direct self-include. A cleaner, more general check is to validate after writing: run `git config --file <stub> --includes --list` in a hermetic environment (see Suggestion 6). On failure, restore the previous file and abort. That catches any cycle, including the repo file including `~/.gitconfig`.

### 4. The commit that edits repo `.gitconfig` must start from a clean copy of that file

Right now the working copy of the repo `.gitconfig` contains the injected work-internal sections (`git diff .gitconfig` shows them below the `~/.my_gitconfig` include). The design orders the steps as: implement, run bootstrap, then `git checkout -- .gitconfig`. But the implementation commit that removes the `[include] path = ~/.my_gitconfig` line edits that same dirty file *before* that checkout. A whole-file `git add`/`commit -a` would publish internal hostnames and credential paths to this public repo.

Add an explicit step:

1. Run `git checkout -- .gitconfig` (or stage only the include-removal hunk with `git add -p`) before committing.
2. Audit `git diff --cached` per the repo's confidentiality policy.

A side effect to note in the rollout: between the checkout and the next login-hook run, the cert settings are missing from the effective config. Re-login, or re-run the hook, after the checkout.

## Suggestions (nice to have)

1. **Specify how `_gitconfig_includes` parses the file, and don't use `_pydotlib/git.py` for it.** `read_git_config` has several limits that make it wrong for this:
   - It keeps only the last value per key, so a stub with a second `path =` added later reads as "not migrated", which leads to a re-prompt and a nested double include.
   - It matches section and key names case-sensitively. Git doesn't (`[Include] Path =` is valid).
   - It leaves inline comments in the value.
   - It doesn't expand `~` or resolve relative paths.

   Instead, run `git config --file <stub> --type=path --get-all include.path` in a hermetic environment (Suggestion 6), with `cwd` set to the stub's directory. In testing, this:
   - expanded `~`
   - ignored `[includeIf]`
   - handled `[Include] Path`
   - stripped inline comments
   - returned relative paths verbatim

   Then resolve relative entries against the stub's directory and compare with `Path.resolve()`.

2. **Order the regular-file conversion so an interruption can't lose the old content.**
   - If it copies `safe_symlink` (`rename` to `.ORIGINAL`, then create), a crash between the two leaves `~/.gitconfig` missing. The next run then takes the "missing" row, and the old content survives only in the backup, no longer applied.
   - Safer order: read the old content, `shutil.copy2` it to the backup, then `os.replace` the rendered stub (old content appended) over the original.
   - Also make sure a newline separates each appended block (old content, then the `~/.my_gitconfig` block) even if the source lacks a trailing newline.
   - If the old file already includes `~/.my_gitconfig`, don't also inline it.

3. **Compare resolved paths when deciding "repo under `$HOME`".** `find_dotfiles_root` returns a resolved path. If `~` or `~/.dotfiles` is itself a symlink (common when home is small and a data volume holds the checkout), a plain lexical check against `Path.home()` fails, so the stub gets a host-specific absolute path, and that stub then syncs to other machines. Check against both `Path.home()` and `Path.home().resolve()`, and prefer `~/.dotfiles/.gitconfig` whenever it resolves to the same file. This doesn't affect this devserver, where `~/.dotfiles` is a real directory.

4. **Container upgrade test details.**
   - Bootstrap runs with `--git-name 'Testy McTestFace'`, which overwrites any seeded identity, so the fold-in can't be proven through `user.name`. Seed a unique sentinel key instead (e.g. `[dotfilestest] migrated = yes`). Then assert it reaches `~/.gitconfig`, and that `~/.my_gitconfig` still exists (bootstrap never deletes).
   - Repoint the two existing `check_file_contains(~/.my_gitconfig, ...)` checks to `~/.gitconfig`. As written, they would pass trivially against the seeded file.
   - Seeding every flavor drops container coverage of the fresh-install ("missing") row. Seed only one flavor, or note that unit tests alone cover that row.
   - A positive worth keeping: the read-only repo mount makes any write-through bug fail loudly with EROFS in CI.

5. **Native check:** don't match the exact include line text. Its tab/space form and `~`-vs-absolute form vary, and `build_native_checks` gets a resolved absolute `dotfiles` path while the stub says `~/...`. The `--includes --get log.date` check already proves the include resolves; it's enough on its own.

6. **Test hermeticity.** Any unit test or helper that shells out to git should set `HOME=<tmp>` and `GIT_CONFIG_NOSYSTEM=1`, and unset `XDG_CONFIG_HOME`. This repo's shell init exports `XDG_CONFIG_HOME` pointing at the real home, so with only `HOME` overridden, git still resolves the XDG global file in the real home. During this review that would have written into it if the file had existed. The same environment (plus `GIT_CONFIG_GLOBAL=/dev/null`) also lets the bootstrap helpers in #3 and Suggestion 1 run even when the user's global config is broken.

7. **Sync spot-check.** Since the tool keeps the local copy when both sides changed, extend the check on the other devserver beyond "the stub is a regular file":
   - `git -C ~/.dotfiles status --short .gitconfig` is clean there. Its login hook may have written through its symlink before the stub arrived, leaving injected content and a conflict.
   - The tool's conflicts directory holds nothing for these two paths.

   Also note in the doc that the stub carries this machine's folded identity to all synced machines (presumably intended).

8. **CHANGELOG wording:** "re-run bootstrap right after pulling" doesn't fit synced machines, which get the change with no pull. Add a clause that synced machines need no action beyond the spot-check.

9. **Policy text.** The migration policy's step 5 (`tests/docker/upgrade_from_v<N>/`) conflicts with the integration-test policy's "flat in `tests/docker/`, no per-target subdirectory". The design's pre-seed choice is reasonable. Update CLAUDE.md step 5 to name the pre-seed mechanism so future reviews don't flag it.

10. **Legacy-artifact log line.** The migration policy says to log when the old artifact is detected. The design logs only when it writes a new stub. A single quiet line on later runs while `~/.my_gitconfig` exists (and is already folded) would meet the policy without noise.

11. **`bin/dotfiles-cleanup`:** with no TTY, default to "no" for each path rather than reading EOF as consent.

## Verified Claims

All tested with git 2.53 under a temp `HOME` with `XDG_CONFIG_HOME` unset. The real home was not modified.

- **Precedence:** with the stub's `[user] name` placed after the include, git returns the stub value, and `--show-origin --get-all` lists the repo value first. Later values win, as the design states.
- **`~` expansion in `include.path`** works: the repo file loads, and `--type=path` expands `~` to `$HOME`.
- **`git config --global --get` ignores includes:** `log.date`, defined only in the repo file, returns exit 1. With `--includes` it returns `relative`. The proposed integration check is valid.
- **Tool writes land in the stub and preserve it:** `git config --global --replace-all 'http.https://example.invalid.proxy' ''` against a regular stub kept the header comment, the tab-indented `[include]`, and the migrated block, and appended a new `[http "..."]` section at the end. The repo file was untouched.
- **Symlinked `~/.gitconfig` writes through to the target** (the root cause), confirmed.
- **Approach 2's failure mode is real:** with `~/.gitconfig` missing and `$XDG_CONFIG_HOME/git/config` present, `git config --global` writes to the XDG file. Approach 1's fail-safe claim holds because the repo places nothing in the XDG location.
- **A self-include is fatal for every git command, with the error shown in #3.** `GIT_CONFIG_GLOBAL=/dev/null` bypasses it.
- **Relative include paths resolve against the including file's directory.** `~/.my_gitconfig` and the stub both live in `$HOME`, so relative includes inside folded content keep working.
- **Folding `~/.my_gitconfig` below the include keeps its effective precedence.** Today it is included after all shared settings in the repo file; below the stub's include, it still comes after them.
- **Duplicate `[user]` sections after the fold-in are handled:** `update_git_config` rewrites every matching `user.name`/`user.email` line in place and appends only missing keys, so values stay consistent. A differently-cased `[User]` would get a new `[user]` appended, which git resolves last-wins.
- **Container runner:** `confirm()` returns its default when stdin isn't a TTY, so the default-yes prompt never hangs under `< /dev/null`. The `.bashrc` seed step is a working template for the pre-seed. The second bootstrap run in the runner exercises the "already includes" row for idempotency.
- **Confidentiality:** the design doc names no internal tools, hosts, or paths. It uses generic terms ("login-shell hook", "file-sync tool", "work devservers"). This review also avoids them.
