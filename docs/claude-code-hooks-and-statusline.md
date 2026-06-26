# Claude Code hooks & status line — observed behavior

Empirical reference for the Claude Code platform behavior that `bin/claude-status`
(the status line) and `bin/claude-tmux-state` (the per-window tmux state icon)
depend on. Captured so we never re-research it.

**Trust but verify.** Much of this is *observed*, not documented — Claude Code can
change it. The dated provenance is at the bottom; re-probe (see *How this was
captured*) before relying on anything marked "observed" if behavior looks off.

---

## Status line (`bin/claude-status`)

### Invocation & refresh model

- The `statusLine` command is **re-invoked per render**, as a fresh process, with
  *that session's* JSON piped to stdin. It is stateless and per-session — the
  displayed value is never cross-contaminated between concurrent sessions (only a
  *shared debug log* can interleave; the display cannot).
- **Event-driven, not a heartbeat.** It re-runs after each assistant message,
  after `/compact` finishes, on permission-mode change, and on vim-mode toggle;
  debounced at 300ms. During true idle nothing re-runs **unless** you set
  `statusLine.refreshInterval` (seconds, minimum 1), which adds a fixed timer.
- Full `statusLine` config fields: `type`, `command`, `padding`,
  `refreshInterval`, `hideVimModeIndicator`.
- Consequence: the status line **cannot force its own redraw**. After `/compact`
  the line goes quiet until your next turn (see below) and nothing — not even
  `refreshInterval` — can make the rebuilt number appear sooner, because the data
  isn't in the payload yet.

### The `/compact` empty window

- During `/compact` and until the **next API call** (your next turn) repopulates
  it, `context_window` token counts come through as **zero/null**
  (`used_percentage` 0, `current_usage` all-zero). The genuine post-compact
  percentage simply does not exist in the payload until that next turn.
- `claude-status` detects this all-zero frame and renders a quiet `◑ …`
  placeholder (not a bogus `0%`, and the token-usage section is suppressed),
  snapping to the real number on the next turn. A live session always has the
  system prompt resident, so a *true* sustained 0% never happens.

### Percentage / token bracket

- Derive the `[used/total]` bracket from `used_percentage` (authoritative), **not**
  from `current_usage` input + cache-read tokens — that sum collapses right after
  a cache *write* (large `cache_creation_input_tokens`), making the bracket read
  far below the percentage.

---

## Hooks (`bin/claude-tmux-state`)

The feature's hook→state wiring lives in `_pydotlib/bootstrap.py`
(`CLAUDE_TMUX_STATE_HOOKS`); the state→icon render is in `.tmux.conf`. What
follows is the **platform lifecycle** those depend on.

### General

- Hook commands run in the **main session's pane** with `$TMUX_PANE` set —
  including for subagent/orchestration events (see below).
- Tool names seen by `PreToolUse`/`PostToolUse` matchers are bare:
  `Bash`, `Read`, `Edit`, `Agent` (the Task tool; `Task` alias also works),
  `Workflow`, `AskUserQuestion`, etc. Matchers are regex (e.g. `Agent|Workflow`).
- `SessionStart` is distinguished by `source` (`startup`, `resume`, `clear`,
  `compact`, …). Scoping to `startup` avoids a mid-session resume/compact
  resetting in-progress state.
- The **task-completion re-invoke** (when a background workflow/task finishes)
  arrives as a `UserPromptSubmit` whose `prompt` is `<task-notification>…`.

### Orchestration (Workflow tool / subagents) — the important part

- The **Workflow tool returns a task id immediately** and runs in the background.
  `PostToolUse:Workflow` fires at *dispatch* (~0.7s after `PreToolUse`), **not** at
  completion. The main turn then has nothing left to do and **ends**.
- `SubagentStart` fires at subagent dispatch; `SubagentStop` when each subagent
  ends. Both fire **in the main pane** (`agent_type` e.g. `workflow-subagent`,
  `general-purpose`). Neither is wired to a state today.
- A **subagent's own tool calls fire the *parent* session's
  `PreToolUse`/`PostToolUse` hooks**, annotated with `agent_id` + `agent_type`
  (e.g. a workflow subagent's `sleep 90` fired the parent's `PreToolUse:Bash`).
- **`Stop` is the authoritative "is background work pending" signal.** Its payload
  includes `background_tasks` (array) and `session_crons`. `background_tasks` is
  **non-empty (`[{ "id": … }]`) while a background workflow/task is still
  running**, and **empty (`[]`) once it's done**. This is the clean, stateless way
  to tell, at turn-end, whether the session is truly idle or just foreground-free
  with work still running in the background.

### Notifications

- `idle_prompt` — message `"Claude is waiting for your input"`, fires **~60s after
  a `Stop`**. It fires **even while background work is still pending**, and its
  payload does **not** include `background_tasks`. It is just an "idle a while"
  nudge, *not* a signal that Claude is actually asking you a question.
- `permission_prompt` — a tool is awaiting approval.
- **`AskUserQuestion` fires NO `Notification`** (probed). The genuine "Claude is
  asking you something" is observable only as a **tool call** —
  `PreToolUse`/`PostToolUse` with `tool_name = AskUserQuestion`. So the real
  producer for a "needs input" icon is `PreToolUse:AskUserQuestion` (cleared by
  `PostToolUse:AskUserQuestion` when you answer), **not** a notification. No
  `elicitation_*` notification was observed.

### Canonical captured timelines

All events in the main pane. `bg` = the `Stop` payload's `background_tasks`.

**Fast workflow (subagent finishes before the dispatch `Stop`):**
```
UserPromptSubmit → PreToolUse:Workflow → PostToolUse:Workflow → SubagentStart
→ SubagentStop → Stop[bg=[]] → UserPromptSubmit(<task-notification>)
→ Stop[bg=[]] → Notification:idle_prompt (+60s, work already DONE)
```

**Slow workflow (subagent still running at the dispatch `Stop`):**
```
UserPromptSubmit → PreToolUse:Workflow → PostToolUse:Workflow → SubagentStart
→ Stop[bg=[{id}]]                       ← session NOT idle; work pending
→ PreToolUse:Bash (the subagent's own command)
→ Notification:idle_prompt (+60s, MID-RUN)   ← false "needs input" during real work
→ PostToolUse:Bash → SubagentStop
→ UserPromptSubmit(<task-notification>) → Stop[bg=[]] → Notification:idle_prompt
```

---

## Gotchas these explain

- **A session looks "idle" during a background workflow** because the main turn
  genuinely ends (`Stop` fires) at dispatch. Mechanically the interactive loop
  *is* free; what's missing is a representation of "foreground-free **and**
  background-pending" — read it from `Stop`'s `background_tasks`.
- **Every walked-away session goes "needs input" after ~60s** because
  `idle_prompt` is a generic idle nudge; mapping it to an urgent indicator is a
  false positive. Reserve "needs input" for the genuine ask —
  `PreToolUse:AskUserQuestion` (cleared by `PostToolUse:AskUserQuestion`); no
  `elicitation_*` notification exists.
- No mechanism forces a status-line or tmux-icon redraw during idle.

## Open questions (re-probe before relying)

- Whether a plain `run_in_background` **Bash** (not a Workflow) also populates
  `Stop.background_tasks`.
- Exact `idle_prompt` timeout (observed ~60s; undocumented).
- Whether *any* flow emits an `elicitation_*` `Notification` (an `AskUserQuestion`
  does **not** — it surfaces only as a `PreToolUse`/`PostToolUse` tool call).

## How this was captured

- **Status line:** a `--debug`/`session_id`-tagged capture of the piped JSON
  across `/compact` boundaries (earlier work; see `CHANGELOG.md`).
- **Hooks:** a throwaway logging hook registered on every event in a scratch
  project's `.claude/settings.json`, logging timestamp + event + `$TMUX_PANE` +
  trimmed payload, while running a trivial and a sleeping (`sleep 90`) workflow,
  then reading the log. Reproduce by registering a logger on
  `SessionStart, UserPromptSubmit, Pre/PostToolUse(.*), Notification,
  SubagentStart, SubagentStop, Stop, StopFailure, SessionEnd`.

_Captured 2026-06-25. See also `docs/tmux-claude-state.md` (the icon feature) and
`bin/claude-status` / `bin/claude-tmux-state`._
