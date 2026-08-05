import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _pydotlib import vcs


class ParseDiffstatTests(unittest.TestCase):
    def test_insertions_and_deletions(self):
        summary = "3 files changed, 12 insertions(+), 4 deletions(-)"
        self.assertEqual(vcs.parse_diffstat(summary), "+12 -4")

    def test_only_insertions(self):
        self.assertEqual(vcs.parse_diffstat("1 file changed, 7 insertions(+)"), "+7")

    def test_only_deletions(self):
        self.assertEqual(vcs.parse_diffstat("1 file changed, 2 deletions(-)"), "-2")

    def test_no_line_changes(self):
        self.assertEqual(vcs.parse_diffstat("1 file changed"), "")

    def test_empty(self):
        self.assertEqual(vcs.parse_diffstat(""), "")


class SelectSaplingDisplayRevisionTests(unittest.TestCase):
    def test_bookmark_wins(self):
        self.assertEqual(
            vcs.select_sapling_display_revision("feature-x\ndraft\nabc123def456"),
            "feature-x",
        )

    def test_skips_main_bookmark(self):
        self.assertEqual(
            vcs.select_sapling_display_revision("main feature-y\ndraft\nabc123"),
            "feature-y",
        )

    def test_main_only_bookmark_is_blank(self):
        self.assertEqual(
            vcs.select_sapling_display_revision("main\npublic\nabc123"),
            "",
        )

    def test_draft_without_bookmark_uses_short_hash(self):
        self.assertEqual(
            vcs.select_sapling_display_revision("\ndraft\nabc123def456"),
            "abc123def456",
        )

    def test_public_without_bookmark_is_blank(self):
        self.assertEqual(
            vcs.select_sapling_display_revision("\npublic\nabc123"),
            "",
        )

    def test_empty(self):
        self.assertEqual(vcs.select_sapling_display_revision(""), "")


class FindRepositoryTests(unittest.TestCase):
    def test_git_marker_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").mkdir()
            self.assertEqual(vcs.find_repository(root), vcs.Repository("git", root))

    def test_git_marker_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").write_text("gitdir: /elsewhere\n")
            self.assertEqual(vcs.find_repository(root), vcs.Repository("git", root))

    def test_sapling_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".sl").mkdir()
            self.assertEqual(vcs.find_repository(root), vcs.Repository("sapling", root))

    def test_hg_marker_is_sapling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".hg").mkdir()
            self.assertEqual(vcs.find_repository(root), vcs.Repository("sapling", root))

    def test_returns_ancestor_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").mkdir()
            child = root.joinpath("a", "b")
            child.mkdir(parents=True)
            self.assertEqual(vcs.find_repository(child), vcs.Repository("git", root))


class CollectVcsStatusTests(unittest.TestCase):
    @patch("_pydotlib.vcs.subprocess.run", side_effect=UnicodeError("invalid output"))
    def test_unicode_command_failure_is_ignored(self, run):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").mkdir()

            status = vcs.collect_vcs_status(root)

        assert status is not None
        self.assertEqual(status.display_revision, "")
        run.assert_called_once()

    def test_git_branch_and_diffstat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").mkdir()

            def run_command(argv, cwd):
                self.assertEqual(cwd, root)
                command = tuple(argv)
                if command == (
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "branch",
                    "--show-current",
                ):
                    return "feature-x"
                if command == (
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "diff",
                    "--no-color",
                    "--shortstat",
                    "HEAD",
                ):
                    return "3 files changed, 12 insertions(+), 4 deletions(-)"
                self.fail(f"unexpected command: {command}")

            status = vcs.collect_vcs_status(root, run_command=run_command)
            assert status is not None
            self.assertEqual(status.repository, vcs.Repository("git", root))
            self.assertEqual(status.display_revision, "feature-x")
            self.assertEqual(status.diffstat, "+12 -4")

    def test_main_branch_omits_revision_and_diff_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".git").mkdir()
            commands = []
            expected_command = (
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "branch",
                "--show-current",
            )

            def run_command(argv, cwd):
                self.assertEqual(cwd, root)
                command = tuple(argv)
                commands.append(command)
                if command != expected_command:
                    self.fail(f"unexpected command: {command}")
                return "main"

            status = vcs.collect_vcs_status(root, run_command=run_command)
            assert status is not None
            self.assertEqual(status.display_revision, "")
            self.assertEqual(status.diffstat, "")
            self.assertEqual(commands, [expected_command])

    def test_sapling_bookmark_and_diffstat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".sl").mkdir()

            def run_command(argv, cwd):
                self.assertEqual(cwd, root)
                command = tuple(argv)
                if command == (
                    "sl",
                    "log",
                    "-r",
                    ".",
                    "-T",
                    "{bookmarks}\n{phase}\n{node|short}",
                ):
                    return "bookmark-z\ndraft\nabc123"
                if command == ("sl", "diff", "--stat"):
                    return "file.py | 3 ++-\n1 file changed, 2 insertions(+), 1 deletion(-)"
                self.fail(f"unexpected command: {command}")

            status = vcs.collect_vcs_status(root, run_command=run_command)
            assert status is not None
            self.assertEqual(status.repository, vcs.Repository("sapling", root))
            self.assertEqual(status.display_revision, "bookmark-z")
            self.assertEqual(status.diffstat, "+2 -1")

    @patch("_pydotlib.vcs.subprocess.run")
    def test_sapling_draft_without_bookmark_uses_hash_through_runner(self, run):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.joinpath(".sl").mkdir()

            def run_command(argv, **kwargs):
                self.assertEqual(kwargs["cwd"], root)
                command = tuple(argv)
                if command == (
                    "sl",
                    "log",
                    "-r",
                    ".",
                    "-T",
                    "{bookmarks}\n{phase}\n{node|short}",
                ):
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        stdout="\ndraft\nabc123def456",
                        stderr="",
                    )
                if command == ("sl", "diff", "--stat"):
                    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
                self.fail(f"unexpected command: {command}")

            run.side_effect = run_command
            status = vcs.collect_vcs_status(root)

        assert status is not None
        self.assertEqual(status.display_revision, "abc123def456")
        self.assertEqual(status.diffstat, "")

    def test_no_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertIsNone(vcs.collect_vcs_status(temp_dir))


if __name__ == "__main__":
    unittest.main()
