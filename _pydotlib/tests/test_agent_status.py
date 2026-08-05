import unittest
from pathlib import Path
from unittest.mock import patch

from _pydotlib import agent_status, vcs


class FormatDisplayPathTests(unittest.TestCase):
    REPOS = ("bigrepo", "src")

    def test_home_is_tilde(self):
        self.assertEqual(agent_status.format_display_path("/home/me", home="/home/me"), "~")

    def test_home_substitution(self):
        self.assertEqual(
            agent_status.format_display_path("/home/me/projects/foo", home="/home/me"),
            "~/projects/foo",
        )

    def test_similar_prefix_is_not_home(self):
        self.assertEqual(
            agent_status.format_display_path("/home/meanwhile", home="/home/me"),
            "/home/meanwhile",
        )

    def test_deep_monorepo_path_collapses(self):
        self.assertEqual(
            agent_status.format_display_path(
                "/home/me/bigrepo/a/b/c/d",
                home="/home/me",
                monorepos=self.REPOS,
            ),
            "~/bigrepo/.../c/d",
        )

    def test_digit_suffix_matches_basename(self):
        self.assertEqual(
            agent_status.format_display_path(
                "/home/me/bigrepo2/a/b/c/d",
                home="/home/me",
                monorepos=self.REPOS,
            ),
            "~/bigrepo2/.../c/d",
        )

    def test_shallow_path_is_unchanged(self):
        self.assertEqual(
            agent_status.format_display_path(
                "/home/me/bigrepo/a/b/c",
                home="/home/me",
                monorepos=self.REPOS,
            ),
            "~/bigrepo/a/b/c",
        )


class CollectDirectoryStatusTests(unittest.TestCase):
    @patch.object(agent_status.vcs, "collect_vcs_status")
    def test_combines_display_path_and_vcs_status(self, collect_vcs_status):
        repository = vcs.Repository("git", Path("/repo"))
        collect_vcs_status.return_value = vcs.VcsStatus(
            repository=repository,
            display_revision="feature-x",
            diffstat="+12 -4",
        )

        status = agent_status.collect_directory_status(
            "/home/me/repo",
            home="/home/me",
        )

        self.assertEqual(status.display_path, "~/repo")
        self.assertEqual(status.vcs_kind, "git")
        self.assertEqual(status.display_revision, "feature-x")
        self.assertEqual(status.diffstat, "+12 -4")
        collect_vcs_status.assert_called_once_with("/home/me/repo")

    @patch.object(agent_status.vcs, "collect_vcs_status", return_value=None)
    def test_no_repository(self, collect_vcs_status):
        status = agent_status.collect_directory_status("/some/path", home="/home/me")
        self.assertEqual(status.display_path, "/some/path")
        self.assertIsNone(status.vcs_kind)
        self.assertEqual(status.display_revision, "")
        self.assertEqual(status.diffstat, "")
        collect_vcs_status.assert_called_once_with("/some/path")


if __name__ == "__main__":
    unittest.main()
