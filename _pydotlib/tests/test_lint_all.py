import subprocess
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
