import importlib.util
import json
import os
import re
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

from _pydotlib import agent_status

# bin/claude-status has no .py extension and a hyphen, so it can't be imported by
# name. An explicit SourceFileLoader is required because spec_from_file_location
# can't infer a loader from a suffix-less filename.
_SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "claude-status"


def _load_claude_status():
    loader = SourceFileLoader("claude_status", str(_SCRIPT))
    spec = importlib.util.spec_from_loader("claude_status", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


cs = _load_claude_status()


# The transient all-zero payload Claude Code occasionally emits (seen both at a
# /compact boundary and mid-session). Rendering it flashes a bogus "0%"/"↓0 ↑0".
EMPTY_CTX = {
    "used_percentage": 0,
    "context_window_size": 1_000_000,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "current_usage": {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    },
}


class EntrypointTests(unittest.TestCase):
    def test_runs_outside_repo_without_pythonpath(self):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("S_DOTFILE_ROOT", None)
        env.pop("CLAUDE_STATUS_MONOREPOS", None)
        env["COLUMNS"] = "120"

        with tempfile.TemporaryDirectory() as temp_dir:
            env["HOME"] = os.path.join(temp_dir, "home")
            result = subprocess.run(
                [str(_SCRIPT)],
                cwd=temp_dir,
                env=env,
                input=json.dumps({"workspace": {"current_dir": temp_dir}}),
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().endswith(f"⌂ {temp_dir}"), result.stdout)


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
    USAGE = {"total_input_tokens": 1250000, "total_output_tokens": 10100}

    def test_shows_actual_cost_from_payload(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 1.2345}}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓1.25m ↑10.1k ($1.23)")

    def test_omits_cost_when_absent(self):
        data = {"context_window": self.USAGE}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓1.25m ↑10.1k")

    def test_omits_cost_when_zero(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 0.0}}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓1.25m ↑10.1k")

    def test_short_mode_omits_cost(self):
        data = {"context_window": self.USAGE, "cost": {"total_cost_usd": 1.23}}
        self.assertEqual(cs.build_usage_section(data, short=True), "↓1.25m ↑10.1k")

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

    def test_all_zero_frame_is_suppressed(self):
        # The same empty frame that zeroes context also zeroes the token totals;
        # suppress "↓0 ↑0" so the fix doesn't leave a half-cleaned line.
        self.assertEqual(cs.build_usage_section({"context_window": EMPTY_CTX}, short=False), "")

    def test_fresh_session_zero_totals_without_current_usage_still_renders(self):
        # Zero totals without a populated current_usage is a fresh session, not the
        # empty frame — it should still render rather than disappear.
        data = {"context_window": {"total_input_tokens": 0, "total_output_tokens": 0}}
        self.assertEqual(cs.build_usage_section(data, short=False), "↓0 ↑0")


class FmtTokensTests(unittest.TestCase):
    def test_under_one_thousand(self):
        self.assertEqual(cs.fmt_tokens(0), "0")
        self.assertEqual(cs.fmt_tokens(125), "125")
        self.assertEqual(cs.fmt_tokens(999), "999")

    def test_thousands_three_sig_figs(self):
        self.assertEqual(cs.fmt_tokens(1000), "1.00k")
        self.assertEqual(cs.fmt_tokens(1250), "1.25k")
        self.assertEqual(cs.fmt_tokens(10100), "10.1k")
        self.assertEqual(cs.fmt_tokens(12340), "12.3k")
        self.assertEqual(cs.fmt_tokens(45000), "45.0k")
        self.assertEqual(cs.fmt_tokens(100000), "100k")

    def test_millions_three_sig_figs(self):
        self.assertEqual(cs.fmt_tokens(1_000_000), "1.00m")
        self.assertEqual(cs.fmt_tokens(1_500_000), "1.50m")
        self.assertEqual(cs.fmt_tokens(1_234_567), "1.23m")
        self.assertEqual(cs.fmt_tokens(12_500_000), "12.5m")
        self.assertEqual(cs.fmt_tokens(125_000_000), "125m")


class BuildContextSectionTests(unittest.TestCase):
    @staticmethod
    def _plain(s: str) -> str:
        return re.sub(r"\033\[[0-9;]*m", "", s)

    def test_missing_used_percentage_returns_empty(self):
        self.assertEqual(cs.build_context_section({"context_window": {}}, short=False), "")

    def test_short_mode_shows_only_percentage(self):
        data = {"context_window": {"used_percentage": 60, "context_window_size": 1_000_000}}
        self.assertEqual(self._plain(cs.build_context_section(data, short=True)), "◑ 60%")

    def test_no_window_size_shows_only_percentage(self):
        data = {"context_window": {"used_percentage": 60}}
        self.assertEqual(self._plain(cs.build_context_section(data, short=False)), "◑ 60%")

    def test_bracket_is_derived_from_percentage(self):
        data = {"context_window": {"used_percentage": 60, "context_window_size": 1_000_000}}
        self.assertEqual(self._plain(cs.build_context_section(data, short=False)), "◑ 60% [600k/1.00m]")

    def test_bracket_ignores_misleading_current_usage(self):
        # Regression: the bracket must track the percentage, not a tiny
        # input+cache_read sum left small by a cache-creation-heavy turn.
        data = {
            "context_window": {
                "used_percentage": 47,
                "context_window_size": 1_000_000,
                "current_usage": {"input_tokens": 14000, "cache_read_input_tokens": 0},
            }
        }
        self.assertEqual(self._plain(cs.build_context_section(data, short=False)), "◑ 47% [470k/1.00m]")

    def test_all_zero_frame_shows_placeholder(self):
        # The transient empty payload must not render "◑ 0%". It shows a quiet
        # placeholder instead of blank so the slot doesn't look broken in the
        # idle gap after /compact (Claude Code re-renders only on the next turn).
        self.assertEqual(self._plain(cs.build_context_section({"context_window": EMPTY_CTX}, short=False)), "◑ …")

    def test_all_zero_frame_shows_placeholder_in_short_mode(self):
        self.assertEqual(self._plain(cs.build_context_section({"context_window": EMPTY_CTX}, short=True)), "◑ …")

    def test_placeholder_is_dimmed(self):
        # The placeholder is low-emphasis so it reads as "pending", not a value.
        out = cs.build_context_section({"context_window": EMPTY_CTX}, short=False)
        self.assertTrue(out.startswith(cs.DIM))
        self.assertTrue(out.endswith(cs.RESET))

    def test_zero_percent_without_current_usage_still_renders(self):
        # A present-but-0 percentage lacking current_usage detail is NOT the empty
        # frame (the real ones always carry a populated all-zero current_usage), so
        # it must still render rather than vanish.
        data = {"context_window": {"used_percentage": 0, "context_window_size": 1_000_000}}
        self.assertEqual(self._plain(cs.build_context_section(data, short=False)), "◑ 0% [0/1.00m]")

    def test_zero_percent_with_real_tokens_still_renders(self):
        # A genuine sub-1% session (rounds to 0%) with live tokens must not be
        # mistaken for the empty frame.
        data = {
            "context_window": {
                "used_percentage": 0,
                "context_window_size": 1_000_000,
                "current_usage": {"input_tokens": 1500, "cache_read_input_tokens": 0},
            }
        }
        self.assertEqual(self._plain(cs.build_context_section(data, short=False)), "◑ 0% [0/1.00m]")


class BuildDirBranchSectionTests(unittest.TestCase):
    def test_no_cwd_returns_empty(self):
        self.assertEqual(cs.build_dir_branch_section({}), "")

    @patch.object(agent_status, "collect_directory_status")
    def test_branch_and_stat(self, collect):
        collect.return_value = agent_status.DirectoryStatus(
            display_path="/some/repo",
            vcs_kind="git",
            display_revision="feature-x",
            diffstat="+5 -1",
        )
        data = {"workspace": {"current_dir": "/some/repo"}}
        with patch.dict(os.environ, {"CLAUDE_STATUS_MONOREPOS": ""}):
            self.assertEqual(
                cs.build_dir_branch_section(data),
                "⌂ /some/repo ⎇ feature-x +5 -1",
            )
        collect.assert_called_once_with("/some/repo", monorepos=())

    @patch.object(agent_status, "collect_directory_status")
    def test_no_revision_omits_vcs_decoration(self, collect):
        collect.return_value = agent_status.DirectoryStatus(
            display_path="/some/repo",
            vcs_kind="git",
        )
        data = {"workspace": {"current_dir": "/some/repo"}}
        with patch.dict(os.environ, {"CLAUDE_STATUS_MONOREPOS": ""}):
            self.assertEqual(cs.build_dir_branch_section(data), "⌂ /some/repo")
        collect.assert_called_once_with("/some/repo", monorepos=())

    @patch.object(agent_status, "collect_directory_status")
    def test_passes_monorepo_configuration(self, collect):
        collect.return_value = agent_status.DirectoryStatus(display_path="~/bigrepo/.../c/d")
        data = {"workspace": {"current_dir": "/home/me/bigrepo/a/b/c/d"}}
        with patch.dict(os.environ, {"CLAUDE_STATUS_MONOREPOS": "bigrepo"}):
            self.assertEqual(cs.build_dir_branch_section(data), "⌂ ~/bigrepo/.../c/d")
        collect.assert_called_once_with(
            "/home/me/bigrepo/a/b/c/d",
            monorepos=("bigrepo",),
        )


class MonoreposEnvTests(unittest.TestCase):
    def test_unset_is_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cs._monorepos(), ())

    def test_space_and_comma_separated(self):
        with patch.dict(os.environ, {"CLAUDE_STATUS_MONOREPOS": "alpha, beta  gamma,delta"}):
            self.assertEqual(cs._monorepos(), ("alpha", "beta", "gamma", "delta"))


if __name__ == "__main__":
    unittest.main()
