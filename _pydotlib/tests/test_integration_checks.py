import subprocess
import unittest
from unittest.mock import MagicMock

from _pydotlib.integration_checks import (
    BOOTSTRAP_CHECKS,
    CheckResult,
    check_dir_exists,
    check_file_contains,
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
