import os
import unittest
from pathlib import Path
from unittest.mock import patch


def xdg_config_dir() -> Path:
    """Returns the base directory for user-specific config files."""
    if "XDG_CONFIG_HOME" in os.environ:
        return Path(os.environ["XDG_CONFIG_HOME"])
    else:
        return Path.home().joinpath(".config")


def xdg_data_dir() -> Path:
    """Returns the base directory for user-specific data files."""

    if "XDG_DATA_HOME" in os.environ:
        return Path(os.environ["XDG_DATA_HOME"])
    else:
        return Path.home().joinpath(".local/share")


def xdg_state_dir() -> Path:
    """Returns the base directory for user-specific state files."""

    if "XDG_STATE_HOME" in os.environ:
        return Path(os.environ["XDG_STATE_HOME"])
    else:
        return Path.home().joinpath(".local/state")


def xdg_cache_dir() -> Path:
    """Returns the base directory for user-specific non-essential data files."""

    if "XDG_CACHE_HOME" in os.environ:
        return Path(os.environ["XDG_CACHE_HOME"])
    else:
        return Path.home().joinpath(".cache")


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
