# Plan: Claude Code state icons in tmux window tabs

**Status:** Planned, not built (captured 2026-06-15). Skip-to [Build plan](#build-plan).

**Goal:** Show a per-window tmux tab icon reflecting what Claude Code is doing in
that window — busy, running a command, long-running, waiting for input, idle —
color-coded, instant, and with near-zero idle cost.

**Architecture:** Claude Code hooks *push* a per-window tmux user option
(`@claude_state`); `window-status-format` renders an icon+color from it via a
`#{?...}` conditional. No polling, no daemon.

**Tech stack:** POSIX sh helper (`bin/`), tmux 3.5a format language, Claude Code
hooks (`~/.claude/settings.json`), `bootstrap.py` for reproducible hook install.

---

> **See also:** [`claude-code-hooks-and-statusline.md`](claude-code-hooks-and-statusline.md)
> — the observed Claude Code hook lifecycle + status-line behavior this feature
> relies on (event firing order, `background_tasks` at `Stop`, `idle_prompt`
> semantics, subagent/orchestration events). Captured 2026-06-25.

## Why this design (investigation summary)

Chosen after a 3-agent investigation (empirical tmux testing + doc-grounded hook
mapping + prior-art survey). Findings worth keeping so we never re-research them:

- **PUSH via per-window user option is the cleanest mechanism** (empirically the
  winner over pull/`#()`, pane-border, and window-rename). The external program
  runs `tmux set -w -t "$TMUX_PANE" @claude_state busy`; the format reads it.
  - Resolves **per-window** correctly in the real status bar.
  - **Instant: in tmux 3.5a, `set -w @opt` triggers a client redraw on its own** —
    no `refresh-client -S` needed.
  - **Zero idle cost** — no shell spawns, no polling. (The `#()` pull alternative
    spawns a shell *per window per status tick forever*.)
  - Target by `$TMUX_PANE` (resolves to its window), **never window index** —
    index churn is unreliable.
- **Long-running elapsed is computable in pure tmux 3.5a format math — no helper
  script.** `%s` (strftime "now") composes with `#{e|-:...}` and `#{e|>:...}` in
  one expansion pass: `#{e|-:%s,#{@claude_since}}` = elapsed seconds;
  `#{?#{e|>:#{e|-:%s,#{@claude_since}},30},SLOW,BUSY}` escalates after 30s. There
  is **no `#{now}` primitive**; the `*_activity` epochs mean *last activity*, not
  now (a trap — they give negative elapsed).
- **Measurement gotcha for future tmux debugging:** `display-message -p
  '#{T:status-format[0]}'` does **not** await async `#()` jobs and renders them
  empty. Observe the real client screen (e.g. a `script(1)`-attached pty), not
  `display-message`, when testing `#()`.
- **pane-border-format** reads per-pane options but **does not redraw on option
  change** (only on layout/resize) — unusable for live state. **window-rename /
  OSC 2 title** consumes the name channel and fights `automatic-rename`. Both
  rejected.
- **Hooks can run `tmux` and read `$TMUX_PANE`** (proven by the existing
  `notify-gchat.sh`). `tmux set-option` is atomic, so it sidesteps the file-race a
  state-file approach would have under parallel hooks.
- **`Notification` distinguishes `idle_prompt` (waiting for you) from
  `permission_prompt` (needs approval)** via its matcher — so needs-input and
  needs-permission are separable.
- **Scheduled waits are NOT observable.** `/loop`, `/schedule`, `ScheduleWakeup`
  fire no hook and expose no env var — "waiting for a scheduled wakeup" cannot be
  distinguished from idle at the hook level (by design). See [Deferred](#deferred--out-of-scope).
- **`SessionEnd` does not fire on crash/SIGKILL** — drives the crash-cleanup
  design below.
- **The statusLine JSON is a richer second source** (model, ctx%, cost, effort,
  current tool) but goes quiet on idle — good for detail, bad for the idle edge.
  Not used in Phase 1.

---

## States and hook mapping

`done` is **not** distinguishable from `idle` (`Stop` = "finished this turn /
waiting for you"), so they collapse into one **idle** state.

| State | Trigger (hook → `claude-tmux-state <arg>`) | Default glyph | Default color |
|---|---|---|---|
| present | `SessionStart` → `present` | (none / faint dot) | dim |
| busy (generating) | `UserPromptSubmit`, `PostToolUse` → `busy` |  | yellow |
| running a command | `PreToolUse` matcher `Bash` → `running` |  | cyan |
| long-running ("slow") | derived in-format from `running` + elapsed > 30s |  | orange |
| needs input | `Notification`/`idle_prompt` → `needs-input` |  | red |
| needs permission | `Notification`/`permission_prompt` → `needs-perm` |  | red/magenta |
| idle / done | `Stop` → `idle` | (none) | dim/green |
| (gone) | `SessionEnd` → `clear` | — | — |

Glyphs are Nerd-Font placeholders — finalize at build time. Color matters more than
glyph in a row of tabs.

---

## Decisions (settled)

1. **Mechanism:** hook → `tmux set -w -t "$TMUX_PANE" @claude_state` push; icon via
   `window-status-format` conditional. (Confirmed.)
2. **Color-coded**, per the table above.
3. **Only inside tmux** — helper no-ops when `$TMUX` is unset.
4. **Multi-pane:** first Claude in a window **owns** the icon (`@claude_owner` =
   owning pane id); extra Claudes in the same window **no-op**. Released on
   `SessionEnd`; takeover allowed when the owner is gone/stale. Fallback if
   ownership proves fragile: last-writer-wins (acceptable — rare one-offs).
5. **Active tab:** show the state on the focused tab too, **dimmed** (you can see
   Claude directly when focused). Same conditional in `window-status-current-format`.
6. **Crash cleanup (layered, no polling):**
   - `Stop` resets busy/running→idle every turn (so a stuck *active* icon only
     happens on a mid-work crash).
   - `SessionEnd` clears on normal exit / `/clear` / `/logout` / API error.
   - **Clear-on-`SessionStart`** wipes stale state when Claude restarts in the pane.
   - **Transient-only TTL:** stamp `@claude_since`; in the format, hide/dim a
     *transient* state (busy/running) older than ~10–15 min. **Never** TTL
     idle/needs-input (those legitimately persist for hours).
   - Bulletproof liveness needs per-window process polling → rejected (CPU). The
     above bounds a crash-stuck icon to a dimmed glyph for a few minutes.
7. **Long-running** ("slow") is **in Phase 1** — it's nearly free (in-format math
   off `@claude_since`). At the default 15s `status-interval` it flips to "slow"
   within ≤15s of crossing the threshold, with **no** added cost. Snappier
   escalation needs a lower interval → tied to the spinner work (Phase 2).
8. **Retire the bell** once needs-input ships: remove `preferredNotifChannel:
   terminal_bell` from `settings.json`. ⚠️ This also drops the *audible* ping (the
   icon is visual-only) — keep the bell if you still want sound.
9. **Reproducibility:** extend `bootstrap.py` `configure_claude_code()` to merge
   the hooks idempotently. ⚠️ That function likely needs a small rework first
   (currently it only sets EDITOR + statusLine) — treat as a sub-task.
10. **"Waiting for external event" is opt-in/explicit, not auto-detected** (Phase 3).

---

## Components / files

| File | Action | Notes |
|---|---|---|
| `bin/claude-tmux-state` | new | POSIX sh, no extension, kebab-case, `chmod +x`, stdlib-portable per `bin/` policy. Sets/clears `@claude_state`/`@claude_since`/`@claude_owner`. No-op outside tmux. |
| `.tmux.conf` | modify | Add `@claude_state` icon+color chain to `window-status-format` *and* `window-status-current-format` (dimmed). Long-running + transient-TTL conditionals. |
| `~/.claude/settings.json` | modify (via bootstrap) | Wire SessionStart/UserPromptSubmit/PreToolUse(Bash)/PostToolUse(Bash)/Notification/Stop/SessionEnd → `claude-tmux-state`. |
| `_pydotlib/bootstrap.py` | modify | Extend `configure_claude_code()` to idempotently merge our hooks. |
| `_pydotlib/tests/test_bootstrap.py` | modify | Unit tests for the hook merge (idempotent; preserves existing hooks). |
| `CHANGELOG.md` | modify | Entry when shipped. |
| `README.md` | modify | Document the feature + bell retirement. |

### Helper skeleton (`bin/claude-tmux-state`)

```sh
#!/bin/sh
# Push Claude Code's per-window state to a tmux user option for the tab icon.
# Usage: claude-tmux-state <present|busy|running|needs-input|needs-perm|idle|waiting|clear>
set -eu
[ -n "${TMUX:-}" ] || exit 0          # only inside tmux
pane="${TMUX_PANE:-}"; [ -n "$pane" ] || exit 0
state="${1:-}"; [ -n "$state" ] || exit 0

owner="$(tmux show-option -wqv -t "$pane" @claude_owner 2>/dev/null || true)"

if [ "$state" = clear ]; then
    [ -z "$owner" ] || [ "$owner" = "$pane" ] || exit 0   # only owner releases
    for o in @claude_state @claude_since @claude_owner; do
        tmux set -wu -t "$pane" "$o" 2>/dev/null || true
    done
    exit 0
fi

if [ -z "$owner" ]; then
    tmux set -w -t "$pane" @claude_owner "$pane"          # claim a free window
elif [ "$owner" != "$pane" ]; then
    exit 0                                                 # another Claude owns it
fi

tmux set -w -t "$pane" @claude_state "$state"
tmux set -w -t "$pane" @claude_since "$(date +%s)"
```

### tmux format technique (representative — full chain built at impl time)

```tmux
# elapsed-in-current-state seconds:  #{e|-:%s,#{@claude_since}}
# long-running escalation (running > 30s -> slow):
#   #{?#{&&:#{==:#{@claude_state},running},#{e|>:#{e|-:%s,#{@claude_since}},30}}, <slow>, <running>}
# transient-only staleness (busy/running older than 900s -> hide):
#   #{?#{e|>:#{e|-:%s,#{@claude_since}},900}, <hidden>, <icon>}
```

### bootstrap hook merge (approach)

`configure_claude_code()` gains: for each owned (event, matcher, command) — where
command invokes `claude-tmux-state` — ensure a matching hook entry exists in
`settings["hooks"][event]`; append if absent; never duplicate; never touch
unrelated hooks. Identify ours by the `claude-tmux-state` substring in the command.
Idempotent on re-run.

---

## Build plan

### Dependency groups

| Group | Steps | Parallel? |
|---|---|---|
| 1 | Step 1 (helper) | — |
| 2 | Step 2 (.tmux.conf icons) ‖ Step 3 (bootstrap merge + tests) | Yes (independent files) |
| 3 | Step 4 (wire hooks) | No (needs 1 + 3) |
| 4 | Step 5 (crash cleanup + ownership polish), Step 6 (retire bell) | After verify |
| 5 | Step 7 (end-to-end verification) | Last |

### Phase 1 — core state icons

**Step 1 — `bin/claude-tmux-state` helper.** Write the script above; `chmod +x`.
Verify: `lint_all.py` (shellcheck) passes; `TMUX= claude-tmux-state busy` no-ops;
in a scratch server `tmux -L s new-session -d; TMUX=... ` sets `@claude_state`
(read back with `show-option -wqv`). Add a `_pydotlib`/subprocess test driving it
against `tmux -L claudetest` (set → read back → clear), killing the scratch server
after.

**Step 2 — `.tmux.conf` icon+color chain.** Prepend the `#{?@claude_state}`
conditional (with long-running + transient-TTL) to both `window-status-format`
(line ~91) and `window-status-current-format` (line ~106, dimmed). Verify in a
scratch tmux: set each state on background windows, confirm the right glyph/color
renders and resolves per-window; confirm "slow" appears after 30s; confirm a
forced-old `@claude_since` hides a transient state.

**Step 3 — bootstrap hook merge.** Extend `configure_claude_code()` (rework as
needed); add idempotent merge of the Phase-1 hooks. TDD in `test_bootstrap.py`:
(a) merges into empty hooks; (b) preserves existing unrelated hooks; (c) no-dupe on
second run. `python3 run_tests.py --no-docker`.

**Step 4 — wire the hooks.** Run `bootstrap.py` to install the hooks into
`settings.json`; or hand-add for testing. Events per the [mapping table](#states-and-hook-mapping).
Notification branches on reason (idle_prompt vs permission_prompt) — reuse the
event JSON the way `notify-gchat.sh` does.

**Step 5 — crash cleanup + ownership polish.** Confirm `Stop` resets, SessionStart
clears, transient TTL hides; confirm second Claude in a window no-ops (ownership).

**Step 6 — retire bell.** Remove `preferredNotifChannel: terminal_bell` from
`settings.json` (and from any bootstrap default). Update README/CHANGELOG.

**Step 7 — end-to-end verification.** New session; in another window watch the tab
go present → busy → running → (slow on a long command) → needs-input → idle; kill
Claude mid-work and confirm the icon goes stale-then-clears within the TTL; restart
Claude and confirm clean state. `lint_all.py` green, `run_tests.py` green,
CHANGELOG + README updated, commit.

### Phase 2 — motion + snappier escalation (optional follow-up)

Spinner needs a ~1s redraw, but `status-interval 1` would re-run
`#(tmux-right-status)` every second (it shells out to next-meeting/weather). So:
1. Refactor `status-right` from `#(tmux-right-status)` to a pushed `@right_status`
   user option updated by a small user-timer (~15s); format just reads the option.
2. Then `status-interval 1` is cheap → add a 1 fps braille spinner for `busy`
   (`frame = #{e|%:%s,N}` cycling `⠋⠙⠹⠸⠼⠴⠦⠧`), and long-running escalation becomes
   near-instant. Pure format math; no extra process for the glyph itself.

### Phase 3 — explicit "waiting" state (optional)

Expose `claude-tmux-state waiting` and drive it explicitly from wait-and-verify
flows (e.g. a CLAUDE.md instruction or the monitor/verify skills) when Claude
deliberately blocks on a canary / land-poll / scheduled check, resetting to `busy`
when done. (Auto-detection is impossible — see below.)

---

## Deferred / out of scope

- **Auto-detecting "waiting for a scheduled task"** (`/loop`, `ScheduleWakeup`,
  cron between-iteration sleeps): not observable from hooks, by design. The
  *useful* case — Claude blocked on a long shell command (canary/land poll) — is
  already covered by the long-running "slow" icon (it's just a long `Bash` call).
  An explicit opt-in `waiting` state (Phase 3) covers the rest if wanted.
- **Rich statusLine-sourced detail** (model/ctx%/cost on the tab): possible later
  via the statusLine JSON, but it goes quiet on idle (needs a watchdog).
- **Bulletproof crash liveness** via process polling: rejected for CPU.

---

## References

- Investigation workflow result: 3 agents (tmux mechanism / Claude hooks / prior
  art), 2026-06-15.
- Related: the [bell fix](../CHANGELOG.md) (`preferredNotifChannel: terminal_bell`),
  retired by this feature's needs-input state.
- tmux 3.5a format language (`#{e|...}`, `%s`, `#{?...}`); Claude Code hooks docs
  (`Notification` reasons, `SessionStart`/`SessionEnd` firing, no scheduled-wait hook).
