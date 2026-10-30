# Design: commit/push leak guard

**Status:** short design, approved 2026-10-28; implementation plan not yet written.
**Goal:** Stop secrets and work-internal content from being committed to or pushed from this
public repo, regardless of who makes the commit (by hand, an editor, or an agent).
**Architecture:** Python 3 stdlib. Logic in `_pydotlib/leak_guard.py`; thin executable wrappers
`bin/leak-guard` and `githooks/{pre-commit,commit-msg,pre-push}`; bootstrap points
`core.hooksPath` at `githooks/` and seeds the personal denylist.

## Why

`~/.gitconfig`, `~/.bashrc`, and `~/.zshrc` are symlinks into the repo, so tools that run
`git config --global` or append to `~/.bashrc` write machine- and work-local config straight
into tracked files, without any notice. That has already leaked once (committed and pushed)
and been re-injected once after a manual cleanup. The root-cause fix (stub files instead of
symlinks) is filed in `TODO.md`; this guard is the safety net until then, and stays useful after.

## Goals / non-goals / anti-goals

- **Goals:** block a commit or push whose *added* content matches a rule; work on every
  machine where bootstrap ran; take under a second; be easy to override on purpose.
- **Non-goals:** scanning existing history; replacing `lint_all.py` or CI; full secret-scanner
  coverage (gitleaks-grade entropy detection).
- **Anti-goals:** a guard noisy enough that `--no-verify` becomes a habit; a guard that
  silently does nothing when it breaks; tracked rules that themselves publish private names.

## Constraints

- Python 3 stdlib only (repo policy); macOS, Linux, WSL.
- Tracked files may only name terms that are already widely public. Private terms live in the
  untracked personal denylist.
- `core.hooksPath` lives in `.git/config`, which the file-sync tool does not sync. Some machines have no
  `.git/` at all, and the container tests mount the repo read-only.

## Approaches considered

1. **Python stdlib, module-backed (chosen).** Matches the `bin/` module-backed pattern, unit-
   testable, no install step. ~50 ms startup.
2. **POSIX sh + `grep -E`.** No Python needed, but diff parsing, line tracking, and pattern
   quoting are fragile and hard to test. Python is already required by bootstrap.
3. **gitleaks (or similar) with a custom config.** Best secret-format coverage, but an external
   binary on every machine (violates stdlib-only; missing binary means skip or block-everything)
   and it knows nothing about internal hostnames, which is what actually leaked.

## Decisions

**Hooks.** `githooks/pre-commit` scans staged changes. `githooks/commit-msg` scans the commit
message being written. `githooks/pre-push` scans every commit in the outgoing range, including
messages, so it also catches `--no-verify` commits, commits made before bootstrap enabled the
hooks, and commits pulled from elsewhere. All are bypassable with `--no-verify`.

**CLI** (`bin/leak-guard`, module-backed per the `bin/` policy):

```
leak-guard hook pre-commit            # called by githooks/pre-commit
leak-guard hook commit-msg <file>     # called by githooks/commit-msg
leak-guard hook pre-push <remote>     # called by githooks/pre-push (refs on stdin)
leak-guard scan [PATH...]             # scan whole files; default: every tracked file
leak-guard status                     # hooks enabled? lists loaded? rule counts
```

The `githooks/` wrappers resolve the repo root, add it to `sys.path`, and call
`leak_guard.main(["hook", ...])`, the same shape as the `bin/` wrappers.

**Change collection.**
- Pre-commit: `git diff --cached -U0 --no-color --no-ext-diff`, skipping binary files.
- Pre-push: read `<local ref> <local sha> <remote ref> <remote sha>` lines from stdin. Skip
  deletions (local sha all zeros). For an existing remote ref, scan `remote_sha..local_sha`;
  for a new ref, scan `local_sha --not --remotes`. Scan per commit (`git log -p -U0`), not the
  net diff, because a line added then removed within the range is still published.

**Diff parsing.** Track the file from `+++ b/<path>` and the new-side line number from `@@`
headers. Only `+` lines are checked, so deleting a bad line never trips the guard.

**Rule sources** (all case-insensitive; every match blocks):
1. *Built-in generic rules (tracked):* private-key headers (`-----BEGIN ... PRIVATE KEY-----`),
   common token formats (GitHub `ghp_`/`gho_`/`github_pat_`, AWS `AKIA...`, Slack `xox[bpas]-`),
   credential paths (`/var/<anything>/credentials/`), and absolute home paths
   (`/home/<name>/`, `/Users/<name>/`) except the container test user `testuser`.
2. *Shared denylist (tracked):* `githooks/denylist`, a short list of employer domains that
   research showed are already widely public. Matching the bare parent domain also covers
   private subdomains without naming them.
3. *Personal denylist (untracked):* `$XDG_CONFIG_HOME/dotfiles/commit-denylist`. If the file is
   missing, print a one-line warning (naming the path and suggesting a bootstrap re-run) and
   continue with the other rules.

**Denylist format** (both lists; Python 3.11 `tomllib` is not available on stock macOS or
Ubuntu 22.04, and JSON has no comments):

```
# full-line comment; blank lines ignored
some-term            # literal, case-insensitive substring; trailing comment allowed
re:host[0-9]+        # Python regex, case-insensitive
```

A malformed `re:` line is reported with its file and line number and blocks (fail closed).

**Structural rule.** Pre-commit reads the staged `.bashrc`/`.zshrc` (`git show :<path>`) and
fails if anything is below the end-of-config sentinel. `check_sentinel_is_last` and the
sentinel constants move from `lint_all.py` into `_pydotlib` so lint and the hook share them.

**Escape hatches.** An inline `leak-guard: allow` marker exempts one line. A small tracked path
allowlist exempts the guard's own test file (it must contain fake secrets).

**Output.** For each hit: `path:line`, rule name, and the offending line; then how to fix
(move it to `~/.gitconfig`, a local stub once the gitconfig-stub change lands, or `~/.config/dotfiles/my_*.sh`) and how to bypass
(`--no-verify`). Exit non-zero on any hit.

**Fail closed.** An unexpected exception in the guard blocks the commit with a clear message
naming the bypass.

**Bootstrap.** New `configure_leak_guard()` step, called next to `configure_vcs_author`:
1. If the repo has a `.git/`, set `core.hooksPath=githooks` when it is unset or already ours;
   warn and leave it alone if it points somewhere else.
2. If the personal denylist is missing, write a template; never overwrite an existing file.
   The template is self-explanatory for someone editing it months later: what the file is for,
   that it is untracked and per-machine, that matches block commits and pushes, the format
   (literal, `re:`, comments) with generic examples, how to test an entry
   (`leak-guard scan`), and the `--no-verify` bypass. Examples stay generic (no real names).
3. Honor `--dry-run`. A write failure (no `.git/`, read-only mount) logs a warning and never
   fails the bootstrap.

**Docs.** CLAUDE.md (Key Directories plus a short Policies note), a README line, and a
CHANGELOG entry: hook added, re-run bootstrap to enable, personal denylist optional.

## Testing

- `_pydotlib/tests/test_leak_guard.py`: diff parsing (line numbers, multiple files, binary
  skip), each rule's pass and fail paths, the `testuser` exception, inline allow, path
  allowlist, denylist parsing (comments, `re:`, missing file warns), push-range computation
  (new ref, existing ref, deletion), commit-message scanning, and fail-closed.
- `test_bootstrap.py`: `configure_leak_guard` sets the hooks path, is idempotent, leaves a
  foreign value alone, tolerates a missing `.git/`, seeds the template only when absent, and
  honors dry-run.
- `integration_checks.py`: after bootstrap, the personal denylist template exists.
- Manual: stage a line with a home path, confirm the commit is blocked; `--no-verify` passes.

## My calls (flag any you disagree with)

- Bootstrap never overwrites a `core.hooksPath` it didn't set.
- Exact token regexes are left to the builder, kept conservative to avoid noise.
