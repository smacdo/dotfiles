"""Tests for the bin/claude-tmux-state helper.

The helper is a POSIX sh script that pushes per-window state onto tmux user
options, so it's exercised end-to-end against a throwaway `tmux -L` server
rather than by importing it. Skipped entirely when tmux isn't installed (e.g.
the Docker integration images), so it never fails CI for lack of tmux.
"""

import os
import shutil
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "claude-tmux-state"
HAVE_TMUX = shutil.which("tmux") is not None


@unittest.skipUnless(HAVE_TMUX, "tmux not installed")
class ClaudeTmuxStateTests(unittest.TestCase):
    def setUp(self):
        self.sock = f"cltest_{os.getpid()}_{self._testMethodName}"
        self._tmux("kill-server", check=False)
        self._tmux("new-session", "-d", "-s", "t", "-x", "200", "-y", "50")
        self.socket_path = self._tmux_out("display-message", "-p", "#{socket_path}")
        self.pane = self._tmux_out("display-message", "-p", "#{pane_id}")

    def tearDown(self):
        self._tmux("kill-server", check=False)

    def _tmux(self, *args, check=True):
        return subprocess.run(
            ["tmux", "-L", self.sock, *args],
            capture_output=True,
            text=True,
            check=check,
        )

    def _tmux_out(self, *args):
        return self._tmux(*args).stdout.strip()

    def _split(self):
        """Add a second pane to the current window; return its pane id."""
        return self._tmux_out("split-window", "-P", "-F", "#{pane_id}", "-t", self.pane)

    def _run(self, *state, pane=None):
        env = dict(os.environ)
        env["TMUX"] = f"{self.socket_path},{os.getpid()},0"
        env["TMUX_PANE"] = pane or self.pane
        return subprocess.run(
            [str(SCRIPT), *state], env=env, capture_output=True, text=True
        )

    def _opt(self, name, pane=None):
        return self._tmux_out("show-option", "-wqv", "-t", pane or self.pane, name)

    def test_outside_tmux_noops(self):
        env = dict(os.environ)
        env.pop("TMUX", None)
        env.pop("TMUX_PANE", None)
        r = subprocess.run(
            [str(SCRIPT), "busy"], env=env, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)

    def test_sets_busy(self):
        r = self._run("busy")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._opt("@claude_state"), "busy")
        self.assertEqual(self._opt("@claude_owner"), self.pane)
        self.assertTrue(self._opt("@claude_since").isdigit())

    def test_missing_state_noops(self):
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._opt("@claude_state"), "")

    def test_unknown_state_exits_2(self):
        r = self._run("bogus")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown state", r.stderr)
        self.assertEqual(self._opt("@claude_state"), "")

    def test_second_pane_does_not_clobber(self):
        self._run("running")
        pane2 = self._split()
        r = self._run("needs-input", pane=pane2)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._opt("@claude_state"), "running")
        self.assertEqual(self._opt("@claude_owner"), self.pane)

    def test_clear_from_nonowner_is_noop(self):
        self._run("running")
        pane2 = self._split()
        self._run("clear", pane=pane2)
        self.assertEqual(self._opt("@claude_state"), "running")

    def test_clear_from_owner_clears_all(self):
        self._run("busy")
        self._run("clear")
        self.assertEqual(self._opt("@claude_state"), "")
        self.assertEqual(self._opt("@claude_owner"), "")
        self.assertEqual(self._opt("@claude_since"), "")

    def test_stale_owner_is_taken_over(self):
        self._run("busy")
        pane2 = self._split()
        self._tmux("set-option", "-w", "-t", self.pane, "@claude_owner", "%999")
        self._run("busy", pane=pane2)
        self.assertEqual(self._opt("@claude_owner"), pane2)
        self.assertEqual(self._opt("@claude_state"), "busy")

    def test_owner_relocated_out_of_window_is_reclaimable(self):
        # Owner pane that is moved to another window (break-pane) is still alive
        # server-wide but no longer in this window, so a remaining in-window pane
        # must be able to reclaim the icon (regression test for the -a vs -t fix).
        self._run("busy")
        pane2 = self._split()
        self._tmux("break-pane", "-d", "-s", self.pane)
        r = self._run("needs-input", pane=pane2)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self._opt("@claude_owner", pane=pane2), pane2)
        self.assertEqual(self._opt("@claude_state", pane=pane2), "needs-input")


if __name__ == "__main__":
    unittest.main()
