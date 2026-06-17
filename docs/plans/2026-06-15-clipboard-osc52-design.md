# Design: OSC 52 clipboard for `ccopy` / `cpaste`

**Status:** validated + review-revised (lean v1), not yet built (captured 2026-06-15).
**Goal:** Make `ccopy`/`cpaste` work over SSH and inside tmux — copying/pasting on a remote
host interacts with the *local* machine's clipboard — while keeping today's local behavior,
cross-platform on macOS / Linux / WSL.
**Architecture:** Python, logic in `_pydotlib/clipboard.py` behind thin executable `bin/`
wrappers. Native clipboard tools locally; OSC 52 escape sequence over SSH.
**Tech stack:** Python 3 stdlib only (`base64`, `binascii`, `termios`, `tty`, `select`,
`subprocess`, `argparse`, `platform`, `shutil`). Minimal stderr logging — **no** `_pydotlib`
dependency.
**Review:** adversarial review round 1 in `2026-06-15-clipboard-osc52-design-review-1.md`
(verdict NEEDS_REVISION → addressed here).

## Revision log (review round 1)
- **Correctness:** paste reply now accumulates across chunks (bounded, validated, untrusted);
  `/dev/tty` open-failure → exit 4 (no traceback); `termios` targets the `/dev/tty` fd, not
  stdin; oversized copy refuses (exit 6) instead of "succeeding" with nothing; WSL paste
  replicates the CR + trailing-newline trim on bytes.
- **Detection:** SSH gates *before* native; `detect()` takes injected `uname_release` + `which`
  (can't derive OS/WSL from env alone); predicates pinned to non-empty env; screen-under-tmux
  treated as tmux.
- **Factual fix:** `_pydotlib.cli` has no logging setup — dropped that dependency (D4); clipboard
  uses a 2-line stderr `warn()` + `print()`.
- **Lint gap:** `lint_all.py` doesn't lint `_pydotlib/*.py` today — extending it is a rollout step.
- **Trimmed to v1:** full `--check` doctor → deferred (ship only the targeted warning); screen
  DCS/chunk codec → deferred (detect + fail-fast); `.tmux.conf set-clipboard on` → dropped
  (default `external` already forwards copy).
- **CLI split (2026-06-17):** the module is a pure library (capabilities + `resolve_prefer` /
  `paste_timeout` / `default_environment`); each `bin/` script owns its own argparse, input
  plumbing, and exit-code mapping — instead of thin wrappers over a module `main()`. CLI-layer
  tests are skipped (covered by the library tests + runtime smoke).

---

## 1. Decisions (with rationale)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Copy-first, paste best-effort** | OSC 52 *copy* is well supported; OSC 52 *paste (read)* is disabled-by-default or absent on almost every terminal and never works through tmux. |
| D2 | **Copy backend: SSH→OSC 52 first, else native-if-reachable, else OSC 52** | Over SSH the native tool targets the wrong machine (incl. X11 forwarding), so SSH must gate to OSC 52 even when `xclip`/`$DISPLAY` resolve. Native (fast, unlimited, bidirectional) only for a genuinely local session. Force-overridable. |
| D3 | **Python; reusable library in `_pydotlib/clipboard.py`, CLI shell in each `bin/` script** | Logic is non-trivial (detection, base64, tmux/screen handling, size cap, tty-raw paste read) and worth unit-testing by import. `main()`/argparse/exit-codes are application glue, so they live in the scripts, not the library. |
| D4 | **No `_pydotlib` dependency; minimal stderr `warn()`/`print()`** | *(Revised — earlier premise was wrong.)* `_pydotlib/cli.py` has no logging setup (only `ColoredLogFormatter` + prompts); `weather-status` rolls its own `logging.basicConfig`. A clipboard tool's output is raw bytes + one stderr line — colored `asctime/name/level` records are wrong here. |
| D5 | **Diagnostics: quiet hot path + one targeted warning (full doctor deferred)** | An OSC 52 copy is fire-and-forget (no ack), so we can't detect *success* — only inspect config that would silently drop the sequence. A 6-category `--check` doctor is over-built for two verbs; ship the warning, defer the rest. |
| D6 | **Hidden, non-executable module; only `ccopy`/`cpaste` on `$PATH`** | The impl shouldn't be runnable/tab-completed by accident. The CLI scripts are executable; the module is a normal importable `.py`, off `$PATH`. (Symlinks rejected: exec'ing a symlink requires the *target* to be executable + on `$PATH`.) |
| D7 | **Weaken the `bin/` portability policy** (done 2026-06-15) | `bin/` scripts ship with the repo and may depend on `_pydotlib`; manual extraction is the escape hatch. See `CLAUDE.md`. (clipboard happens not to need `_pydotlib` per D4, but the structure — module + wrappers — is the policy's module-backed shape.) |

---

## 2. Research findings (so they aren't re-derived)

Verified via background research + an adversarial fact-check (empirical checks on tmux 3.5a,
GNU screen 4.08, coreutils base64 8.32). **Bottom line: ship OSC 52 for copy, do not build
on OSC 52 for paste.**

### 2.1 Copy (write) support
| Terminal | OSC 52 copy | Config |
|---|---|---|
| **Ghostty** (daily driver) | yes | none — `clipboard-write=allow` default |
| **WezTerm** (daily driver) | yes | none — write on by default |
| kitty | yes | none |
| alacritty | yes | default `OnlyCopy` permits copy |
| iTerm2 | **config** | "Applications in terminal may access clipboard" — **off by default** |
| Terminal.app | **no** | no OSC 52 at all → must use `pbcopy` locally |
| xterm | **config** | `disallowedWindowOps: 20,21,SetXprop` (not `allowWindowOps`) |
| GNOME Terminal / VTE | yes | none (VTE ≥0.50) |
| Konsole | yes | none (recent) |
| foot | yes | `osc52` default enables copy |
| Windows Terminal | yes | none since v1.6 (not legacy conhost) |
| VS Code integrated | yes (recent) | generally on; low confidence on exact gate |

> Both daily-driver terminals copy out of the box — the primary use case needs no terminal config.

### 2.2 Paste (read via `?` query) support — the blunt reality
Read is **off-by-default or absent on the overwhelming majority of setups, and tmux/screen
never forward the `?` query.** Ghostty *prompts* (`clipboard-read=ask`); WezTerm doesn't
implement read. **For this user (tmux + Ghostty/WezTerm), remote OSC 52 paste is effectively
impossible** → fail-fast with a helpful message.

**Security:** anything that can write to your tty could emit `ESC]52;c;?BEL` and read your
clipboard back — exfiltration of passwords/tokens. That's why read is disabled everywhere.
The reply is therefore **untrusted input** (see §5).

### 2.3 tmux / screen
- `set-clipboard` and `allow-passthrough` are **different mechanisms.** For clipboard yank you
  want `set-clipboard`; `allow-passthrough` is the separate raw-escape bypass — **not needed
  for OSC 52 copy.**
- `set-clipboard` values: `on` = forward to OS clipboard **and** populate tmux buffers;
  `external` (modern default) = forward to OS only; `off` = drop. **The shipped default
  `external` already forwards copy to the OS** — no tmux config needed for this feature.
- Forwarding requires the outer terminal advertise the **`Ms` terminfo extension**; else
  `set-clipboard` fills tmux buffers but never reaches the OS. Force with
  `set -ga terminal-features ',<TERM>:clipboard'`.
- tmux is **copy-only** — never answers the read `?` query.
- **screen 4.x has zero OSC 52 support**; 5.0+ added it (knobs unconfirmed). v1 detects screen
  and fails fast (see §4).
- Doctor caveat (deferred): `set-clipboard external` silently ignores app→tmux-buffer writes;
  the Ubuntu tmux OSC-52 packaging regression (launchpad #2040080 / tmux#3646) can break a
  *correct* config.

### 2.4 Portability / emitter details
- **base64:** Python stdlib (`base64.standard_b64encode`) — no subprocess, sidesteps GNU-only
  `base64 -w0`. Payload is a **single line** (no embedded newline).
- **Write to `/dev/tty`, not stdout** — reaches the controlling terminal even when stdout is
  piped, and doesn't pollute captured output.
- **Sequence:** `ESC ] 52 ; c ; <base64> <terminator>`. Always explicit `c` (CLIPBOARD).
  Terminator: **BEL** for direct terminals; **ST (`ESC \`)** inside screen's DCS wrapping.
- **In tmux: emit PLAIN** OSC 52; `set-clipboard` forwards it (no wrapping).
- **Size cap:** de-facto limit is **75000 raw bytes → 100000 base64** (hterm `OSC_52_MAX_SEQUENCE`
  = 99992; ≈74994 raw). Terminals **silently drop** oversized sequences → we refuse (see §4).

---

## 3. Architecture & layout

```
_pydotlib/clipboard.py        # reusable library (capabilities + resolvers); stdlib-only; NOT executable
bin/ccopy                     # CLI: argparse + input plumbing (-f/text/stdin) + exit codes → clipboard.copy()
bin/cpaste                    # CLI: argparse + exit codes → clipboard.paste(), writes stdout
_pydotlib/tests/test_clipboard.py
```

Each `bin/` script is a small program that bootstraps `sys.path` (via `$S_DOTFILE_ROOT` or its
own `__file__`), imports the library, parses its own args, and calls in:

```python
#!/usr/bin/env python3
import argparse, os, pathlib, sys
_root = os.environ.get("S_DOTFILE_ROOT") or str(pathlib.Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
from _pydotlib import clipboard  # noqa: E402  (path set above)

def main(argv: list[str]) -> int:
    ...  # argparse → read input → clipboard.copy()/paste() → map exit codes

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

**Library public surface** (capabilities only — no CLI; the scripts own argparse/exit codes):

- `detect(env, *, system, release, which) -> Environment` — pure. `env` is `os.environ`-like;
  `system`/`release` are `platform.system()`/`platform.uname().release` (the latter for WSL
  detection); `which` is `shutil.which`. Returns `is_ssh`, `is_tmux`, `is_screen`, `is_mosh`,
  `os` (mac/linux/wsl), the resolved native copy/paste argv, `$TERM`/`$TERM_PROGRAM`.
  `default_environment()` builds one from the real process state.
- `choose_backend(env, verb, prefer) -> str` — pure backend decision.
- `copy(data: bytes, env, *, prefer=None, …) -> int` — picks backend, encodes, writes; exit code.
- `paste(env, *, prefer=None, timeout=5.0, …) -> tuple[int, bytes]` — exit code + bytes to emit.
- `encode_osc52(data, *, target=b'c', terminator=b'\a') -> bytes` — pure.
- `parse_osc52_reply(buf: bytes) -> bytes | None` — pure; decodes a complete reply or `None`.
- `resolve_prefer(cli_value) -> str | None`, `paste_timeout() -> float` — flag/env resolvers
  shared by both scripts.
- exit-code + backend constants (`EXIT_*`, `BACKEND_*`). The targeted misconfig warning is the
  internal `_osc52_warnings(env, run)`.

Backends behind a common shape: **native** (`pbcopy`/`pbpaste`, `wl-copy`/`wl-paste`,
`xclip`/`xsel`, `clip.exe`/`powershell.exe`) and **osc52** (encode + write to `/dev/tty`;
read via tty raw mode).

---

## 4. Detection & copy path

`detect()` ordering inputs, then `ccopy` backend choice:
1. **Forced?** `--osc52`/`--native` flag or `CLIPBOARD_BACKEND=native|osc52|auto` → honor.
   A forced backend that's unreachable (e.g. `--native` on a headless SSH host) → **exit 4**
   naming the backend; never silently fall back.
2. **SSH? → OSC 52** (even if `xclip`/`$DISPLAY` resolve — the native target is the wrong machine).
   `is_ssh := bool(SSH_TTY or SSH_CONNECTION or SSH_CLIENT)`.
3. **Local + native writer + usable display?** → native:
   macOS `pbcopy`; WSL `clip.exe`; Linux Wayland (`$WAYLAND_DISPLAY`) `wl-copy`;
   Linux X11 (`$DISPLAY`) `xclip -selection clipboard` / `xsel -ib`.
4. **Else** → OSC 52.

OSC 52 emit:
- stdlib-base64 → `ESC]52;c;<b64>BEL`. **In tmux: emit plain** (rely on `set-clipboard`).
- Write to `/dev/tty`. **Open in `try/except OSError`** (ENXIO under sudo/cron/CI/containers) →
  **exit 4** with stderr `"no controlling terminal; cannot emit OSC 52"`; never traceback.
- **Size cap:** if `len(data) > OSC52_MAX_RAW` (named constant ≈75000, commented terminal-dependent),
  **do not emit** → **exit 6** `"payload too large for OSC 52 (N bytes > cap)"`. OSC52-path-only;
  native has no cap.
- **screen** (`$STY` set, `$TMUX` not) → v1 **fails fast**: exit 4 `"screen OSC 52 unsupported;
  use tmux or a native clipboard"`. (DCS/chunk codec deferred — see §10.)

Targeted warning (hot path) fires **only when the OSC 52 backend is selected** and the path is
detectably broken: in tmux with `set-clipboard off`, or `Ms` not advertised → one stderr line
with the fix. (Keyed on backend, not on `is_ssh`.) `mosh` detected → lower-confidence note.

---

## 5. Paste path

`cpaste` backend choice mirrors copy (forced? → SSH? → native → osc52), for reading:
1. **Native reader** (local): `pbpaste`; `wl-paste`; `xclip -o -selection clipboard` / `xsel -ob`;
   WSL `powershell.exe Get-Clipboard` *(was `pwsh`; `powershell.exe` is present on stock WSL —
   see §10)*.
   - **WSL byte transform** (matches today's `sed 's/\r$//' | head -c -1`): on **bytes**, replace
     `b'\r\n'`→`b'\n'`, then strip exactly one trailing `b'\n'`. No decode (non-UTF-8 safe).
2. **In tmux → do not attempt** OSC 52 read (query never forwarded) → **exit 5** with message.
3. **Remote (or no native reader), not tmux → best-effort OSC 52 read:**
   - Open `/dev/tty` `O_RDWR` once. Apply raw + no-echo via `termios`/`tty` to **that fd**
     (`tcgetattr`/`tcsetattr(TCSANOW)`); **never touch fd 0**. **Restore that fd in `finally`**
     on every exit path.
   - Write `ESC]52;c;?BEL` to the tty.
   - **Accumulation loop:** `deadline = monotonic + timeout`; loop `select()` on remaining time,
     append reads to a buffer, stop when the buffer holds the terminator (BEL or ST) after the
     `ESC]52;c;` prefix **or** the deadline passes. Enforce a **hard byte ceiling** (~1 MB) →
     abort as no-reply (bounds memory; reply is untrusted, §2.2).
   - `parse_osc52_reply()`: validate the strict `ESC]52;c;<base64><terminator>` shape, slice the
     payload, `base64.b64decode(..., validate=True)`; `binascii.Error` → treat as no-reply.
   - Write **only decoded bytes** to stdout; never re-emit to the tty.
   - No reply / timeout / unsupported → **exit 5** `"remote paste isn't supported by this
     terminal; use Ctrl/Cmd-Shift-V or a tmux paste-buffer."`
4. Successful empty paste → exit 0, no stdout (distinct from the exit-5 timeout case).

Timeout configurable via `CLIPBOARD_PASTE_TIMEOUT_MS` (default 5000; high enough to approve a
terminal's clipboard-read prompt — Ghostty/kitty ask by default — and ~free on the no-reply path
since it's a blocking `select()` wait, not a spin). WAN SSH may want more.

Honest expectation for tmux + Ghostty/WezTerm: remote paste hits the exit-5 message (correct,
non-hanging). The read path mainly helps the no-tmux SSH case on a read-capable terminal.

---

## 6. Diagnostics (v1: targeted warning only)

v1 ships **only** the hot-path warning, built from pure check functions (so it's testable and
reusable). Fires when the OSC 52 backend is selected and:
- tmux `set-clipboard` is `off` (`tmux show -gv set-clipboard`), or
- `Ms` not advertised by the outer terminal (`tmux show -gv terminal-features` / `infocmp`), or
- `mosh` detected (lower-confidence wording).

One stderr line, with the fix. Static advisory hints (iTerm2 clipboard toggle off by default;
Terminal.app has no OSC 52) live in **README troubleshooting**, not code.

**Deferred** (§10): the full `--check`/`--doctor` (environment summary, native-backend probe,
`on` vs `external` distinction, screen-version check, the tmux packaging-regression note).

---

## 7. CLI surface & errors

- `ccopy [-f FILE] [text…]` — input precedence `-f` > positional args > stdin (as today).
  No args + **tty** stdin → usage + **exit 2** (no more hang-on-EOF); no args + piped stdin → read it.
  `-c/--clear` empties the clipboard (ignores input, bypassing the empty-input guard).
- `cpaste` — writes clipboard to stdout. (`-f`/`-c` are **ccopy-only**.)
- Shared opts: `--osc52` / `--native` (force, **mutually exclusive**), `-v/--verbose` (logs the
  chosen backend), `-V/--version`, `-h/--help` (**exits 0**). Both carry a help `epilog`
  documenting the auto default, the env vars, paste-best-effort, the args-in-shell-history
  caveat, and the exit-code legend.
- Env: `CLIPBOARD_BACKEND=auto|native|osc52` (default `auto`; set-but-invalid → warn + auto);
  `CLIPBOARD_PASTE_TIMEOUT_MS` (5000).
- Text input (`-f`/positional) decoded/encoded as **UTF-8** with an explicit errors policy.
- **Empty-input copy → refuse, exit 2** (avoids `ESC]52;c;BEL` = accidental clipboard-clear;
  use `--clear` to clear deliberately).

**Exit codes:**
| Code | Meaning |
|---|---|
| 0 | success |
| 2 | usage error (bad opt, empty-input copy, ccopy no-arg on a tty) |
| 3 | input file missing (`-f`) |
| 4 | no usable backend / no controlling tty / forced backend unreachable / screen |
| 5 | remote paste unsupported (in tmux, or timeout/no reply) |
| 6 | payload too large for OSC 52 |

**Deferred:** `--primary`/`-p` (target `p`). **Dropped:** a `clipboard <verb>` subcommand
entrypoint — the two wrappers are the interface.

---

## 8. Testing plan

`_pydotlib/tests/test_clipboard.py` — `from _pydotlib.clipboard import …`; all dependency-injected
(no real clipboard/terminal):
- `detect()` — table-driven over env dicts **plus injected `uname_release` + fake `which`**:
  ssh-gates-before-native, mac/linux/wsl (via `uname_release`), Wayland vs X11 display present/absent,
  empty `$TMUX`, screen-under-tmux (`$TMUX` set, `TERM=screen*` → tmux), forced override.
- backend selection — asserts native-vs-osc52 + exact command per env.
- `encode_osc52()` — exact bytes: base64 correctness, explicit `c`, plain-in-tmux (no wrap),
  BEL terminator; `encode_osc52(b'')` contract (refused upstream); boundary at `OSC52_MAX_RAW`.
- copy failure paths — failing `/dev/tty` opener → exit 4 + message; oversized → exit 6; forced
  unreachable native → exit 4; screen → exit 4.
- native argv per OS (mock `subprocess`); **WSL paste** `b'foo\r\nbar\r\n'` → `b'foo\nbar'`.
- `parse_osc52_reply()` — replies in 1, 2, and N chunks; terminator in a later chunk; garbage;
  oversized (ceiling); embedded control chars; non-base64 → `None`.
- paste with non-tty stdin pipe (termios must not touch fd 0); timeout → exit 5; in-tmux → exit 5.
- `main()` — verb routing (from passed verb) + every exit code.

Run via `python3 run_tests.py` (auto-discovered). Lint per §9.

---

## 9. Rollout / migration

1. Add `_pydotlib/clipboard.py`; replace `bin/ccopy` & `bin/cpaste` (sh) with the identical
   Python wrappers.
2. Drop the stray `# vim: set filetype=python` modeline.
3. **Extend `lint_all.py` to discover `_pydotlib/*.py` in the *fatal* py pass** — today it only
   lints `["lint_all.py", "bootstrap.py"]` (fatal) + `bin/` py (non-fatal warning), so
   `clipboard.py` would otherwise go unchecked. Verify the wrapper's post-`sys.path` import is
   clean under ruff/ty (the `# noqa: E402` is in place).
4. Local behavior is unchanged for the common paths (still `pbcopy`/`xsel`/…); OSC 52 over SSH is
   additive. Minor user-visible deltas → CHANGELOG: SSH/OSC 52 copy support added; `cpaste -h`
   now exits 0; empty-input copy now refuses; `ccopy` with no input on an interactive tty now
   prints usage instead of waiting on EOF; WSL paste uses `powershell.exe` (was `pwsh`).
5. **`.tmux.conf`: no change** — the default `set-clipboard external` already forwards copy to
   the OS clipboard. README documents this and the `Ms`/`terminal-features` knob if needed.
6. `README.md`: SSH/OSC 52 behavior, `CLIPBOARD_BACKEND` / `CLIPBOARD_PASTE_TIMEOUT_MS`, and a
   troubleshooting section (iTerm2 toggle, Terminal.app, tmux `set-clipboard`/`Ms`, mosh).
7. Confidentiality: generic clipboard/terminal/tmux content only — nothing internal.

---

## 10. Open questions / deferred
- **WSL paste backend** — `powershell.exe` (present on stock WSL, chosen default) vs `pwsh`
  (PowerShell Core, faster, not always installed). Confirm the swap or keep `pwsh` with a fallback.
- **Full `--check`/`--doctor`** — deferred; v1 ships only the targeted warning.
- **screen OSC 52 codec** — deferred; v1 fails fast. Add per hterm only if screen is used: split
  *only the base64* so `len(b'\033P') + chunk + len(b'\033\\') <= 256`, one `ESC P … ESC \` per
  chunk; assert exact bytes across the boundary.
- **`set-clipboard on`** — a separate opt-in (adds tmux-buffer population), not part of this feature.
- **`--primary`/`-p`** — deferred until needed.
- **Live smoke test** — once built, verify end-to-end from both daily-driver terminals, inside and
  outside tmux, over a real SSH session. Doc-derived matrices are no substitute for one real
  (terminal × tmux) round-trip.

---

## 11. References
- hterm `osc52.sh` (canonical emitter: format, base64 idiom, tmux/screen wrapping, 252 B chunking).
- tmux 3.5a man page (`set-clipboard`, `allow-passthrough`, `Ms` terminfo requirement).
- Neovim built-in OSC 52 provider (copy-only stance; pure-language base64).
- Ubuntu/tmux OSC 52 regression: launchpad #2040080 / tmux#3646.
