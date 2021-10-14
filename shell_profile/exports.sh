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

# Some programs require this environment variable to show color.
export CLICOLOR=1

# Hide the “default interactive shell is now zsh” warning on macOS.
export BASH_SILENCE_DEPRECATION_WARNING=1

# Adds color highlighting to less (which includes man pages).
#  http://boredzo.org/blog/archives/2016-08-15/colorized-man-pages-understood-and-customized
export LESS="-R -q"
LESS_TERMCAP_mb=$(printf '\E[1;31m')     # begin blink
LESS_TERMCAP_md=$(printf '\E[1;32m')     # begin bold
LESS_TERMCAP_me=$(printf '\E[0m')        # reset bold/blink
LESS_TERMCAP_so=$(printf '\E[01;44;33m') # begin reverse video
LESS_TERMCAP_se=$(printf '\E[0m')        # reset reverse video
LESS_TERMCAP_us=$(printf '\E[1;94m')     # begin underline
LESS_TERMCAP_ue=$(printf '\E[0m')        # reset underline

export LESS_TERMCAP_mb
export LESS_TERMCAP_md
export LESS_TERMCAP_me
export LESS_TERMCAP_so
export LESS_TERMCAP_se
export LESS_TERMCAP_us
export LESS_TERMCAP_ue

# ls colors (MacOS)
export CLICOLOR=1
export LSCOLORS=ExFxCxDxBxegedabagacad
