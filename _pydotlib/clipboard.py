"""Cross-platform clipboard copy/paste with OSC 52 support for remote sessions.

This is the reusable core behind the `ccopy`/`cpaste` scripts (the CLI shells
live in those scripts; this module exposes capabilities, not a CLI). Locally,
callers reach the native clipboard tool (``pbcopy``/``xclip``/``wl-copy``/
``clip.exe``); over SSH there is no local clipboard to reach, so an OSC 52 escape
sequence is emitted that the *local* terminal interprets and applies to its own
clipboard.

Copy works well over SSH; paste (OSC 52 read) is best-effort — it is disabled by
default on most terminals and never forwarded through tmux, so remote paste fails
fast rather than hanging. See ``docs/plans/2026-06-15-clipboard-osc52-design.md``.
"""

from __future__ import annotations

import base64
import binascii
import os
import platform
import select
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import IO

# --- OSC 52 wire constants ---------------------------------------------------
ESC = b"\x1b"
BEL = b"\x07"
ST = ESC + b"\\"  # String Terminator
OSC52_PREFIX = ESC + b"]52;"

# Terminals silently DROP an OSC 52 sequence larger than this rather than
# erroring; the de-facto limit is 75000 raw bytes (100000 base64 chars, from
# hterm's OSC_52_MAX_SEQUENCE). Terminal-dependent — some are smaller.
OSC52_MAX_RAW = 75000
# Hard ceiling on an OSC 52 paste reply. The reply is untrusted (anything that
# can write to the tty can answer the clipboard query), so bound it.
OSC52_READ_CEILING = 1 << 20  # 1 MiB
DEFAULT_PASTE_TIMEOUT = 5.0  # seconds; long enough to approve a terminal's
# clipboard-read prompt (Ghostty/kitty ask before answering by default). It's a
# blocking select() wait, not a spin, so a high value is ~free on the no-reply
# path — and in tmux/screen paste fails fast before ever reaching this.

# --- exit codes (consumed by the ccopy/cpaste CLI shells) --------------------
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NO_FILE = 3
EXIT_NO_BACKEND = 4
EXIT_PASTE_UNSUPPORTED = 5
EXIT_TOO_LARGE = 6

# --- backend selection results ----------------------------------------------
BACKEND_NATIVE = "native"
BACKEND_OSC52 = "osc52"
BACKEND_NATIVE_UNREACHABLE = "native-unreachable"


def warn(message: str) -> None:
    """Print a single advisory line to stderr."""
    print(message, file=sys.stderr)


@dataclass(frozen=True)
class Environment:
    """Facts about where we're running, used to choose a clipboard backend."""

    os: str  # "macos" | "linux" | "wsl" | "unknown"
    is_ssh: bool
    is_tmux: bool
    is_screen: bool
    is_mosh: bool
    term: str
    term_program: str
    native_copy: list[str] | None  # argv to copy via native tool, or None
    native_paste: list[str] | None  # argv to paste via native tool, or None


def _detect_os(system: str, release: str) -> str:
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        # WSL reports a Linux kernel with "microsoft" in the release string.
        return "wsl" if "microsoft" in release.lower() else "linux"
    return "unknown"


def _native_copy_cmd(
    os_name: str, env: Mapping[str, str], which: Callable[[str], str | None]
) -> list[str] | None:
    if os_name == "macos":
        return ["pbcopy"] if which("pbcopy") else None
    if os_name == "wsl":
        return ["clip.exe"] if which("clip.exe") else None
    if os_name == "linux":
        if env.get("WAYLAND_DISPLAY") and which("wl-copy"):
            return ["wl-copy"]
        if env.get("DISPLAY"):
            if which("xclip"):
                return ["xclip", "-selection", "clipboard"]
            if which("xsel"):
                return ["xsel", "-ib"]
    return None


def _native_paste_cmd(
    os_name: str, env: Mapping[str, str], which: Callable[[str], str | None]
) -> list[str] | None:
    if os_name == "macos":
        return ["pbpaste"] if which("pbpaste") else None
    if os_name == "wsl":
        # powershell.exe (Windows PowerShell) ships on stock Windows/WSL;
        # pwsh (PowerShell Core) is not always installed.
        if which("powershell.exe"):
            return ["powershell.exe", "-NoProfile", "-Command", "Get-Clipboard"]
        return None
    if os_name == "linux":
        if env.get("WAYLAND_DISPLAY") and which("wl-paste"):
            return ["wl-paste", "--no-newline"]
        if env.get("DISPLAY"):
            if which("xclip"):
                return ["xclip", "-selection", "clipboard", "-o"]
            if which("xsel"):
                return ["xsel", "-ob"]
    return None


def detect(
    env: Mapping[str, str],
    *,
    system: str,
    release: str,
    which: Callable[[str], str | None],
) -> Environment:
    """Build an :class:`Environment` from injected ambient facts (pure).

    ``env`` is an ``os.environ``-like mapping, ``system`` is
    ``platform.system()``, ``release`` is ``platform.uname().release`` (used for
    WSL detection), and ``which`` resolves a command name to a path or ``None``.
    """
    os_name = _detect_os(system, release)
    is_tmux = bool(env.get("TMUX"))
    # screen-under-tmux: when $TMUX is set tmux owns the session even though it
    # sets TERM=screen*, so treat it as tmux. Detect real screen via $STY.
    is_screen = (not is_tmux) and bool(env.get("STY"))
    return Environment(
        os=os_name,
        is_ssh=bool(
            env.get("SSH_TTY") or env.get("SSH_CONNECTION") or env.get("SSH_CLIENT")
        ),
        is_tmux=is_tmux,
        is_screen=is_screen,
        is_mosh=bool(env.get("MOSH_CONNECTION")),
        term=env.get("TERM", ""),
        term_program=env.get("TERM_PROGRAM", ""),
        native_copy=_native_copy_cmd(os_name, env, which),
        native_paste=_native_paste_cmd(os_name, env, which),
    )


def default_environment() -> Environment:
    """Detect the :class:`Environment` from the real process/OS state."""
    return detect(
        os.environ,
        system=platform.system(),
        release=platform.uname().release,
        which=shutil.which,
    )


def choose_backend(env: Environment, verb: str, prefer: str | None) -> str:
    """Decide the backend for ``verb`` ("copy"/"paste"); see module docs.

    Returns one of ``BACKEND_NATIVE``, ``BACKEND_OSC52``, or
    ``BACKEND_NATIVE_UNREACHABLE`` (only when native was forced but no tool
    resolves).
    """
    native = env.native_copy if verb == "copy" else env.native_paste
    if prefer == BACKEND_OSC52:
        return BACKEND_OSC52
    if prefer == BACKEND_NATIVE:
        return BACKEND_NATIVE if native is not None else BACKEND_NATIVE_UNREACHABLE
    # auto: over SSH the native tool would target the wrong machine (the remote
    # host), so OSC 52 wins even when xclip/$DISPLAY resolve (incl. X11 fwd).
    if env.is_ssh:
        return BACKEND_OSC52
    return BACKEND_NATIVE if native is not None else BACKEND_OSC52


def resolve_prefer(cli_value: str | None) -> str | None:
    """Resolve the forced backend: a CLI flag value wins, then $CLIPBOARD_BACKEND.

    Returns ``BACKEND_NATIVE`` / ``BACKEND_OSC52`` to force a backend, or ``None``
    for automatic selection. A set-but-invalid ``$CLIPBOARD_BACKEND`` warns and
    falls back to auto.
    """
    if cli_value:
        return cli_value
    raw = os.environ.get("CLIPBOARD_BACKEND")
    if raw is None:
        return None
    value = raw.lower()
    if value in (BACKEND_NATIVE, BACKEND_OSC52):
        return value
    if value != "auto":
        warn(f"ignoring invalid CLIPBOARD_BACKEND={raw!r}; expected native, osc52, or auto")
    return None


def paste_timeout() -> float:
    """OSC 52 read timeout in seconds, from $CLIPBOARD_PASTE_TIMEOUT_MS."""
    raw = os.environ.get("CLIPBOARD_PASTE_TIMEOUT_MS")
    if raw:
        try:
            return max(0.0, float(raw) / 1000.0)
        except ValueError:
            pass
    return DEFAULT_PASTE_TIMEOUT


def encode_osc52(data: bytes, *, target: bytes = b"c", terminator: bytes = BEL) -> bytes:
    """Return the OSC 52 sequence that sets the clipboard to ``data`` (pure).

    The base64 payload is a single line; ``target`` is ``b"c"`` (CLIPBOARD) or
    ``b"p"`` (PRIMARY). Inside tmux this plain sequence is emitted unchanged —
    tmux's ``set-clipboard`` forwards it; no passthrough wrapping is needed.
    """
    payload = base64.standard_b64encode(data)
    return OSC52_PREFIX + target + b";" + payload + terminator


def _find_terminator(payload: bytes) -> int | None:
    candidates = [i for i in (payload.find(BEL), payload.find(ST)) if i != -1]
    return min(candidates) if candidates else None


def parse_osc52_reply(buf: bytes) -> bytes | None:
    """Decode a clipboard-read reply, or ``None`` if absent/malformed (pure).

    Accepts ``ESC ] 52 ; <selection> ; <base64> <BEL|ST>`` anywhere in ``buf``
    (the terminator may arrive in a later read than the prefix). The payload is
    untrusted, so base64 is validated strictly and anything malformed is
    rejected as "no reply".
    """
    start = buf.find(OSC52_PREFIX)
    if start < 0:
        return None
    body = buf[start + len(OSC52_PREFIX) :]
    semi = body.find(b";")  # end of the selection field (e.g. "c")
    if semi < 0:
        return None
    payload = body[semi + 1 :]
    end = _find_terminator(payload)
    if end is None:
        return None
    try:
        return base64.b64decode(payload[:end], validate=True)
    except (binascii.Error, ValueError):
        return None


def _reply_complete(buf: bytes) -> bool:
    start = buf.find(OSC52_PREFIX)
    return start >= 0 and _find_terminator(buf[start:]) is not None


def _run_cmd(cmd: list[str]) -> str | None:
    """Run a command, returning stdout on success or ``None`` on any failure."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def _osc52_warnings(env: Environment, run: Callable[[list[str]], str | None]) -> list[str]:
    """Misconfig warnings for the OSC 52 path (only the reliable ones)."""
    out: list[str] = []
    if env.is_tmux:
        sc = run(["tmux", "show", "-gv", "set-clipboard"])
        if sc is not None and sc.strip() == "off":
            out.append(
                "tmux set-clipboard is off; OSC 52 copy will be dropped "
                "(fix: tmux set -g set-clipboard on)"
            )
    if env.is_mosh:
        out.append("mosh detected; OSC 52 may be dropped (best-effort)")
    return out


def _open_tty_write() -> IO[bytes]:
    """Open /dev/tty for unbuffered binary writing (the controlling terminal)."""
    return open("/dev/tty", "wb", buffering=0)


def _open_tty_rw_fd() -> int:
    """Open /dev/tty read-write and return the raw fd."""
    return os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)


def _native_copy(cmd: list[str], data: bytes) -> int:
    try:
        proc = subprocess.run(cmd, input=data, check=False)
    except OSError as exc:
        warn(f"native clipboard command failed: {exc}")
        return EXIT_NO_BACKEND
    return EXIT_OK if proc.returncode == 0 else EXIT_NO_BACKEND


def _normalize_wsl(data: bytes) -> bytes:
    """Mirror the old `sed 's/\\r$//' | head -c -1`: CRLF→LF, drop one trailing LF."""
    data = data.replace(b"\r\n", b"\n")
    if data.endswith(b"\n"):
        data = data[:-1]
    return data


def _native_paste(cmd: list[str], os_name: str) -> tuple[int, bytes]:
    try:
        proc = subprocess.run(cmd, capture_output=True, check=False)
    except OSError as exc:
        warn(f"native clipboard command failed: {exc}")
        return EXIT_NO_BACKEND, b""
    if proc.returncode != 0:
        warn("native clipboard command failed")
        return EXIT_NO_BACKEND, b""
    out = proc.stdout
    return EXIT_OK, _normalize_wsl(out) if os_name == "wsl" else out


def _osc52_paste(timeout: float, tty_fd_opener: Callable[[], int]) -> bytes | None:
    """Best-effort OSC 52 clipboard read; ``None`` if unsupported/no reply.

    Puts /dev/tty in raw/no-echo mode (restored on every exit path), writes the
    read query, then accumulates the reply across reads until the terminator or
    the deadline. Never touches stdin (fd 0).
    """
    import termios
    import tty as tty_mod

    try:
        fd = tty_fd_opener()
    except OSError:
        return None

    saved = None
    try:
        try:
            saved = termios.tcgetattr(fd)
        except termios.error:
            return None
        tty_mod.setraw(fd)
        os.write(fd, OSC52_PREFIX + b"c;?" + BEL)

        buf = bytearray()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                break
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > OSC52_READ_CEILING:
                return None
            if _reply_complete(bytes(buf)):
                break
        return parse_osc52_reply(bytes(buf))
    finally:
        if saved is not None:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, saved)
            except termios.error:
                pass
        try:
            os.close(fd)
        except OSError:
            pass


def copy(
    data: bytes,
    env: Environment,
    *,
    prefer: str | None = None,
    tty_writer: Callable[[], IO[bytes]] = _open_tty_write,
    run: Callable[[list[str]], str | None] = _run_cmd,
) -> int:
    """Copy ``data`` to the clipboard; return an exit code."""
    backend = choose_backend(env, "copy", prefer)
    if backend == BACKEND_NATIVE_UNREACHABLE:
        warn("forced native clipboard is unavailable on this host")
        return EXIT_NO_BACKEND
    if backend == BACKEND_NATIVE:
        assert env.native_copy is not None
        return _native_copy(env.native_copy, data)

    # OSC 52 path.
    if len(data) > OSC52_MAX_RAW:
        warn(f"payload too large for OSC 52: {len(data)} bytes (cap {OSC52_MAX_RAW}); not copied")
        return EXIT_TOO_LARGE
    if env.is_screen:
        warn("screen does not support OSC 52; use tmux or a native clipboard tool")
        return EXIT_NO_BACKEND
    for message in _osc52_warnings(env, run):
        warn(message)
    try:
        with tty_writer() as tty:
            tty.write(encode_osc52(data))
            tty.flush()
    except OSError:
        warn("no controlling terminal; cannot emit OSC 52")
        return EXIT_NO_BACKEND
    return EXIT_OK


def paste(
    env: Environment,
    *,
    prefer: str | None = None,
    timeout: float = DEFAULT_PASTE_TIMEOUT,
    tty_fd_opener: Callable[[], int] = _open_tty_rw_fd,
) -> tuple[int, bytes]:
    """Read the clipboard; return ``(exit_code, data)``."""
    backend = choose_backend(env, "paste", prefer)
    if backend == BACKEND_NATIVE_UNREACHABLE:
        warn("forced native clipboard is unavailable on this host")
        return EXIT_NO_BACKEND, b""
    if backend == BACKEND_NATIVE:
        assert env.native_paste is not None
        return _native_paste(env.native_paste, env.os)

    # OSC 52 read is only attempted where it has a chance.
    if env.is_tmux:
        warn(
            "remote paste isn't supported through tmux; "
            "use Ctrl/Cmd-Shift-V or a tmux paste-buffer"
        )
        return EXIT_PASTE_UNSUPPORTED, b""
    if env.is_screen:
        warn("screen does not support OSC 52 clipboard read")
        return EXIT_PASTE_UNSUPPORTED, b""
    data = _osc52_paste(timeout, tty_fd_opener)
    if data is None:
        warn(
            f"no clipboard reply after {timeout:g}s — the terminal may not support "
            f"OSC 52 read, or the read timed out before you approved it. Raise "
            f"CLIPBOARD_PASTE_TIMEOUT_MS, or use Ctrl/Cmd-Shift-V or a tmux paste-buffer."
        )
        return EXIT_PASTE_UNSUPPORTED, b""
    return EXIT_OK, data
