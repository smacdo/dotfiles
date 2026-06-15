import importlib.util
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
