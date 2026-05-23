import subprocess
import unittest
from unittest.mock import MagicMock

from _pydotlib.integration_checks import (
    BOOTSTRAP_CHECKS,
    CheckResult,
    check_command_output_matches,
    check_command_silent,
    check_command_succeeds,
    check_dir_exists,
    check_dir_non_empty,
    check_file_contains,
    check_file_not_exists,
    check_symlink,
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
