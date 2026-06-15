import importlib.util
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

# bin/claude-status has no .py extension and a hyphen, so it can't be imported by
# name. Load it from its path instead — the test depends on the bin script, not
# the other way around, so the script stays standalone (bin/ portability policy).
# An explicit SourceFileLoader is required because spec_from_file_location can't
# infer a loader from a suffix-less filename.
_SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "claude-status"


def _load_claude_status():
    loader = SourceFileLoader("claude_status", str(_SCRIPT))
    spec = importlib.util.spec_from_loader("claude_status", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


cs = _load_claude_status()


class BuildDurationSectionTests(unittest.TestCase):
    def test_missing_cost_returns_empty(self):
        self.assertEqual(cs.build_duration_section({}), "")

    def test_zero_duration_returns_empty(self):
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": 0}}), "")

    def test_negative_duration_returns_empty(self):
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": -5}}), "")

    def test_under_one_minute(self):
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": 45_000}}), "◷ <1min")

    def test_whole_minutes(self):
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": 5 * 60_000}}), "◷ 5min")

    def test_minutes_floor(self):
        # 5m59s floors to 5min
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": 359_000}}), "◷ 5min")

    def test_hours_and_minutes(self):
        ms = (2 * 3600 + 3 * 60) * 1000
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": ms}}), "◷ 2h 3m")

    def test_exact_hours_omits_minutes(self):
        self.assertEqual(cs.build_duration_section({"cost": {"total_duration_ms": 2 * 3600 * 1000}}), "◷ 2h")


class BuildUsageSectionTests(unittest.TestCase):
    USAGE = {"total_input_tokens": 12000, "total_output_tokens": 3000}

    def test_shows_actual_cost_from_payload(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 1.2345}}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓12k ↑3k ($1.23)")

    def test_omits_cost_when_absent(self):
        data = {"context_window": self.USAGE}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓12k ↑3k")

    def test_omits_cost_when_zero(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 0.0}}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓12k ↑3k")

    def test_short_mode_omits_cost(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 1.23}}
        self.assertEqual(cs.build_usage_section(data, short=True), "↓12k ↑3k")

    def test_rate_limits_take_priority_over_cost(self):
        data = {
            "rate_limits": {
                "five_hour": {"used_percentage": 12},
                "seven_day": {"used_percentage": 4},
            },
            "cost": {"total_cost_usd": 9.99},
        }
        result = cs.build_usage_section(data, short=False)
        self.assertTrue(result.startswith("⏱"))
        self.assertNotIn("$", result)


class FmtTokensTests(unittest.TestCase):
    def test_under_one_thousand(self):
        self.assertEqual(cs.fmt_tokens(0), "0")
        self.assertEqual(cs.fmt_tokens(999), "999")

    def test_thousands_trim_trailing_zeros(self):
        self.assertEqual(cs.fmt_tokens(1000), "1k")
        self.assertEqual(cs.fmt_tokens(1500), "1.5k")
        self.assertEqual(cs.fmt_tokens(45000), "45k")
        self.assertEqual(cs.fmt_tokens(12340), "12.34k")

    def test_millions_trim_trailing_zeros(self):
        self.assertEqual(cs.fmt_tokens(1_000_000), "1m")
        self.assertEqual(cs.fmt_tokens(1_200_000), "1.2m")
        self.assertEqual(cs.fmt_tokens(1_234_567), "1.23m")


class ParseDiffstatTests(unittest.TestCase):
    def test_insertions_and_deletions(self):
        self.assertEqual(cs._parse_diffstat("3 files changed, 12 insertions(+), 4 deletions(-)"), "+12 -4")

    def test_only_insertions(self):
        self.assertEqual(cs._parse_diffstat("1 file changed, 7 insertions(+)"), "+7")

    def test_only_deletions(self):
        self.assertEqual(cs._parse_diffstat("1 file changed, 2 deletions(-)"), "-2")

    def test_no_line_changes(self):
        self.assertEqual(cs._parse_diffstat("1 file changed"), "")

    def test_empty(self):
        self.assertEqual(cs._parse_diffstat(""), "")


class ParseSlLabelTests(unittest.TestCase):
    def test_bookmark_wins(self):
        self.assertEqual(cs._parse_sl_label("feature-x\ndraft\nabc123def456"), "feature-x")

    def test_skips_main_bookmark(self):
        self.assertEqual(cs._parse_sl_label("main feature-y\ndraft\nabc123"), "feature-y")

    def test_main_only_bookmark_is_blank(self):
        self.assertEqual(cs._parse_sl_label("main\npublic\nabc123"), "")

    def test_draft_without_bookmark_uses_short_hash(self):
        self.assertEqual(cs._parse_sl_label("\ndraft\nabc123def456"), "abc123def456")

    def test_public_without_bookmark_is_blank(self):
        self.assertEqual(cs._parse_sl_label("\npublic\nabc123"), "")

    def test_empty(self):
        self.assertEqual(cs._parse_sl_label(""), "")


class DetectVcsTests(unittest.TestCase):
    def test_git_marker_dir(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".git"))
            self.assertEqual(cs._detect_vcs(d), "git")

    def test_git_marker_file(self):
        # git worktrees use a .git *file*, not a directory
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".git"), "w") as f:
                f.write("gitdir: /elsewhere\n")
            self.assertEqual(cs._detect_vcs(d), "git")

    def test_sl_marker(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".sl"))
            self.assertEqual(cs._detect_vcs(d), "sl")

    def test_hg_marker_is_sapling(self):
        # Sapling marks its root with .hg on many installs; driven via `sl`.
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".hg"))
            self.assertEqual(cs._detect_vcs(d), "sl")

    def test_walks_up_to_ancestor_marker(self):
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".git"))
            sub = os.path.join(d, "a", "b")
            os.makedirs(sub)
            self.assertEqual(cs._detect_vcs(sub), "git")


class BuildDirBranchSectionTests(unittest.TestCase):
    def test_no_cwd_returns_empty(self):
        self.assertEqual(cs.build_dir_branch_section({}), "")

    @patch.object(cs, "_detect_vcs", return_value=None)
    def test_home_substitution_no_repo(self, _):
        home = os.path.expanduser("~")
        data = {"workspace": {"current_dir": home + "/projects/foo"}}
        self.assertEqual(cs.build_dir_branch_section(data), "⌂ ~/projects/foo")

    @patch.object(cs, "_git_stat", return_value="+5 -1")
    @patch.object(cs, "_git_label", return_value="feature-x")
    @patch.object(cs, "_detect_vcs", return_value="git")
    def test_git_branch_and_stat(self, *_):
        data = {"workspace": {"current_dir": "/some/repo"}}
        self.assertEqual(cs.build_dir_branch_section(data), "⌂ /some/repo ⎇ feature-x +5 -1")

    @patch.object(cs, "_sl_stat", return_value="+9")
    @patch.object(cs, "_sl_label", return_value="bookmark-z")
    @patch.object(cs, "_detect_vcs", return_value="sl")
    def test_sapling_bookmark_and_stat(self, *_):
        data = {"workspace": {"current_dir": "/some/repo"}}
        self.assertEqual(cs.build_dir_branch_section(data), "⌂ /some/repo ⎇ bookmark-z +9")

    @patch.object(cs, "_git_label", return_value="")
    @patch.object(cs, "_detect_vcs", return_value="git")
    def test_main_branch_no_decoration(self, *_):
        data = {"workspace": {"current_dir": "/some/repo"}}
        self.assertEqual(cs.build_dir_branch_section(data), "⌂ /some/repo")

    @patch.object(cs, "_git_stat", return_value="")
    @patch.object(cs, "_git_label", return_value="feature-x")
    @patch.object(cs, "_detect_vcs", return_value="git")
    def test_branch_without_changes_omits_stat(self, *_):
        data = {"workspace": {"current_dir": "/some/repo"}}
        self.assertEqual(cs.build_dir_branch_section(data), "⌂ /some/repo ⎇ feature-x")


if __name__ == "__main__":
    unittest.main()
