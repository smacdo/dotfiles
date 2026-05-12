import os
import unittest
from pathlib import Path
from unittest.mock import patch

from _pydotlib.xdg import xdg_cache_dir, xdg_config_dir, xdg_data_dir, xdg_state_dir


class TestXdgConfigDir(unittest.TestCase):
    @patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"})
    def test_returns_env_variable_if_set(self):
        self.assertEqual(xdg_config_dir(), Path("/custom/config"))

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_default_if_env_not_set(self):
        expected = Path.home() / ".config"
        self.assertEqual(xdg_config_dir(), expected)


class TestXdgDataDir(unittest.TestCase):
    @patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/data"})
    def test_returns_env_variable_if_set(self):
        self.assertEqual(xdg_data_dir(), Path("/custom/data"))

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_default_if_env_not_set(self):
        expected = Path.home() / ".local" / "share"
        self.assertEqual(xdg_data_dir(), expected)


class TestXdgStateDir(unittest.TestCase):
    @patch.dict(os.environ, {"XDG_STATE_HOME": "/custom/state"})
    def test_returns_env_variable_if_set(self):
        self.assertEqual(xdg_state_dir(), Path("/custom/state"))

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_default_if_env_not_set(self):
        expected = Path.home() / ".local" / "state"
        self.assertEqual(xdg_state_dir(), expected)


class TestXdgCacheDir(unittest.TestCase):
    @patch.dict(os.environ, {"XDG_CACHE_HOME": "/custom/cache"})
    def test_returns_env_variable_if_set(self):
        self.assertEqual(xdg_cache_dir(), Path("/custom/cache"))

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_default_if_env_not_set(self):
        expected = Path.home() / ".cache"
        self.assertEqual(xdg_cache_dir(), expected)
