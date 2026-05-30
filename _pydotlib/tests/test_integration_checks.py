import subprocess
import unittest
from unittest.mock import MagicMock

from _pydotlib.integration_checks import (
    BOOTSTRAP_CHECKS,
    CheckResult,
    build_native_checks,
    check_command_output_matches,
    check_command_silent,
    check_command_succeeds,
    check_dir_exists,
    check_dir_non_empty,
    check_file_contains,
    check_file_not_exists,
    check_symlink,
    check_tmux_config,
)


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class CheckSymlinkTests(unittest.TestCase):
    def test_passes_when_link_target_matches(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(0, stdout="/expected/target\n"),
            ]
        )
        result = check_symlink("/link", "/expected/target")(exec_fn)
        self.assertTrue(result.passed)
        self.assertEqual(result.detail, "")

    def test_fails_when_not_a_symlink(self):
        exec_fn = MagicMock(return_value=_completed(1))
        result = check_symlink("/link", "/expected/target")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("not a symlink", result.detail)

    def test_fails_when_link_target_differs(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(0, stdout="/wrong/target\n"),
            ]
        )
        result = check_symlink("/link", "/expected/target")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("/wrong/target", result.detail)
        self.assertIn("/expected/target", result.detail)

    def test_fails_when_readlink_errors(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(1, stderr="readlink: bad"),
            ]
        )
        result = check_symlink("/link", "/expected/target")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("readlink", result.detail)


class CheckDirExistsTests(unittest.TestCase):
    def test_passes_when_dir_exists(self):
        exec_fn = MagicMock(return_value=_completed(0))
        result = check_dir_exists("/some/dir")(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_dir_missing(self):
        exec_fn = MagicMock(return_value=_completed(1))
        result = check_dir_exists("/some/dir")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("not a directory", result.detail)


class CheckFileContainsTests(unittest.TestCase):
    def test_passes_when_substring_present(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(0, stdout="header\nname = Alice\nfooter\n"),
            ]
        )
        result = check_file_contains("/file", "Alice")(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_file_missing(self):
        exec_fn = MagicMock(return_value=_completed(1))
        result = check_file_contains("/file", "Alice")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("not a regular file", result.detail)

    def test_fails_when_substring_absent(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(0, stdout="something else\n"),
            ]
        )
        result = check_file_contains("/file", "Alice")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("does not contain", result.detail)

    def test_fails_when_cat_errors(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(1, stderr="cat: bad"),
            ]
        )
        result = check_file_contains("/file", "Alice")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("cat", result.detail)


class CheckDirNonEmptyTests(unittest.TestCase):
    def test_passes_when_dir_has_entries(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),  # test -d
                _completed(0, stdout="/some/dir/sub1\n/some/dir/sub2\n"),  # find
            ]
        )
        result = check_dir_non_empty("/some/dir")(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_dir_missing(self):
        exec_fn = MagicMock(return_value=_completed(1))
        result = check_dir_non_empty("/some/dir")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("not a directory", result.detail)

    def test_fails_when_dir_empty(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),  # test -d
                _completed(0, stdout=""),  # find produces no output
            ]
        )
        result = check_dir_non_empty("/some/dir")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("empty", result.detail)

    def test_fails_when_find_errors(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(1, stderr="find: bad"),
            ]
        )
        result = check_dir_non_empty("/some/dir")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("find", result.detail)


class CheckFileNotExistsTests(unittest.TestCase):
    def test_passes_when_path_absent(self):
        # `test -e` returns non-zero when the path doesn't exist.
        exec_fn = MagicMock(return_value=_completed(1))
        result = check_file_not_exists("/no/such/path")(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_path_exists(self):
        exec_fn = MagicMock(return_value=_completed(0))
        result = check_file_not_exists("/some/path")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("exists but should not", result.detail)


class CheckCommandSucceedsTests(unittest.TestCase):
    def test_passes_when_command_exits_zero(self):
        exec_fn = MagicMock(return_value=_completed(0))
        result = check_command_succeeds(["true"])(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_command_exits_nonzero(self):
        exec_fn = MagicMock(return_value=_completed(1, stderr="bad config"))
        result = check_command_succeeds(["zsh", "-c", "source ~/.zshrc"])(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("exit 1", result.detail)
        self.assertIn("bad config", result.detail)


class CheckCommandSilentTests(unittest.TestCase):
    def test_passes_when_silent_and_exit_zero(self):
        exec_fn = MagicMock(return_value=_completed(0))
        result = check_command_silent(["zsh", "-ilc", "true"])(exec_fn)
        self.assertTrue(result.passed)
        self.assertEqual(result.detail, "")

    def test_fails_when_command_exits_nonzero(self):
        exec_fn = MagicMock(return_value=_completed(1, stderr="bad config"))
        result = check_command_silent(["zsh", "-ilc", "true"])(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("exit 1", result.detail)
        self.assertIn("bad config", result.detail)

    def test_fails_on_unexpected_stdout(self):
        exec_fn = MagicMock(return_value=_completed(0, stdout="hello\n"))
        result = check_command_silent(["zsh", "-ilc", "true"])(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("unexpected stdout", result.detail)
        self.assertIn("hello", result.detail)

    def test_fails_on_unexpected_stderr(self):
        exec_fn = MagicMock(return_value=_completed(0, stderr="deprecated: foo\n"))
        result = check_command_silent(["zsh", "-ilc", "true"])(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("unexpected stderr", result.detail)
        self.assertIn("deprecated", result.detail)

    def test_fails_when_both_streams_nonempty(self):
        # Documents the "noisy on both streams still fails" invariant, without
        # pinning down which stream is named first in the detail message.
        exec_fn = MagicMock(return_value=_completed(0, stdout="out\n", stderr="err\n"))
        result = check_command_silent(["zsh", "-ilc", "true"])(exec_fn)
        self.assertFalse(result.passed)
        self.assertRegex(result.detail, r"unexpected (stdout|stderr)")


class CheckCommandOutputMatchesTests(unittest.TestCase):
    def test_passes_when_output_contains_substring(self):
        exec_fn = MagicMock(return_value=_completed(0, stdout="prefix Seattle suffix\n"))
        result = check_command_output_matches(["echo", "x"], "Seattle")(exec_fn)
        self.assertTrue(result.passed)

    def test_fails_when_command_errors(self):
        exec_fn = MagicMock(return_value=_completed(2, stderr="boom"))
        result = check_command_output_matches(["bad"], "anything")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("exit 2", result.detail)
        self.assertIn("boom", result.detail)

    def test_fails_when_substring_absent(self):
        exec_fn = MagicMock(return_value=_completed(0, stdout="nothing here\n"))
        result = check_command_output_matches(["echo", "x"], "Seattle")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("Seattle", result.detail)


class BootstrapChecksSmokeTests(unittest.TestCase):
    def test_suite_is_non_empty(self):
        self.assertTrue(len(BOOTSTRAP_CHECKS) > 0)

    def test_every_check_is_callable_and_returns_result(self):
        # Make every exec_fn call succeed with empty output; that means symlink
        # checks fail (readlink returns "" != expected), but the important
        # invariant is that nothing crashes and every check returns a CheckResult.
        exec_fn = MagicMock(return_value=_completed(0, stdout=""))
        for check in BOOTSTRAP_CHECKS:
            result = check(exec_fn)
            self.assertIsInstance(result, CheckResult)


class CheckTmuxConfigTests(unittest.TestCase):
    def test_passes_when_source_file_succeeds(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),  # new-session (start server)
                _completed(0),  # source-file
                _completed(0),  # kill-server
            ]
        )
        result = check_tmux_config("/h/.tmux.conf")(exec_fn)
        self.assertTrue(result.passed)
        self.assertEqual(exec_fn.call_count, 3)

    def test_uses_isolated_socket_and_empty_startup_config(self):
        # The two load-bearing design choices: never touch a real server (-L)
        # and let source-file be the sole error-surfacing load (-f /dev/null).
        exec_fn = MagicMock(side_effect=[_completed(0), _completed(0), _completed(0)])
        check_tmux_config("/h/.tmux.conf", socket="probe_sock")(exec_fn)
        start_cmd = exec_fn.call_args_list[0].args[0]
        self.assertIn("-L", start_cmd)
        self.assertIn("probe_sock", start_cmd)
        self.assertIn("/dev/null", start_cmd)
        source_cmd = exec_fn.call_args_list[1].args[0]
        self.assertIn("source-file", source_cmd)

    def test_always_kills_server_after_source_file(self):
        exec_fn = MagicMock(side_effect=[_completed(0), _completed(1), _completed(0)])
        check_tmux_config("/h/.tmux.conf")(exec_fn)
        kill_cmd = exec_fn.call_args_list[-1].args[0]
        self.assertIn("kill-server", kill_cmd)

    def test_fails_when_server_does_not_start(self):
        exec_fn = MagicMock(return_value=_completed(1, stderr="no server"))
        result = check_tmux_config("/h/.tmux.conf")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("failed to start", result.detail)
        # Bails before source-file/kill — only the start call happened.
        self.assertEqual(exec_fn.call_count, 1)

    def test_fails_when_source_file_errors(self):
        exec_fn = MagicMock(
            side_effect=[
                _completed(0),
                _completed(1, stderr="invalid option: foo"),
                _completed(0),
            ]
        )
        result = check_tmux_config("/h/.tmux.conf")(exec_fn)
        self.assertFalse(result.passed)
        self.assertIn("source-file exit 1", result.detail)
        self.assertIn("invalid option", result.detail)


class NativeChecksSmokeTests(unittest.TestCase):
    def test_linux_returns_non_empty_list(self):
        checks = build_native_checks("/home/user", "/home/user/.dotfiles", platform="linux")
        self.assertTrue(len(checks) > 0)

    def test_darwin_returns_more_checks_than_linux(self):
        linux = build_native_checks("/home/user", "/home/user/.dotfiles", platform="linux")
        darwin = build_native_checks("/Users/user", "/Users/user/.dotfiles", platform="darwin")
        self.assertGreater(len(darwin), len(linux))

    def test_symlink_targets_point_from_home_into_dotfiles(self):
        # Guards against swapping the home/dotfiles args or a wrong subpath:
        # check counts/callability alone stay green if the link/target reverse.
        checks = build_native_checks("/h", "/h/.dotfiles", platform="linux")
        names = [c(MagicMock(return_value=_completed(0, stdout=""))).name for c in checks]
        self.assertTrue(
            any("/h/.bashrc -> /h/.dotfiles/.bashrc" in n for n in names)
        )

    def test_darwin_includes_macos_specific_checks(self):
        checks = build_native_checks("/Users/user", "/Users/user/.dotfiles", platform="darwin")
        names = [c(MagicMock(return_value=_completed(0, stdout=""))).name for c in checks]
        macos_names = [n for n in names if "DOT_OS" in n or "DOT_DIST" in n or "zsh" in n]
        self.assertGreater(len(macos_names), 0)

    def test_linux_excludes_macos_specific_checks(self):
        checks = build_native_checks("/home/user", "/home/user/.dotfiles", platform="linux")
        names = [c(MagicMock(return_value=_completed(0, stdout=""))).name for c in checks]
        macos_names = [n for n in names if "DOT_OS" in n or "DOT_DIST" in n or "zsh" in n]
        self.assertEqual(len(macos_names), 0)

    def test_every_check_is_callable_and_returns_result(self):
        exec_fn = MagicMock(return_value=_completed(0, stdout=""))
        for platform in ("linux", "darwin"):
            for check in build_native_checks("/home/u", "/home/u/.dotfiles", platform=platform):
                result = check(exec_fn)
                self.assertIsInstance(result, CheckResult)
