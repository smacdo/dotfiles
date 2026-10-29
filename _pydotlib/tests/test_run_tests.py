import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run_tests import (
    _log_subprocess_failure,
    _make_timeout_exec_fn,
    detect_runtime,
    discover_bin_test_scripts,
    discover_flavors,
    run_bin_script_tests,
)

# A minimal conforming self-test hook: python shebang + --run-tests + unittest.main.
_HOOK = (
    "#!/usr/bin/env python3\n"
    "import sys, unittest\n"
    'if "--run-tests" in sys.argv:\n'
    "    unittest.main()\n"
)


class DetectRuntimeTests(unittest.TestCase):
    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n in {"podman", "docker"} else None)
    def test_auto_prefers_podman_when_both_present(self, _):
        self.assertEqual(detect_runtime(), "podman")

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "docker" else None)
    def test_auto_falls_back_to_docker(self, _):
        self.assertEqual(detect_runtime(), "docker")

    @patch("run_tests.shutil.which", return_value=None)
    def test_auto_raises_when_none_present(self, _):
        with self.assertRaises(SystemExit) as cm:
            detect_runtime()
        self.assertIn("no container runtime", str(cm.exception))

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "podman" else None)
    def test_explicit_podman_succeeds(self, _):
        self.assertEqual(detect_runtime("podman"), "podman")

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "podman" else None)
    def test_explicit_docker_raises_when_missing(self, _):
        with self.assertRaises(SystemExit) as cm:
            detect_runtime("docker")
        self.assertIn("'docker'", str(cm.exception))
        self.assertIn("not on PATH", str(cm.exception))

    @patch("run_tests.shutil.which", side_effect=lambda n: f"/usr/bin/{n}" if n == "docker" else None)
    def test_auto_string_is_treated_as_auto_detect(self, _):
        # Passing the literal "auto" sentinel should not be treated as a runtime name.
        self.assertEqual(detect_runtime("auto"), "docker")


class DiscoverFlavorsTests(unittest.TestCase):
    def _make_repo(self, root: Path, dockerfiles: list[str]) -> None:
        docker_dir = root / "tests" / "docker"
        docker_dir.mkdir(parents=True)
        for name in dockerfiles:
            (docker_dir / name).touch()

    def test_returns_sorted_flavors_from_dockerfiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile.ubuntu", "Dockerfile.alpine", "Dockerfile.fedora"])
            self.assertEqual(discover_flavors(root), ["alpine", "fedora", "ubuntu"])

    def test_ignores_plain_dockerfile_without_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile", "Dockerfile.debian"])
            self.assertEqual(discover_flavors(root), ["debian"])

    def test_returns_empty_when_docker_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(discover_flavors(Path(tmpdir)), [])

    def test_returns_empty_when_no_dockerfiles_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "tests" / "docker").mkdir(parents=True)
            self.assertEqual(discover_flavors(root), [])

    def test_picks_up_suffixed_variants(self):
        # Sanity: discoverer uses glob("Dockerfile.*"), so an unusual suffix like
        # `.bak` would also match. That's by design — it's the author's job to
        # only commit real dockerfiles. Lock in current behavior.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_repo(root, ["Dockerfile.alpine", "Dockerfile.bak"])
            self.assertEqual(discover_flavors(root), ["alpine", "bak"])


class DiscoverBinTestScriptsTests(unittest.TestCase):
    def _make_bin(self, root: Path, files: dict[str, str]) -> None:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, content in files.items():
            (bin_dir / name).write_text(content)

    def test_finds_python_script_with_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root,
                {
                    "withtests": _HOOK,
                    "notests": "#!/usr/bin/env python3\nprint('hi')\n",
                },
            )
            found = [p.name for p in discover_bin_test_scripts(root)]
            self.assertEqual(found, ["withtests"])

    def test_marker_without_unittest_main_is_skipped(self):
        # Mentions the flag in a comment but wires no real hook — must NOT be
        # discovered, else it gets run for real and fails.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root,
                {
                    "mentions": '#!/usr/bin/env python3\n# supports --run-tests someday\nprint("hi")\n',
                },
            )
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_requires_shebang_line(self):
        # First line contains "python" and the markers but is not a #! shebang.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root,
                {"notshebang": 'x = "python --run-tests unittest.main"\n'},
            )
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_ignores_non_python_shebang(self):
        # A shell script that only mentions the marker in a comment is skipped.
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(
                root, {"shscript": "#!/bin/sh\n# --run-tests unsupported\necho hi\n"}
            )
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_skips_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(root, {})
            (root / "bin" / "__pycache__").mkdir()
            self.assertEqual(discover_bin_test_scripts(root), [])

    def test_returns_empty_when_bin_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(discover_bin_test_scripts(Path(tmpdir)), [])

    def test_results_are_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._make_bin(root, {"bbb": _HOOK, "aaa": _HOOK})
            found = [p.name for p in discover_bin_test_scripts(root)]
            self.assertEqual(found, ["aaa", "bbb"])


class RunBinScriptTestsTests(unittest.TestCase):
    def _completed(self, returncode: int, stderr: str = "") -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout="", stderr=stderr
        )

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_passing_suite_returns_true(self, mock_discover, mock_run):
        mock_discover.return_value = [Path("bin/newline")]
        mock_run.return_value = self._completed(0, "Ran 5 tests in 0.0s\n\nOK\n")
        self.assertTrue(run_bin_script_tests(Path("/repo")))

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_failing_suite_returns_false(self, mock_discover, mock_run):
        mock_discover.return_value = [Path("bin/newline")]
        mock_run.return_value = self._completed(1, "FAILED (failures=1)\n")
        self.assertFalse(run_bin_script_tests(Path("/repo")))

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_no_tests_collected_warns_but_passes(self, mock_discover, mock_run):
        # unittest exit 5 = "NO TESTS RAN": hook wired but no tests yet (mid-TDD)
        # is a warning, not a suite failure.
        mock_discover.return_value = [Path("bin/newline")]
        mock_run.return_value = self._completed(5, "NO TESTS RAN\n")
        self.assertTrue(run_bin_script_tests(Path("/repo")))

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_timeout_returns_false(self, mock_discover, mock_run):
        mock_discover.return_value = [Path("bin/newline")]
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="newline", timeout=1)
        self.assertFalse(run_bin_script_tests(Path("/repo")))

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_empty_discovery_skips_without_running(self, mock_discover, mock_run):
        mock_discover.return_value = []
        self.assertTrue(run_bin_script_tests(Path("/repo")))
        mock_run.assert_not_called()

    @patch("run_tests.subprocess.run")
    @patch("run_tests.discover_bin_test_scripts")
    def test_one_failure_still_runs_remaining_scripts(self, mock_discover, mock_run):
        mock_discover.return_value = [Path("bin/a"), Path("bin/b")]
        mock_run.side_effect = [
            self._completed(1, "boom"),
            self._completed(0, "Ran 1 test\nOK\n"),
        ]
        self.assertFalse(run_bin_script_tests(Path("/repo")))
        self.assertEqual(mock_run.call_count, 2)  # did not abort after first failure


class LogSubprocessFailureTests(unittest.TestCase):
    def test_bytes_output_is_decoded(self):
        # TimeoutExpired carries captured output as bytes even with text=True.
        with self.assertLogs(level="ERROR") as logs:
            _log_subprocess_failure("timed out", b"out\xff\n", b"err\n")
        message = logs.output[0]
        self.assertIn("stdout:\nout\ufffd", message)
        self.assertIn("stderr:\nerr", message)
        self.assertNotIn("b'", message)

    def test_str_output_unchanged(self):
        with self.assertLogs(level="ERROR") as logs:
            _log_subprocess_failure("failed", "out\n", None)
        self.assertIn("stdout:\nout", logs.output[0])
        self.assertNotIn("stderr", logs.output[0])


class TimeoutExecFnTests(unittest.TestCase):
    @patch("run_tests.subprocess.run")
    def test_timeout_with_bytes_output_returns_124(self, mock_run):
        # TimeoutExpired output is bytes even with text=True; this used to
        # raise TypeError (bytes + str) instead of reporting the timeout.
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="x", timeout=1, output=b"partial out", stderr=b"partial err"
        )
        result = _make_timeout_exec_fn(["docker", "exec", "c"])(["true"])
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.stdout, "partial out")
        self.assertTrue(result.stderr.startswith("partial err\n<timed out after"))
