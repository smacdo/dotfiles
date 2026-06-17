# Design Review 1 — `ccopy`/`cpaste` OSC 52 design

Adversarial review of `2026-06-15-clipboard-osc52-design.md` by four independent lenses
(simplicity, correctness, assumptions-vs-repo, detection/testability/security) + synthesis.

VERDICT: NEEDS_REVISION

## Summary Assessment
The core architecture (copy-first, native-local/OSC52-remote, stdlib base64 to `/dev/tty`,
fail-fast paste) is sound and well-researched, but the design has one true correctness
blocker — the paste reply read does not accumulate across split/partial reads — plus a
cluster of unspecified failure paths (no `/dev/tty` fallback, which fd termios targets,
oversized/empty payload exit codes, WSL trailing-newline regression) that will produce
silent wrong behavior. Two doc claims are factually wrong against the repo (`_pydotlib.cli`
exposes no logging setup; `clipboard.py` won't be linted by `lint_all.py`), and the
detection heuristic is under-specified in the exact cases that matter (local-tmux-over-SSH,
empty `$TMUX`, screen-under-tmux, pure-env WSL detection). All fixable in the doc before
building.

## Critical Issues (must fix before building)

1. **Paste reply read is single-shot and will truncate any non-trivial clipboard.**
   Section 5 specifies one `select()` + one read. A multi-KB base64 reply arrives in multiple
   chunks and the terminator can land in a later read; `b64decode` on a partial quantum
   raises.
   **Fix:** Rewrite §5 step 3 as an accumulation loop: `deadline = now + timeout`; loop
   `select()` against remaining time, append to a buffer, stop when the buffer contains the
   terminator (BEL or ST) after the `ESC]52;c;` prefix **or** the deadline passes; only then
   slice and `b64decode(validate=True)`, treating `binascii.Error` as no-reply. Add a
   `parse_osc52_reply()` test covering replies in 1, 2, and N chunks and the terminator in a
   separate chunk. Add a hard read ceiling (Major #7).

## Major Issues (should fix)

1. **`/dev/tty` open failure has no defined fallback or exit code.** `open('/dev/tty')` raises
   ENXIO under sudo/cron/CI/systemd/containers — exactly the SSH-automation target — and
   OSC 52 is the chosen backend there, so copy tracebacks or silently no-ops.
   **Fix:** §4 wrap the open in try/except OSError → **exit 4** with stderr `"no controlling
   terminal; cannot emit OSC 52"` (never traceback). Add the no-tty→4 row to the §7 table and
   a test injecting a failing tty-opener.

2. **termios raw mode must target the `/dev/tty` fd, not stdin.** If applied to fd 0,
   `tcgetattr(0)` raises ENOTTY when stdin is piped, and echo-suppression races the reply read
   on a different fd.
   **Fix:** §5: open `/dev/tty` `O_RDWR` once; apply raw+noecho `tcsetattr(TCSANOW)` to **that**
   fd; read the reply from it; restore it in `finally`; never touch fd 0. Add a test running
   paste with a non-tty stdin pipe.

3. **Doc claims `_pydotlib.cli` provides logging — it does not.** Verified: `_pydotlib/cli.py`
   exposes only `ColoredLogFormatter`, `input_field`, `confirm` — no `getLogger`/`basicConfig`/
   setup. `bin/weather-status:267` wires its own `logging.basicConfig(...)` and ignores cli.py.
   Colored `asctime - name - levelname` records are wrong for a tool whose output is raw bytes
   + one stderr warning.
   **Fix:** Rewrite D4 (and tech-stack line, layout line). Drop the cli logging dependency; use
   a 2-line `warn()` + `print()` like weather-status. Remove the "first bin/ command to dogfood
   the shared library" framing.

4. **`clipboard.py` will not be linted or typechecked.** Verified: `lint_all.py:20`
   `DOTFILES_PY_SCRIPTS = [basename(__file__), "bootstrap.py"]` (fatal); line 285 globs only
   `bin/` for py scripts (line 287-290 non-fatal warning); nothing walks `_pydotlib/*.py`.
   **Fix:** Add an explicit §9 rollout step extending `lint_all.py` to discover `_pydotlib/*.py`
   in the *fatal* py pass. Note the wrapper's `sys.path.insert` + `from _pydotlib import
   clipboard` may trip ruff E402 / ty unresolved-import; pre-clear empirically or with `# noqa`.

5. **Oversized payload returns success (0) while copying nothing.** Warning to stderr then
   still emitting yields warning + unchanged clipboard + exit 0.
   **Fix:** §4 + §7: on the OSC52 path, if raw bytes exceed the cap, **do not emit** → exit 6
   "payload too large for OSC 52". OSC52-path-only (native has no cap). Named constant. Fix the
   arithmetic: **75000 raw → 100000 base64** (74994 → 99992).

6. **WSL paste CR-strip regresses the trailing-newline trim.** Today `bin/cpaste:44` is
   `pwsh Get-Clipboard | sed 's/\r$//' | head -c -1` — strips CR **and** drops the final
   newline. "strip trailing `\r`" alone leaves a spurious `\n`.
   **Fix:** §5 exact byte transform: `b'\r\n'`→`b'\n'`, then strip exactly one trailing `b'\n'`,
   on **bytes**. Decide `pwsh` vs `powershell.exe` deliberately. Test `'foo\r\nbar\r\n'` →
   `'foo\nbar'`.

7. **Paste-read path is untrusted input with no size bound.** Reply is attacker-influenceable
   within the window; a huge crafted reply blows memory.
   **Fix:** §2.2/5: cap bytes read from `/dev/tty` (hard ceiling ~1-2 MB, abort otherwise; also
   bounds Critical #1); validate strict `ESC]52;c;<base64><terminator>` shape +
   `b64decode(validate=True)`; write only decoded bytes to stdout, never re-emit to tty. Tests
   for garbage / oversized / embedded-control-char replies.

8. **Detection picks the wrong clipboard for local-tmux-over-SSH; unspecified for empty env /
   screen-under-tmux / WSL.** (Design itself flags local-tmux as an open question and never
   answers it.)
   **Fix:** Rewrite §3 `detect()` + §4 ordering:
   - **SSH gates first:** if `is_ssh`, choose OSC 52 even when `xclip`/`$DISPLAY` resolve (over
     SSH the native target is the wrong machine, incl. X11 forwarding). Native only when **not**
     SSH **and** a native tool **and** a usable display.
   - **Pin predicates** (repo precedent `functions.sh:346`): `is_tmux := bool(env.get("TMUX"))`,
     `is_ssh := bool(env.get("SSH_TTY") or env.get("SSH_CONNECTION") or env.get("SSH_CLIENT"))`.
   - **screen-under-tmux:** `$TMUX` set ⇒ treat as tmux, emit PLAIN regardless of `TERM`; detect
     screen via `$STY`, not `TERM`.
   - **WSL is not pure-over-env:** repo uses `uname -r` match `*microsoft*` (`functions.sh:52`).
     Change signature to inject ambient facts:
     `detect(env, *, uname_release: str, which: Callable[[str], str|None]) -> Environment`;
     wrapper supplies `os.environ`, `platform.uname().release`, `shutil.which`; tests supply fakes.
   - Note SSH detection is best-effort / not load-bearing; key the hot-path warning on "OSC52
     backend selected," not on `is_ssh`.

9. **`.tmux.conf` → `set-clipboard on` is an unjustified user-noticeable change the design's own
   analysis contradicts.** Research §2.3 + §10 say the shipped default `external` **already**
   forwards app OSC 52 to the OS clipboard; `on` only adds tmux-buffer population, unused here.
   **Fix:** §9 step 4: do **not** modify `set-clipboard` in v1; document that `external`
   suffices. Resolve §10's open question to "leave `external`." `on` is a separate opt-in.

## Minor / Polish
- **Doctor / `--check` is over-built (YAGNI)** for a 2-verb tool. Ship only the targeted
  hot-path warning in v1 (tmux `set-clipboard off` / `Ms` missing); defer the full doctor; move
  static advisory hints (iTerm2 toggle, Terminal.app) to README troubleshooting; drop `--doctor`
  alias. If kept, name its result type distinctly (e.g. `ClipboardCheck`) — CLAUDE.md's
  integration-test isolation policy forbids importing `integration_checks.CheckResult`.
- **Public surface bloat.** The public surface is `main(verb, argv) -> int`; `detect`/`copy`/
  `paste`/`diagnose` are impl details tested because pure, not API. `CopyResult` is questionable
  given copy is fire-and-forget — collapse `CopyResult`/`PasteResult`.
- **Defer screen entirely in v1.** User is tmux + Ghostty/WezTerm; screen 4.x has zero OSC 52.
  Detect `is_screen` → fail-fast; add the DCS/chunk codec only when screen is actually used. If
  kept, pin exactly what is chunked (per hterm: split only the base64 so
  `len(b'\033P') + chunk + len(b'\033\\') <= 256`, one `ESC P … ESC \` per chunk) and assert
  exact bytes across the boundary.
- **Paste timeout vs in-tmux exit codes.** Timeout-with-no-reply → exit 5 (distinct from
  successful empty paste = exit 0, no stdout). Make the 300 ms timeout configurable (too short
  over WAN SSH).
- **Empty-input copy contract undefined.** `b64encode(b'')` → `ESC]52;c;BEL` = "clear clipboard"
  on some terminals. Decide: refuse (exit 2) or intentionally clear. Add `encode_osc52('')` test.
- **`cpaste -h` / `-f`.** §7's blanket "keeps `-f`/`-V`/`-h`" is wrong for cpaste: `bin/cpaste:27`
  `-h` does `exit 1`; cpaste has no `-f`. Clarify `-f` is ccopy-only; decide whether to normalize
  cpaste `-h`→0 (noticeable → CHANGELOG note).
- **`ccopy` no-args with tty stdin blocks on EOF forever.** If no `-f`/args and
  `sys.stdin.isatty()`, print usage + exit 2 (or a "Ctrl-D to finish" hint).
- **Wrapper snippet hardcodes `"copy"` for both wrappers.** Show both explicitly or derive the
  verb from `pathlib.Path(sys.argv[0]).name`.
- **Delete the deferred "clipboard <verb> subcommand"** — mark rejected, not deferred.
- **mosh:** warn on the copy hot path when detected, but lower-confidence language (`MOSH_*` is
  often cleared before the login shell).
- **Forced-but-unreachable native** (`--native` on headless SSH) → exit 4 naming the forced
  backend; do not silently fall back.
- **Text-input encoding:** state UTF-8 (with an errors policy) for `-f`/positional args.

## Verified Claims (repo-grounded)
- `_pydotlib/cli.py` exposes only `ColoredLogFormatter`, `input_field`, `confirm` — no logging
  setup (grep across `_pydotlib/*.py` returns nothing).
- `bin/weather-status:267` uses `logging.basicConfig(...)` and ignores cli.py.
- `lint_all.py` lints only `DOTFILES_PY_SCRIPTS` (fatal) + `bin/` py (non-fatal warning); nothing
  walks `_pydotlib/*.py` → `clipboard.py` would be unlinted.
- `bin/cpaste:27` `-h` exits 1; cpaste has only `-h`/`-V` (no `-f`); uses `pwsh ... | sed 's/\r$//'
  | head -c -1`.
- `bin/ccopy:6`/`cpaste:6` carry the `# vim: set filetype=python` modeline; §9.2's plan to drop it
  is accurate.
- `bin/ccopy` precedence `-f` > args > stdin, exit 3 on missing file, exit 2 on bad opt/platform.
- No Python OS/WSL detection helper exists in `_pydotlib`; WSL detection lives only in
  `functions.sh` via `uname -r` match → `detect()` cannot be pure-over-env for the OS/WSL axis.
- `test_clipboard.py` can use plain `from _pydotlib.clipboard import …` (siblings do this);
  `SourceFileLoader` is only needed for extensionless `bin/` scripts.

## False Positives Dropped
- "Reconsider whether the module needs `_pydotlib` at all / single bin script keeps portability" —
  re-litigates accepted D3/D6; only the over-broad D7 framing is actionable (Major #3).
- "ty/ruff may flag the import / E402" — speculative; folded into Major #4 as a pre-clear note.
- "SSH detection unreliable inside tmux" as standalone — subsumed by Major #8.
