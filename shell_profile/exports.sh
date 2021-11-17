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

# Adds color highlighting to less (which includes man pages).
# References:
#  http://boredzo.org/blog/archives/2016-08-15/colorized-man-pages-understood-and-customized
#  https://unix.stackexchange.com/a/108840
#  https://unix.stackexchange.com/a/329092
#  https://linuxcommand.org/lc3_adv_tput.php
#
# Other notes
#  "Stand out mode is reverse on many terminals, bold on others"
export LESS="-R -q"

LESS_TERMCAP_mb=$(tput bold; tput setaf 2) # Begin bold; use bold + green fg.
LESS_TERMCAP_md=$(tput bold; tput setaf 6) # Begin blink: use bold + teal fg.
LESS_TERMCAP_me=$(tput sgr0)               # End bold/blink: Reset.
LESS_TERMCAP_so=$(tput smso; tput setaf 3; tput setab 4) # Begin reverse video: yellow on blue.
LESS_TERMCAP_se=$(tput rmso; tput sgr0)    # End reverse video: End standout, reset fg bg color.
LESS_TERMCAP_us=$(tput smul; tput setaf 5) # Start underline, with white fg.
LESS_TERMCAP_ue=$(tput rmul; tput sgr0)    # End underline, reset formatting.

export LESS_TERMCAP_mb
export LESS_TERMCAP_md
export LESS_TERMCAP_me
export LESS_TERMCAP_so
export LESS_TERMCAP_se
export LESS_TERMCAP_us
export LESS_TERMCAP_ue
export GROFF_NO_SGR=1

# ls colors (MacOS)
export CLICOLOR=1
export LSCOLORS=ExFxCxDxBxegedabagacad
