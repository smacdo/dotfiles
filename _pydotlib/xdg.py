import os
from pathlib import Path


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