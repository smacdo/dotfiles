# `~/.gitconfig` Local Stub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use 10x-engineer:subagent-driven-development (recommended) or 10x-engineer:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `~/.gitconfig` an untracked local stub that includes the repo `.gitconfig`, fold `~/.my_gitconfig` into it, and retire the legacy file.

**Architecture:** A new `install_gitconfig_stub()` in `_pydotlib/bootstrap.py` replaces the `.gitconfig` symlink step. It inspects config files with git in a hermetic environment, writes atomically with backups, validates after writing, and returns a `StubResult` enum that gates `configure_vcs_author` and bootstrap's exit code. A small POSIX `bin/dotfiles-cleanup` removes the legacy file once its content is folded in.

**Tech Stack:** Python 3 stdlib (`enum`, `hashlib`, `shutil`, `subprocess`, `tempfile`), git CLI, POSIX sh, `unittest`.

**Spec:** `docs/plans/2026-10-28-gitconfig-stub-design.md`

## Global Constraints

- Public repo: no internal tool names, hostnames, or paths in code, tests, comments, docs, or commit messages. Audit `git diff --cached` before every commit.
- Python stdlib only; type hints in the repo's existing style (`Path | str`, `list[...]`).
- Every git subprocess in bootstrap helpers and tests uses the hermetic env: `HOME=<dir>`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, `XDG_CONFIG_HOME` removed.
- Stage files explicitly (`git add <paths>`); never `git commit -a`. Run `python3 lint_all.py` before each commit.
- Stub header text, marker format, and recovery command are exact copy (see Task 1 and Task 2).
- Bootstrap never deletes user data; every write to an existing regular `~/.gitconfig` makes a `.ORIGINAL` backup first via `create_backup_filename`.

## Review Focus

1. `git` missing from PATH when bootstrap runs: `install_gitconfig_stub` returns `FAILED` with a clear log line, no traceback (test in Task 2).
2. `~/.my_gitconfig` unreadable (permission denied): log a warning, skip the fold-in, don't crash; result still `READY` if the stub is otherwise fine (test in Task 2).
3. A `.gitconfig.ORIGINAL` already exists from an earlier run: the new backup gets a timestamped name and the old backup is untouched (test in Task 2).
4. `--dry-run` on the conversion and fold-in paths writes nothing, including no backup file (test in Task 2).
5. An empty `~/.my_gitconfig`: fold-in appends only the marker line, so cleanup can proceed (test in Task 2; cleanup case in Task 5).

---

### Task 0: Preconditions (owner)

These need the owner's decision before any task commits. They aren't implementation work.

- [ ] **Step 1: Park or land the pre-existing working-tree changes** that overlap this plan's files (`_pydotlib/bootstrap.py`, `_pydotlib/tests/test_bootstrap.py`, `run_tests.py`, `CHANGELOG.md`, `README.md`, `TODO.md`, `.tmux.conf`, `tools/install_nerd_fonts.sh`, `_pydotlib/tests/test_run_tests.py`). Each task below must commit only its own changes.
- [ ] **Step 2: Fix or baseline lint.** `lint_all.py` currently fails on HEAD because `uvx ruff` is unpinned (ruff 0.17.3 adds new rules). Either pin ruff first, or record the baseline (`python3 lint_all.py 2>&1 | tail -3`) and treat "no new errors in touched files" as the gate.
- [ ] **Step 3: Pause the sync timer on this devserver for the duration** (the owner's choice; it avoids synced overwrites of working-tree edits mid-task) and resume it after Task 7.

---

### Task 1: Hermetic git helpers and stub rendering

**Files:**
- Modify: `_pydotlib/bootstrap.py` (new helpers near `create_backup_filename`)
- Test: `_pydotlib/tests/test_bootstrap.py` (new `TestGitconfigHelpers`)

**Interfaces:**
- Produces:
  - `STUB_HEADER: str`, exactly:
    ```
    # Local git config for this machine. Not tracked: tools such as `git config --global`
    # write here, and so can you. Shared settings come from the dotfiles repo via the include.
    ```
  - `LEGACY_MARKER_PREFIX = "# migrated from ~/.my_gitconfig sha256="`
  - `_hermetic_git_env(home: Path) -> dict[str, str]`: a copy of `os.environ` with `HOME=str(home)`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, and `XDG_CONFIG_HOME` removed.
  - `_gitconfig_include_paths(path: Path) -> list[Path]`: runs `git config --file <path> --type=path --get-all include.path` with `cwd=path.parent` and `env=_hermetic_git_env(path.parent)`. Exit 1 (no key) means `[]`. Relative results are resolved against `path.parent`. Every result is `.resolve()`d. Raises `GitConfigError` on any other non-zero exit or `FileNotFoundError` from a missing git.
  - `class GitConfigError(Exception)`
  - `_gitconfig_includes(path: Path, repo_file: Path) -> bool`: is `repo_file.resolve()` in `_gitconfig_include_paths(path)`.
  - `_include_path_for(repo_gitconfig: Path, home: Path) -> str`: returns `"~/" + rel` when `repo_gitconfig.resolve()` equals `(home / rel).resolve()`, with `rel` taken from `repo_gitconfig` relative to `home`, else relative to `home.resolve()`. Otherwise returns the absolute resolved path.
  - `_render_gitconfig_stub(include_path: str) -> str`: `STUB_HEADER + "[include]\n\tpath = " + include_path + "\n"`.
  - `_legacy_marker(legacy: Path) -> str`: `LEGACY_MARKER_PREFIX + sha256(legacy.read_bytes()).hexdigest()`.
  - `_validate_stub(stub: Path, repo_file: Path) -> bool`: True iff `git config --file <stub> --includes --list` (hermetic env, `home=stub.parent`) exits 0 **and** `_gitconfig_includes(stub, repo_file)` **and** `repo_file.is_file()`.

- [ ] **Step 1: Write failing tests** in `TestGitconfigHelpers`. Each uses a `tempfile.TemporaryDirectory()` as the home:
  - `test_hermetic_env_strips_xdg_and_global`: env has `GIT_CONFIG_GLOBAL == "/dev/null"`, `GIT_CONFIG_NOSYSTEM == "1"`, `HOME == str(tmp)`, and no `XDG_CONFIG_HOME` key, even when one is set in `os.environ` (use `patch.dict`).
  - `test_include_paths_expands_tilde_and_case`: a file with `[Include]\n\tPath = ~/repo/.gitconfig ; comment\n` returns `[tmp/"repo/.gitconfig"]` (resolved).
  - `test_include_paths_multiple_and_relative`: two `path =` entries, one relative (`sub/x`), resolve against the file's dir; both returned.
  - `test_include_paths_none_returns_empty`: a file with no include returns `[]`.
  - `test_includes_true_for_absolute_or_tilde_form`: `_gitconfig_includes` is True for both `~/repo/.gitconfig` and the absolute form.
  - `test_include_path_for_under_home`: repo at `tmp/repo/.gitconfig` with home `tmp` gives `"~/repo/.gitconfig"`.
  - `test_include_path_for_symlinked_home`: home `tmp/link -> tmp/real`, repo at `tmp/real/repo/.gitconfig` gives `"~/repo/.gitconfig"`.
  - `test_include_path_for_outside_home`: gives the absolute resolved path.
  - `test_render_stub_exact`: equals `STUB_HEADER + "[include]\n\tpath = ~/repo/.gitconfig\n"`.
  - `test_legacy_marker_changes_with_content`: different bytes give different markers; the same bytes give the same marker; it starts with `LEGACY_MARKER_PREFIX`.
  - `test_validate_stub_detects_cycle`: the repo file includes itself, so the result is False.
  - `test_validate_stub_detects_missing_include_target`: the stub includes a nonexistent file, so the result is False.
  - `test_validate_stub_ok`: a valid stub plus repo file gives True.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest _pydotlib.tests.test_bootstrap.TestGitconfigHelpers -v`
Expected: ImportError / FAIL (names not defined)

- [ ] **Step 3: Implement the helpers** listed in Interfaces in `_pydotlib/bootstrap.py`. Use `subprocess.run(..., capture_output=True, text=True, check=False)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest _pydotlib.tests.test_bootstrap.TestGitconfigHelpers -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add _pydotlib/bootstrap.py _pydotlib/tests/test_bootstrap.py
git diff --cached   # audit: no internal names
git commit -m "add hermetic git config helpers for the gitconfig stub"
```

---

### Task 2: `install_gitconfig_stub`

**Files:**
- Modify: `_pydotlib/bootstrap.py`
- Test: `_pydotlib/tests/test_bootstrap.py` (new `TestInstallGitconfigStub`)

**Interfaces:**
- Consumes: everything from Task 1; existing `create_backup_filename`, `confirm`.
- Produces:
  - `class StubResult(enum.Enum): READY, SKIPPED, FAILED`
  - `install_gitconfig_stub(stub_path: Path, repo_gitconfig: Path, legacy_local: Path, dry_run: bool = False) -> StubResult`
  - `RECURSION_FIX = "GIT_CONFIG_GLOBAL=/dev/null git -C {repo} checkout -- .gitconfig"`. The error log line includes it, formatted with the repo dir.

Behavior (from the spec), in order:
1. Recursion guard: `_gitconfig_includes(repo_gitconfig, repo_gitconfig)` means log an error with `RECURSION_FIX`, return `FAILED`. A `GitConfigError` or missing git anywhere also means log an error, return `FAILED`.
2. Rows:
   - missing: write the stub.
   - symlink resolving to the repo file: replace it with the stub.
   - a regular file where `_gitconfig_includes` is True: no conversion.
   - a regular file without the include: `confirm(..., default=True)`. On no, return `SKIPPED`. On yes, `shutil.copy2` to the backup, then write `stub + "\n" + old content` (ensure a trailing newline between blocks).
   - a foreign or broken symlink: warn, return `SKIPPED`.
3. Legacy fold-in, when a regular stub results: if `legacy_local` exists, is readable, and `_legacy_marker(legacy_local)` isn't a line in the stub, then `confirm(..., default=True)`. On yes, back up the existing stub (if it existed before this run), then append `"\n" + marker + "\n" + legacy content` with newline separation. Unreadable means warn and skip. While the marker is current, log one info line: "~/.my_gitconfig is no longer used; `bin/dotfiles-cleanup` can remove it".
4. All writes go through a temp file in the same dir plus `os.replace`. In dry-run, log the intended action, write nothing (no backups), skip step 5, and return `READY` when the planned outcome is a stub (`SKIPPED`/`FAILED` as the rows dictate otherwise).
5. `_validate_stub` after the run (also when nothing was written). On failure, restore: copy the backup back, or recreate the prior symlink if one was replaced, or remove a stub created from nothing. Log an error and return `FAILED`. Otherwise return `READY`.

- [ ] **Step 1: Write failing tests** in `TestInstallGitconfigStub`. Each test runs in a temp home with a `repo/.gitconfig` containing `[log]\n\tdate = relative\n`. Patch `_pydotlib.bootstrap.confirm` where a prompt occurs. Assert on returned `StubResult`, file contents, and backups:
  - `test_missing_writes_stub`: READY; content == `_render_gitconfig_stub("~/repo/.gitconfig")`.
  - `test_symlink_to_repo_replaced`: READY; `not stub.is_symlink()`; repo file bytes unchanged.
  - `test_already_stub_is_noop`: second call returns READY; content and mtime unchanged.
  - `test_regular_file_converted_with_backup`: original `[alias]\n\tst = status` (no trailing newline) becomes stub + original; the backup holds the exact original bytes; the backup exists (order: copy before replace).
  - `test_regular_file_declined_skipped`: confirm returns False, so SKIPPED, the file is untouched, and no backup.
  - `test_foreign_symlink_skipped` and `test_broken_symlink_skipped`: SKIPPED; link unchanged; no file created at the link target.
  - `test_recursion_guard_fails_without_changes`: the repo file includes itself, so FAILED; the stub path is untouched; the log contains `GIT_CONFIG_GLOBAL=/dev/null git -C`.
  - `test_legacy_folded_once`: legacy `[user]\n\tname = Old\n[x]\n\ty = 1\n` gets folded with the marker. A second call is a no-op with no new block.
  - `test_legacy_not_refolded_after_value_rewrite`: after the fold, rewrite `user.name` in the stub to `New` with `git config --file`. A second call adds nothing, and `git config --file stub --includes --get user.name` == `New`.
  - `test_legacy_refolded_after_legacy_edit`: edit the legacy file, so a second call appends a new block and the new marker.
  - `test_synced_stub_with_other_marker_still_folds`: the stub already contains `LEGACY_MARKER_PREFIX + "0"*64`, so this machine's legacy file is folded.
  - `test_legacy_left_on_disk`: after the fold, `legacy_local.exists()`.
  - `test_old_file_including_legacy_still_folds`: the old regular `~/.gitconfig` has `[include]\n\tpath = ~/.my_gitconfig`. After the conversion, the legacy content is appended with its marker and the old include line is still present.
  - `test_dry_run_returns_ready_without_validation`: dry-run on a missing stub returns READY and creates nothing.
  - `test_validation_failure_restores`: patch `_validate_stub` to return False on a conversion run, so FAILED and the original bytes are restored.
  - Review Focus tests: `test_git_missing_fails_cleanly` (patch `subprocess.run` to raise `FileNotFoundError`; FAILED, no exception); `test_unreadable_legacy_warns_and_continues` (chmod 000, skip if root; READY, warning logged, no marker); `test_existing_backup_preserved` (pre-create `.gitconfig.ORIGINAL`; the new backup has a different name; the old one is unchanged); `test_dry_run_writes_nothing` (conversion plus legacy present; directory listing and contents unchanged); `test_empty_legacy_appends_marker_only`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest _pydotlib.tests.test_bootstrap.TestInstallGitconfigStub -v`
Expected: FAIL (names not defined)

- [ ] **Step 3: Implement `StubResult` and `install_gitconfig_stub`** per the behavior above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest _pydotlib.tests.test_bootstrap -v`
Expected: all PASS (the whole module, to catch regressions)

- [ ] **Step 5: Commit**

```bash
git add _pydotlib/bootstrap.py _pydotlib/tests/test_bootstrap.py
git diff --cached
git commit -m "add install_gitconfig_stub to replace the ~/.gitconfig symlink"
```

---

### Task 3: Wire into bootstrap; retarget `configure_vcs_author`

**Files:**
- Modify: `bootstrap.py` (imports; remove `(".gitconfig", ...)` from the symlink list; `MY_GITCONFIG_PATH`; `--git-name`/`--git-email` help; call order and exit code)
- Modify: `_pydotlib/bootstrap.py` (`configure_vcs_author` symlink refusal)
- Test: `_pydotlib/tests/test_bootstrap.py` (`TestConfigureVcsAuthor`)

**Interfaces:**
- Consumes: `install_gitconfig_stub`, `StubResult` (Task 2).
- Produces: `bootstrap.main()` returns 1 when the stub result is `FAILED`. `configure_vcs_author` runs only on `READY`.

- [ ] **Step 1: Write failing tests**:
  - `test_refuses_symlink`: `configure_vcs_author(link_path, name="A", email="a@x")` where `link_path` is a symlink to another file: the link and its target bytes are unchanged, and a warning is logged.
  - `test_refuses_broken_symlink_creates_nothing`: the target path still doesn't exist afterwards.
- [ ] **Step 2: Run** `python3 -m unittest _pydotlib.tests.test_bootstrap.TestConfigureVcsAuthor -v`. Expected: the two new tests FAIL.
- [ ] **Step 3: Implement.** In `configure_vcs_author`, if `gitconfig_path.is_symlink()`, log a warning and return before any read or write. In `bootstrap.py`:
  - `MY_GITCONFIG_PATH = Path.home() / ".gitconfig"` (rename to `GITCONFIG_PATH`).
  - Help text: "Name to use for git user.name in ~/.gitconfig" (same shape for email).
  - Call `install_gitconfig_stub(home_dir / ".gitconfig", dotfiles_root / ".gitconfig", home_dir / ".my_gitconfig", dry_run=args.dry_run)` right after `apply_dotfile_symlinks`. Return 1 on `FAILED`. Call `configure_vcs_author` only on `READY`.
- [ ] **Step 4: Run** `python3 run_tests.py --no-docker`. Expected: all suites pass.
- [ ] **Step 5: Manual dry run.** Run `HOME=$(mktemp -d) python3 bootstrap.py --dry-run --git-name T --git-email t@t < /dev/null`. Expected: it logs "Would write ~/.gitconfig stub" and no files appear in the temp home.
- [ ] **Step 6: Commit** `bootstrap.py _pydotlib/bootstrap.py _pydotlib/tests/test_bootstrap.py` (audit first). Message: "install the ~/.gitconfig stub from bootstrap and write identity there".

---

### Task 4: Integration checks and container seed

**Files:**
- Modify: `_pydotlib/integration_checks.py` (`BOOTSTRAP_CHECKS`, `build_native_checks`, new `LEGACY_GITCONFIG_SENTINEL`)
- Modify: `run_tests.py` (seed step)
- Test: `_pydotlib/tests/test_integration_checks.py`

**Interfaces:**
- Produces: `LEGACY_GITCONFIG_SENTINEL = "dotfilestest.migrated"` (the key; its value is `yes`).

- [ ] **Step 1: Update the tests first.** In `test_integration_checks.py`, assert that `build_native_checks(...)` no longer contains a check named `symlink: <home>/.gitconfig ...` and does contain one whose name includes `--includes --get log.date`. Run `python3 -m unittest _pydotlib.tests.test_integration_checks -v`. Expected: FAIL.
- [ ] **Step 2: Change the checks.**
  - In both lists, replace `check_symlink(... .gitconfig ...)` with `check_command_output_matches(["git", "config", "--global", "--includes", "--get", "log.date"], "relative")`.
  - In `BOOTSTRAP_CHECKS`, repoint the two `~/.my_gitconfig` `check_file_contains` checks to `~/.gitconfig`.
  - Add `check_command_output_matches(["git", "config", "--get", LEGACY_GITCONFIG_SENTINEL], "yes")`.
  - Add `check_command_succeeds(["test", "-f", f"{_HOME}/.my_gitconfig"])` (bootstrap never deletes).
  - Keep the `git config user.name` == `Testy McTestFace` check: the seeded old name must not win after the second bootstrap pass.
- [ ] **Step 3: Seed in `run_tests.py`** next to the `.bashrc` seed. Seed every flavor (this deviates from the spec's "one flavor": `BOOTSTRAP_CHECKS` is shared across flavors, and unit tests cover the fresh-install row). Run:
  `ln -s /home/testuser/.dotfiles/.gitconfig /home/testuser/.gitconfig && printf '[user]\n\tname = Old Name\n[dotfilestest]\n\tmigrated = yes\n' > /home/testuser/.my_gitconfig`
  with label "seed pre-bootstrap ~/.gitconfig symlink and ~/.my_gitconfig (upgrade test)". Update the spec's Testing bullet to match.
- [ ] **Step 4: Run** `python3 -m unittest _pydotlib.tests.test_integration_checks -v` (PASS), then `python3 run_tests.py` (containers). Expected: all flavors pass, including the re-run pass.
- [ ] **Step 5: Commit** `_pydotlib/integration_checks.py _pydotlib/tests/test_integration_checks.py run_tests.py docs/plans/2026-10-28-gitconfig-stub-design.md`. Message: "check the gitconfig stub and legacy fold-in in container tests".

---

### Task 5: `bin/dotfiles-cleanup`

**Files:**
- Create: `bin/dotfiles-cleanup` (from `bin/mksh dotfiles-cleanup`; `chmod +x`)

**Interfaces:**
- CLI: `dotfiles-cleanup [--dry-run]`. Exit 0 when done (including when nothing was removed). Exit 2 on a usage error.

- [ ] **Step 1: Generate the skeleton** with `bin/mksh dotfiles-cleanup`.
- [ ] **Step 2: Implement one stanza, `~/.my_gitconfig`:**
  - Skip if absent.
  - Compute the legacy file's sha256 with `sha256sum` if available, else `shasum -a 256`.
  - Refuse unless `~/.gitconfig` contains the line `# migrated from ~/.my_gitconfig sha256=<hash>`. Print "not folded into ~/.gitconfig yet; re-run bootstrap.py first".
  - Otherwise prompt `Remove ~/.my_gitconfig? [y/N]`. With no TTY (`[ -t 0 ]` false), treat the answer as no.
  - With `--dry-run`, print "would remove" and don't prompt.
  - Comment each stanza, since shell scripts get comments in this repo.
- [ ] **Step 3: Verify.**
  - `python3 lint_all.py` shows the script passing shellcheck.
  - Manual, in a temp `HOME`: (a) absent: no output, exit 0; (b) unfolded: refuses; (c) folded plus `--dry-run`: "would remove"; (d) folded with `< /dev/null`: not removed; (e) an empty legacy file with its marker present: offered for removal.
- [ ] **Step 4: Commit** `bin/dotfiles-cleanup`. Message: "add dotfiles-cleanup for orphaned legacy files".

---

### Task 6: Drop the legacy include from the repo `.gitconfig`; docs

**Files:**
- Modify: `.gitconfig` (remove the trailing `[include]\n  path = ~/.my_gitconfig`)
- Modify: `CHANGELOG.md`, `CLAUDE.md`, `README.md`, `TODO.md`

- [ ] **Step 1: Start from a clean copy.** `git checkout -- .gitconfig` (the working copy may contain injected machine-specific sections). Verify with `git diff .gitconfig` (empty).
- [ ] **Step 2: Remove the include block** at the end of `.gitconfig`. `git diff .gitconfig` should show only those two lines (plus a blank line, if any) removed.
- [ ] **Step 3: Docs.**
  - `CHANGELOG.md` gets a new dated entry:
    - **Changed** `~/.gitconfig` from a symlink to a local stub that includes the repo file. `~/.my_gitconfig` is folded into it. Re-run `bootstrap.py` right after pulling. A machine that receives the new stub by file sync needs no action if its `~/.my_gitconfig` matches the one folded in; otherwise re-run `bootstrap.py` there so it folds in its own. Tools may have written machine-specific settings into the repo `.gitconfig` through the old symlink: first check `git diff .gitconfig` and copy anything you want to keep into `~/.gitconfig`, then run `git checkout -- .gitconfig` to drop those sections from the repo copy.
    - **Added** `bin/dotfiles-cleanup`, which removes `~/.my_gitconfig` once it's folded in. It is opt-in and asks before removing anything.
  - `CLAUDE.md`:
    - "Bootstrap System": `~/.gitconfig` is a local stub, not a symlink.
    - "Per-Machine Overrides": replace the `~/.my_gitconfig` bullet with `~/.gitconfig`.
    - Migration policy step 4: point to `bin/dotfiles-cleanup`. Step 5: replace `tests/docker/upgrade_from_v<N>/` with "a pre-bootstrap seed step in `run_tests.py` that recreates the old layout".
  - `README.md`: replace any `~/.my_gitconfig` mention with `~/.gitconfig`.
  - `TODO.md`:
    - Narrow the stub item to `.bashrc`/`.zshrc`, noting that the stub logic is ready to extract into a generic installer.
    - Remove the "Move `~/.my_gitconfig` into `$XDG_CONFIG_HOME`" item.
    - Mark the `bin/dotfiles-cleanup` item done, with a pointer to the script (this TODO was explicitly tasked).
- [ ] **Step 4: Verify.**
  - `grep -n my_gitconfig CLAUDE.md README.md .gitconfig bootstrap.py _pydotlib/*.py` shows only intentional references (the legacy path in `install_gitconfig_stub` and its call).
  - `python3 lint_all.py`; `python3 run_tests.py --no-docker`.
- [ ] **Step 5: Commit**, staging only these files.

```bash
git add .gitconfig CHANGELOG.md CLAUDE.md README.md TODO.md
git diff --cached   # audit: .gitconfig hunk is only the include removal; no internal names anywhere
git commit -m "fold ~/.my_gitconfig into the local ~/.gitconfig stub"
```

---

### Task 7: Rollout on this devserver (owner-assisted)

- [ ] **Step 1: Run** `python3 bootstrap.py` and accept the prompts. Expected log lines:
  - "Replaced symlink ~/.gitconfig with local stub"
  - "Folded ~/.my_gitconfig" (or equivalent)
  - "~/.my_gitconfig is no longer used"
- [ ] **Step 2: Verify the stub.**
  - `test ! -L ~/.gitconfig`
  - `git config --global --includes --get log.date` prints `relative`
  - `git config user.name` prints your name
- [ ] **Step 3: Clean the repo working copy.** First check `git -C ~/.dotfiles diff .gitconfig` and copy anything you want to keep into `~/.gitconfig`. Then run `git -C ~/.dotfiles checkout -- .gitconfig`. Then `git -C ~/.dotfiles status --short .gitconfig` should be empty. Re-login so the login hook rewrites its settings into the stub.
- [ ] **Step 4: Check that tool writes land in the stub.** Run `git config --global http.https://example.invalid.proxy ""`. The new section appears in `~/.gitconfig` and the repo `.gitconfig` is unchanged. Then remove it with `git config --global --unset http.https://example.invalid.proxy`.
- [ ] **Step 5: Resume the sync timer.** After the next sync, spot-check one other devserver:
  - `~/.gitconfig` is a regular file with the include
  - `git config user.name` works
  - `git -C ~/.dotfiles status --short .gitconfig` is clean
  - the sync tool's conflicts directory has nothing for these paths
- [ ] **Step 6: The owner pushes** (agents can't push to GitHub here), then pulls and runs `bootstrap.py` on the Mac right away.
