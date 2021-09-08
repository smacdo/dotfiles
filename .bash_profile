## Author: Scott MacDonald <scott@smacdo.com>
## Date: 02/29/2012
################################################################################
# bash_profile is used to set environment variables and other things that should
# happen at login. This file is only sourced in login shells (e.g., the shell
# that was started when you log in via SSH) and not when you create a new
# terminal window (e.g., xterm) or when typing `/bin/bash/` into a terminal.
#
# EXCEPTION:
#  MacOS X, the Terminal by default runs a login shell every time but this
#  behavior can be changed.

# Source bashrc to pull in configuration for interactive shell use. Note that my
# .bashrc was modified to immediately return if the shell is not interactive.
if [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Load custom environment variables.
if [ -f "$HOME/.shell_profile/.exports" ]; then
    source "$HOME/.shell_profile/.exports"
fi

# Load cargo environment variables.
if [ -f "$HOME/.cargo/env" ]; then
    source "$HOME/.cargo/env"
fi
