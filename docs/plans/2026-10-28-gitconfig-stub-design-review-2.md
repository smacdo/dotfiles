VERDICT: NEEDS_REVISION

## Summary Assessment

Round-1 criticals #1, #3, and #4 are fixed. The replacement for #2 (an entry-subset comparison) introduces a new critical: the fold-in is not idempotent and re-appends stale values that override newer ones. That is the "re-appends stale config" behaviour the design is trying to avoid.

## Critical Issues (must fix)

### 1. The entry-subset fold-in fires again after any legitimate change to a folded key, and the stale block then wins

The design's rule is `_gitconfig_entries(legacy) <= _gitconfig_entries(stub)`. It asks whether every legacy `(key, value)` pair still exists in the stub. Two routine writers rewrite folded values in place:

- `configure_vcs_author`: `update_git_config` replaces *every* `user.name`/`user.email` line.
- The login hook: `git config --global --replace-all` rewrites cert settings.

Once either has run, the legacy pairs are gone from the stub, so the next bootstrap prompts and appends the legacy block again. Because it is appended last, it overrides the new values.

I reproduced this in a hermetic temp `HOME` (git 2.53, `GIT_CONFIG_NOSYSTEM=1`, `XDG_CONFIG_HOME` unset):

1. Folded `~/.my_gitconfig` (`user.name=Old Name`, one `http.<url>.sslcert=/a.pem`) into a stub. The subset check passes.
2. Ran `git config --global --replace-all user.name "New Name"` and `--replace-all 'http.<url>.sslCert' /b.pem`. `comm -23` now reports both legacy pairs missing, so a re-fold triggers.
3. After the re-fold append, `git config --get user.name` returns `Old Name` and the sslCert returns `/a.pem`. The user's identity and the hook's fresh cert path are both silently reverted.

It then loops:

- `configure_vcs_author` reads the last value (`Old Name`) as the prompt default, then rewrites every line again. With `--git-name`, or when the user re-types the new name, the next run re-folds again. Every bootstrap appends another block, which breaks the idempotency goal.
- On the machine whose login hook manages cert settings, any drift between the legacy file and what the hook writes causes the same ping-pong between bootstrap runs and logins.
- `bin/dotfiles-cleanup`'s identical subset check then refuses forever, naming `user.name` as unfolded. That fails closed, but is confusing.
- CI won't catch any of this: the pre-seeded legacy file holds only a sentinel key that nothing rewrites.

The coordinator's objection to a plain marker is valid: a synced stub carries another machine's marker. A content-keyed marker answers that objection and avoids the re-fold:

- When folding, write `# migrated from ~/.my_gitconfig sha256=<hash of the legacy file's bytes>`.
- Fold only when no marker in the stub carries the current legacy file's hash.
- How this covers each case:
  - **Stub synced from a machine whose legacy file differs:** the hashes differ, so this machine still folds (the coordinator's case).
  - **Identical legacy files:** the hashes match, so it skips.
  - **Later edits to folded keys** by `configure_vcs_author`, the hook, or the user: they don't change the hash, so no re-fold.
  - **The legacy file itself is edited later:** a new hash, so it prompts again, which is arguably correct.
- `bin/dotfiles-cleanup` uses the same test. Portable shell for the hash: `sha256sum` on Linux, `shasum -a 256` on macOS.
- This also removes the conflict in Suggestion 3.

Add a unit test that folds, rewrites a folded value, re-runs bootstrap, and expects no re-fold.

## Suggestions (nice to have)

1. **The bool return can't carry "bootstrap exits non-zero".** `install_gitconfig_stub -> bool` returns False for each of these, and only some should stop bootstrap:
   - a declined prompt
   - a foreign or broken symlink
   - a validation failure
   - the recursion guard

   As written, an implementer either fails bootstrap whenever the user declines (or has a foreign symlink), or never exits on the guard. Have the guard (and probably the validation failure) raise a dedicated exception that `bootstrap.py` turns into a non-zero exit, or return an enum.

2. **Validation coverage.**
   - Post-write validation correctly catches cycles the narrow guard misses. Tested: a repo file containing `[include] path = ~/.gitconfig` passes `_gitconfig_includes(repo, repo)`, but `git config --file <stub> --includes --list` exits 128. It also catches syntax errors (`bad config line`).
   - Git silently ignores a *missing* include target (the dangling `include.path` exits 0), so validation alone doesn't prove the include resolves. Pair it with `_gitconfig_includes(stub, repo) and repo.exists()`.
   - Run the same validation on the "already migrated, nothing written" branch before returning True. Otherwise a pre-existing cycle passes and the later `git_clone_repos` fails confusingly.
   - Restore source: folding into an existing stub makes no `.ORIGINAL` backup, so "restore the previous file from the backup" has nothing to restore from. Keep the pre-write bytes in memory for that branch.
   - For the "missing" row, restoring means unlinking the stub bootstrap just created. That's fine under the no-delete policy, but say so.

3. **The "skip inlining when the old `~/.gitconfig` already includes `~/.my_gitconfig`" rule conflicts with the subset check.** On the next run, the stub's only related entry is `include.path=~/.my_gitconfig`. The legacy entries aren't in `--list` (no `--includes`), so it prompts to fold anyway. The hash marker resolves this if the skip rule is dropped, or if the skip writes the marker too.

4. **A synced stub is per sync group, not per machine. Say so in the doc.**
   - Once machine B folds its own legacy file, the sync tool carries B's stub back to A, so stubs converge on every machine's folded blocks, and the last-folded value of a shared key wins everywhere.
   - Set-based "present" checks (subset or otherwise) can't tell that A's value is now overridden.
   - That fits the stated "same identity on all synced machines". But the goal line "one local file for per-machine git settings" no longer holds for synced devservers.
   - Consider a one-line warning at fold time when a legacy key's value differs from the stub's effective value (`git config --file <stub> --get <key>`).

5. **`~` detection spec.** "Resolves to the same file as `~/<relative path>`" doesn't say where the candidate relative path comes from. Name the candidates, e.g.:
   - the unresolved cwd-derived root relative to `Path.home()`
   - the resolved root relative to `Path.home().resolve()`
   - `~/.dotfiles/.gitconfig`

6. **Hermetic helper and git version.** With `HOME=<stub dir>`, the stub itself is git's default global file. Only `GIT_CONFIG_GLOBAL=/dev/null` keeps it from being loaded, and that needs git 2.32 or later. That's fine on the supported platforms (current Debian, Ubuntu, Fedora, and macOS ship newer). Note it so nobody "simplifies" the env away.

## Verified Claims

- **Round-1 #1 fixed.** `configure_vcs_author` runs only when the installer returns True and refuses `is_symlink()` paths. `is_symlink()` is True for dangling links, so the broken-symlink write-through can't happen. Unit tests for both rows are specified.
- **Round-1 #3 fixed.** The recovery command `GIT_CONFIG_GLOBAL=/dev/null git -C <repo> checkout -- .gitconfig` restored a self-included repo file in round-1 testing. Bootstrap stopping is specified (but see Suggestion 1). The post-write validation detects both direct and indirect cycles (exit 128) and syntax errors.
- **Round-1 #4 fixed.** There is an explicit clean-copy (`git checkout` or `git add -p`) and `git diff --cached` audit step before committing the repo `.gitconfig` change.
- **`git config --file <f> --list`** lowercases section and key names, keeps subsection case (`http.https://Ex.invalid.sslcert`), and strips inline comments from values. Comparisons are therefore insensitive to formatting, as the design intends. The problem in Critical #1 is the check's semantics, not its parsing.
- **Round-1 suggestions adopted correctly:**
  - interruption-safe copy-then-replace order
  - sentinel-based upgrade test on one flavor, with the other flavors keeping fresh-install coverage
  - exact-text include check dropped
  - extended sync spot-check
  - CHANGELOG wording for synced machines
  - CLAUDE.md migration policy update
  - cleanup defaulting to "no" without a TTY
- **Confidentiality:** the revised doc still names no internal tools, hosts, or paths. This review doesn't either.
