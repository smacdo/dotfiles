import base64
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest import mock

from _pydotlib import clipboard
from _pydotlib.clipboard import (
    BACKEND_NATIVE,
    BACKEND_NATIVE_UNREACHABLE,
    BACKEND_OSC52,
    BEL,
    EXIT_NO_BACKEND,
    EXIT_OK,
    EXIT_PASTE_UNSUPPORTED,
    EXIT_TOO_LARGE,
    OSC52_MAX_RAW,
    OSC52_PREFIX,
    ST,
    Environment,
    choose_backend,
    detect,
    encode_osc52,
    parse_osc52_reply,
)


def make_which(present=()):
    """Return a fake shutil.which that resolves only names in `present`."""
    present = set(present)
    return lambda name: f"/usr/bin/{name}" if name in present else None


def make_env(**overrides) -> Environment:
    base = dict(
        os="linux",
        is_ssh=False,
        is_tmux=False,
        is_screen=False,
        is_mosh=False,
        term="xterm-256color",
        term_program="",
        native_copy=None,
        native_paste=None,
    )
    base.update(overrides)
    return Environment(**base)


def _raise_oserror():
    raise OSError("no tty")


class _Completed:
    def __init__(self, returncode=0, stdout=b""):
        self.returncode = returncode
        self.stdout = stdout


class FakeTTY:
    """A stand-in for the /dev/tty binary file object used by copy()."""

    def __init__(self):
        self.data = b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, b):
        self.data += b

    def flush(self):
        pass


class DetectTests(unittest.TestCase):
    def test_macos(self):
        env = detect({}, system="Darwin", release="23.0.0", which=make_which(["pbcopy", "pbpaste"]))
        self.assertEqual(env.os, "macos")
        self.assertEqual(env.native_copy, ["pbcopy"])
        self.assertEqual(env.native_paste, ["pbpaste"])

    def test_wsl_via_release(self):
        env = detect(
            {}, system="Linux", release="5.15.0-microsoft-standard-WSL2",
            which=make_which(["clip.exe", "powershell.exe"]),
        )
        self.assertEqual(env.os, "wsl")
        self.assertEqual(env.native_copy, ["clip.exe"])
        assert env.native_paste is not None
        self.assertEqual(env.native_paste[0], "powershell.exe")

    def test_linux_wayland_prefers_wl_copy(self):
        env = detect(
            {"WAYLAND_DISPLAY": "wayland-0"}, system="Linux", release="6.1.0",
            which=make_which(["wl-copy", "wl-paste", "xclip"]),
        )
        self.assertEqual(env.native_copy, ["wl-copy"])
        self.assertEqual(env.native_paste, ["wl-paste", "--no-newline"])

    def test_linux_x11_xclip(self):
        env = detect(
            {"DISPLAY": ":0"}, system="Linux", release="6.1.0",
            which=make_which(["xclip", "xsel"]),
        )
        self.assertEqual(env.native_copy, ["xclip", "-selection", "clipboard"])

    def test_linux_x11_xsel_when_no_xclip(self):
        env = detect(
            {"DISPLAY": ":0"}, system="Linux", release="6.1.0", which=make_which(["xsel"])
        )
        self.assertEqual(env.native_copy, ["xsel", "-ib"])

    def test_linux_headless_has_no_native(self):
        env = detect({}, system="Linux", release="6.1.0", which=make_which(["xclip"]))
        self.assertIsNone(env.native_copy)
        self.assertIsNone(env.native_paste)

    def test_ssh_predicates(self):
        for var in ("SSH_TTY", "SSH_CONNECTION", "SSH_CLIENT"):
            env = detect({var: "x"}, system="Linux", release="x", which=make_which())
            self.assertTrue(env.is_ssh, var)
        self.assertFalse(detect({}, system="Linux", release="x", which=make_which()).is_ssh)

    def test_empty_tmux_var_is_not_tmux(self):
        self.assertFalse(detect({"TMUX": ""}, system="Linux", release="x", which=make_which()).is_tmux)
        self.assertTrue(detect({"TMUX": "/tmp/s,1,0"}, system="Linux", release="x", which=make_which()).is_tmux)

    def test_screen_under_tmux_is_tmux_not_screen(self):
        env = detect(
            {"TMUX": "/tmp/s,1,0", "STY": "1.foo", "TERM": "screen-256color"},
            system="Linux", release="x", which=make_which(),
        )
        self.assertTrue(env.is_tmux)
        self.assertFalse(env.is_screen)

    def test_real_screen_via_sty(self):
        env = detect({"STY": "1234.pts-0.host"}, system="Linux", release="x", which=make_which())
        self.assertTrue(env.is_screen)


class ChooseBackendTests(unittest.TestCase):
    def test_ssh_gates_before_native(self):
        env = make_env(is_ssh=True, native_copy=["xclip", "-selection", "clipboard"])
        self.assertEqual(choose_backend(env, "copy", None), BACKEND_OSC52)

    def test_local_with_native_uses_native(self):
        env = make_env(native_copy=["pbcopy"])
        self.assertEqual(choose_backend(env, "copy", None), BACKEND_NATIVE)

    def test_local_without_native_falls_back_to_osc52(self):
        self.assertEqual(choose_backend(make_env(native_copy=None), "copy", None), BACKEND_OSC52)

    def test_force_osc52(self):
        env = make_env(native_copy=["pbcopy"])
        self.assertEqual(choose_backend(env, "copy", BACKEND_OSC52), BACKEND_OSC52)

    def test_force_native_unreachable(self):
        env = make_env(native_copy=None)
        self.assertEqual(choose_backend(env, "copy", BACKEND_NATIVE), BACKEND_NATIVE_UNREACHABLE)

    def test_paste_uses_paste_command_presence(self):
        env = make_env(native_copy=["pbcopy"], native_paste=None)
        self.assertEqual(choose_backend(env, "paste", None), BACKEND_OSC52)


class EncodeTests(unittest.TestCase):
    def test_exact_bytes(self):
        seq = encode_osc52(b"hello")
        self.assertEqual(seq, OSC52_PREFIX + b"c;" + base64.standard_b64encode(b"hello") + BEL)

    def test_explicit_clipboard_target(self):
        self.assertIn(b"]52;c;", encode_osc52(b"x"))

    def test_single_line_payload(self):
        self.assertNotIn(b"\n", encode_osc52(b"a" * 100))

    def test_empty_encodes_to_clear(self):
        self.assertEqual(encode_osc52(b""), OSC52_PREFIX + b"c;" + BEL)

    def test_primary_target(self):
        self.assertEqual(
            encode_osc52(b"x", target=b"p"),
            OSC52_PREFIX + b"p;" + base64.standard_b64encode(b"x") + BEL,
        )


class ParseReplyTests(unittest.TestCase):
    def _reply(self, data: bytes, term: bytes = BEL) -> bytes:
        return OSC52_PREFIX + b"c;" + base64.standard_b64encode(data) + term

    def test_roundtrip_bel(self):
        self.assertEqual(parse_osc52_reply(self._reply(b"clip text")), b"clip text")

    def test_roundtrip_st(self):
        self.assertEqual(parse_osc52_reply(self._reply(b"clip", term=ST)), b"clip")

    def test_with_leading_and_trailing_noise(self):
        buf = b"garbage" + self._reply(b"payload") + b"trailing"
        self.assertEqual(parse_osc52_reply(buf), b"payload")

    def test_no_prefix_returns_none(self):
        self.assertIsNone(parse_osc52_reply(b"no escape here"))

    def test_missing_terminator_returns_none(self):
        self.assertIsNone(parse_osc52_reply(OSC52_PREFIX + b"c;" + base64.standard_b64encode(b"x")))

    def test_invalid_base64_returns_none(self):
        self.assertIsNone(parse_osc52_reply(OSC52_PREFIX + b"c;!!!notbase64!!!" + BEL))

    def test_reply_complete_helper_handles_split(self):
        head = OSC52_PREFIX + b"c;" + base64.standard_b64encode(b"data")
        self.assertFalse(clipboard._reply_complete(head))
        self.assertTrue(clipboard._reply_complete(head + BEL))


class NormalizeWslTests(unittest.TestCase):
    def test_crlf_to_lf_and_drop_one_trailing_newline(self):
        self.assertEqual(clipboard._normalize_wsl(b"foo\r\nbar\r\n"), b"foo\nbar")

    def test_keeps_interior_newlines(self):
        self.assertEqual(clipboard._normalize_wsl(b"a\r\nb\r\nc"), b"a\nb\nc")

    def test_only_trailing_newline_stripped_once(self):
        self.assertEqual(clipboard._normalize_wsl(b"x\n\n"), b"x\n")


class CopyTests(unittest.TestCase):
    def test_native_copy_invokes_command(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["input"] = kwargs.get("input")
            return _Completed(returncode=0)

        env = make_env(native_copy=["pbcopy"])
        with mock.patch("subprocess.run", side_effect=fake_run):
            rc = clipboard.copy(b"hi", env)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(captured["cmd"], ["pbcopy"])
        self.assertEqual(captured["input"], b"hi")

    def test_osc52_copy_writes_sequence_to_tty(self):
        fake = FakeTTY()
        env = make_env(is_ssh=True, native_copy=None)
        with redirect_stderr(StringIO()):
            rc = clipboard.copy(b"remote", env, tty_writer=lambda: fake, run=lambda c: None)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(fake.data, encode_osc52(b"remote"))

    def test_osc52_copy_refuses_oversized(self):
        env = make_env(is_ssh=True)
        with redirect_stderr(StringIO()) as err:
            rc = clipboard.copy(b"x" * (OSC52_MAX_RAW + 1), env, tty_writer=FakeTTY, run=lambda c: None)
        self.assertEqual(rc, EXIT_TOO_LARGE)
        self.assertIn("too large", err.getvalue())

    def test_osc52_copy_no_controlling_tty(self):
        env = make_env(is_ssh=True)
        with redirect_stderr(StringIO()) as err:
            rc = clipboard.copy(b"x", env, tty_writer=_raise_oserror, run=lambda c: None)
        self.assertEqual(rc, EXIT_NO_BACKEND)
        self.assertIn("no controlling terminal", err.getvalue())

    def test_forced_native_unreachable(self):
        env = make_env(native_copy=None)
        with redirect_stderr(StringIO()) as err:
            rc = clipboard.copy(b"x", env, prefer=BACKEND_NATIVE, tty_writer=FakeTTY)
        self.assertEqual(rc, EXIT_NO_BACKEND)
        self.assertIn("unavailable", err.getvalue())

    def test_screen_fails_fast(self):
        env = make_env(is_ssh=True, is_screen=True)
        with redirect_stderr(StringIO()) as err:
            rc = clipboard.copy(b"x", env, tty_writer=FakeTTY, run=lambda c: None)
        self.assertEqual(rc, EXIT_NO_BACKEND)
        self.assertIn("screen", err.getvalue())

    def test_tmux_set_clipboard_off_warns(self):
        fake = FakeTTY()
        env = make_env(is_ssh=True, is_tmux=True)
        with redirect_stderr(StringIO()) as err:
            rc = clipboard.copy(b"x", env, tty_writer=lambda: fake, run=lambda c: "off\n")
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("set-clipboard is off", err.getvalue())


class PasteTests(unittest.TestCase):
    def test_native_paste_returns_output(self):
        env = make_env(native_paste=["pbpaste"])
        with mock.patch("subprocess.run", return_value=_Completed(0, b"pasted")):
            rc, data = clipboard.paste(env)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(data, b"pasted")

    def test_native_paste_wsl_normalizes(self):
        env = make_env(os="wsl", native_paste=["powershell.exe"])
        with mock.patch("subprocess.run", return_value=_Completed(0, b"foo\r\nbar\r\n")):
            rc, data = clipboard.paste(env)
        self.assertEqual(data, b"foo\nbar")

    def test_paste_in_tmux_fails_fast(self):
        env = make_env(is_ssh=True, is_tmux=True, native_paste=None)
        with redirect_stderr(StringIO()) as err:
            rc, data = clipboard.paste(env)
        self.assertEqual(rc, EXIT_PASTE_UNSUPPORTED)
        self.assertEqual(data, b"")
        self.assertIn("tmux", err.getvalue())

    def test_paste_osc52_no_reply(self):
        env = make_env(is_ssh=True, native_paste=None)
        with redirect_stderr(StringIO()) as err:
            rc, data = clipboard.paste(env, tty_fd_opener=_raise_oserror)
        self.assertEqual(rc, EXIT_PASTE_UNSUPPORTED)
        self.assertIn("no clipboard reply", err.getvalue())


class ResolvePreferTests(unittest.TestCase):
    def test_cli_flag_wins_over_env(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_BACKEND": "native"}):
            self.assertEqual(clipboard.resolve_prefer(BACKEND_OSC52), BACKEND_OSC52)

    def test_env_used_when_no_flag(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_BACKEND": "native"}):
            self.assertEqual(clipboard.resolve_prefer(None), BACKEND_NATIVE)

    def test_auto_returns_none_without_warning(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_BACKEND": "auto"}):
            with redirect_stderr(StringIO()) as err:
                self.assertIsNone(clipboard.resolve_prefer(None))
            self.assertEqual("", err.getvalue())

    def test_invalid_env_warns_and_returns_none(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_BACKEND": "bogus"}):
            with redirect_stderr(StringIO()) as err:
                self.assertIsNone(clipboard.resolve_prefer(None))
            self.assertIn("invalid CLIPBOARD_BACKEND", err.getvalue())


class PasteTimeoutTests(unittest.TestCase):
    def test_default_when_unset(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(clipboard.paste_timeout(), clipboard.DEFAULT_PASTE_TIMEOUT)

    def test_parsed_from_ms(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_PASTE_TIMEOUT_MS": "500"}):
            self.assertEqual(clipboard.paste_timeout(), 0.5)

    def test_invalid_falls_back(self):
        with mock.patch.dict("os.environ", {"CLIPBOARD_PASTE_TIMEOUT_MS": "abc"}):
            self.assertEqual(clipboard.paste_timeout(), clipboard.DEFAULT_PASTE_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
