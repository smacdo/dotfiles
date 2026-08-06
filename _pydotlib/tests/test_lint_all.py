import subprocess
import unittest
from unittest.mock import call, patch

import lint_all


class PinnedToolCommandTests(unittest.TestCase):
    def setUp(self):
        self.completed = subprocess.CompletedProcess([], 0, stdout="")

    def test_every_tool_package_is_exactly_version_pinned(self):
        for tool, package in lint_all.UVX_TOOL_PACKAGES.items():
            with self.subTest(tool=tool):
                self.assertRegex(package, rf"^{tool}==\d+\.\d+\.\d+$")

    @patch("lint_all.subprocess.run")
    def test_typecheck_uses_pinned_ty(self, run):
        run.return_value = self.completed

        self.assertEqual(lint_all.typecheck_py_file("example.py"), (True, ""))

        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "uvx",
                "--from",
                lint_all.UVX_TOOL_PACKAGES["ty"],
                "ty",
                "check",
                "--no-progress",
                "--color",
                "always",
                "example.py",
            ],
        )

    @patch("lint_all.subprocess.run")
    def test_ruff_uses_pinned_package_and_explicit_fix_mode(self, run):
        run.return_value = self.completed

        for auto_fix, expected_flag in ((False, "--no-fix"), (True, "--fix")):
            with self.subTest(auto_fix=auto_fix):
                self.assertEqual(
                    lint_all.ruff_lint_py_file("example.py", auto_fix=auto_fix),
                    (True, ""),
                )
                command = run.call_args.args[0]
                self.assertEqual(
                    command,
                    [
                        "uvx",
                        "--from",
                        lint_all.UVX_TOOL_PACKAGES["ruff"],
                        "ruff",
                        "check",
                        expected_flag,
                        "example.py",
                    ],
                )

    @patch("lint_all.subprocess.run")
    def test_preflight_uses_the_same_pinned_package(self, run):
        run.return_value = self.completed

        self.assertEqual(lint_all.preflight_uvx_tool("ruff"), (True, ""))

        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "uvx",
                "--from",
                lint_all.UVX_TOOL_PACKAGES["ruff"],
                "ruff",
                "--version",
            ],
        )


class MainTests(unittest.TestCase):
    @patch("lint_all.logging")
    @patch("lint_all.preflight_uvx_tool", return_value=(True, ""))
    @patch("lint_all.lint_py_files", return_value=[])
    @patch("lint_all.lint_sh_files", side_effect=[["shell/example"], []])
    @patch("lint_all.find_shell_scripts", return_value=[])
    @patch("sys.argv", ["lint_all.py"])
    def test_shell_lint_failures_are_fatal(
        self, _find_scripts, _lint_sh_files, _lint_py_files, _preflight, logging
    ):
        self.assertEqual(lint_all.main(), 1)

        logging.error.assert_called_once_with(
            "1 shell scripts failed required linter checks"
        )
        logging.warning.assert_called_once_with("fatal linter issues found")

    @patch("lint_all.logging")
    @patch("lint_all.preflight_uvx_tool", return_value=(False, "unavailable"))
    @patch("lint_all.lint_sh_files", return_value=[])
    @patch("lint_all.find_shell_scripts")
    @patch("sys.argv", ["lint_all.py"])
    def test_tools_shell_scripts_are_linted(
        self, find_scripts, lint_sh_files, _preflight, _logging
    ):
        find_scripts.side_effect = lambda directory, _extensions, _shebangs: [
            f"{directory}/script"
        ]

        lint_all.main()

        shell_files = lint_sh_files.call_args_list[1].args[0]
        self.assertIn("tools/script", shell_files)

    @patch("lint_all.logging")
    @patch("lint_all.preflight_uvx_tool", return_value=(False, "unavailable"))
    @patch("lint_all.lint_sh_files", return_value=[])
    @patch("lint_all.find_shell_scripts", return_value=[])
    @patch("sys.argv", ["lint_all.py"])
    def test_skipped_python_lint_is_not_reported_as_success(
        self, _find_scripts, _lint_sh_files, _preflight, logging
    ):
        self.assertEqual(lint_all.main(), 1)

        self.assertNotIn(call("all lint checks passed!"), logging.info.call_args_list)
        logging.warning.assert_called_once_with("fatal linter issues found")

    @patch("lint_all.logging")
    @patch("lint_all.preflight_uvx_tool", return_value=(True, ""))
    @patch("lint_all.lint_py_files", side_effect=[[], ["bin/example"]])
    @patch("lint_all.lint_sh_files", return_value=[])
    @patch("sys.argv", ["lint_all.py"])
    def test_python_bin_lint_failures_are_fatal(
        self, _lint_sh_files, _lint_py_files, _preflight, logging
    ):
        def find_scripts(base_path, extensions, _shebangs):
            if base_path == "bin" and extensions == lint_all.PY_EXTS:
                return ["bin/example"]
            return []

        with patch("lint_all.find_shell_scripts", side_effect=find_scripts):
            self.assertEqual(lint_all.main(), 1)

        logging.error.assert_called_once_with(
            "1 python bin scripts failed required linter checks"
        )
        logging.warning.assert_called_once_with("fatal linter issues found")


if __name__ == "__main__":
    unittest.main()
