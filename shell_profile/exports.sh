#!/bin/sh
################################################################################
# This file defines environment variables that are common to all shell sessions.
#
# NOTE: This file might be sourced more than once, especially for interactive
# login shell session.
################################################################################
# Make vim the default editor.
export EDITOR='vim'

# Rust cargo.
if [ -f "$HOME/.cargo/env" ]; then
    . "$HOME/.cargo/env"
fi

# TODO: Move below to interactive shell only exports?  ####
 
# Some programs require this environment variable to show color.
export CLICOLOR=1

# Hide the “default interactive shell is now zsh” warning on macOS.
export BASH_SILENCE_DEPRECATION_WARNING=1

# ls colors (MacOS)
export CLICOLOR=1
export LSCOLORS=ExFxCxDxBxegedabagacad
