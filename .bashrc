#!/usr/bin/env bash
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Scott's bash shell configuration.
################################################################################
# bashrc is used to configure a user's shell (aliases, functions, settings, etc)
# intended for use in an interactive shell.
#
# Normally bash does not source this file when running as an interactive _login_
# shell - it will source `.bash_profile` instead. I've modified that file to make
# it also source this file. That means in all cases involving an interactive
# bash shell session this file will be loaded!
#
# In some circumstances bash will source .bashrc even though it is running as a
# non-interactive shell (e.g., when using scp). Check for this condition, and
# return immediately if the shell is not interactive.
[[ $- != *i* ]] && return

# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to reduce duplication.
#
# If you want to have machine specific stuff the best place to put it is in
# ~/.my_shell_profile.sh or ~/.my_bash_rc
for file in $S_DOTFILE_ROOT/shell_profile/\
{xdg.sh,paths.sh,exports.sh,functions.sh,aliases.sh}; do
    # -r test if readable, -f is file.
    [ -r "$file" ] && [ -f "$file" ] && source "$file"
done;
unset file

[ -r "${HOME}/.my_shell_profile.sh" ] && [ -f "${HOME}/.my_shell_profile.sh" ]\
&& source "${HOME}/.my_shell_profile.sh"

[ -r "${HOME}/.my_bash_rc.sh" ] && [ -f "${HOME}/.my_bash_rc.sh" ]\
&& source "${HOME}/.my_bash_rc.sh"

# Flash the screen instead of playing an audio bell.
set bell-style visible

# Use case insensitive globbing when expanding pathnames.
shopt -s nocaseglob

# Autocorrect typos in path names when using `cd`
shopt -s cdspell

# Automatically 'cd' when entering just a path.
# Note this is only supported on bash 4+ which is not shipped by default on Mac.
if [ "${BASH_VERSINFO:-0}" -ge 4 ]; then
  shopt -s autocd
fi

# Sometimes bash doesn't get the resize signal from a terminal emulator after the terminal
# window is resized. This opton orces bash to recheck the window size after each command and
# update LINES, COLUMNS if needed.
shopt -s checkwinsize

# Prevent shell output from overwriting regular files
# Use `>|` to override, eg `echo "output" >| file.txt"
set -o noclobber

## History
# Append to bash history file rather than overwriting it.
shopt -s histappend     # Append to bash history fle rather than overwriting it.

HISTSIZE=10000          # Ten thousand entries for in-memory storage.
HISTFILESIZE=1000000    # One million entries
HISTCONTROL=ignoredups  # Do not write duplicate commands to history.
HISTFILE=$XDG_STATE_HOME/bash_history_actual # Use non-standard name to avoid wiping out history file.

# Complete hostnames using this file
export HOSTFILE=~/.ssh/known_hosts

# Readline config
export INPUTRC=~/.inputrc

# Don't print the "you have new mail" notifications.
unset MAILCHECK

# List of file types to ignore
FIGNORE="~:CVS:#:.pyc:.swp:.swa:.o"

# Simple no-frills colored bash prompt.
function set_colored_prompt {
    local GRAY="\[\033[0;37m\]"
    local GREEN="\[\033[0;32m\]"
    local LIGHT_BLUE="\[\033[1;34m\]"
    local RESET_COLOR="\[\033[0m\]"

    # \u: The current user name.
    # \h: The machine hostname up to first dot.
    # \w: Current working directory.
    export PS1="$GREEN\u@\h$GRAY:$LIGHT_BLUE\w$RESET_COLOR\$ "
}

set_colored_prompt

# Make less more friendly for non-text input files, see lesspipe(1).
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Load bash auto-completions.
# TODO: Finish this for system wide homebrew, fedora, debian installs.
[[ -r "$HOME/homebrew/etc/profile.d/bash_completion.sh" ]] && \
  . "$HOME/homebrew/etc/profile.d/bash_completion.sh"

# Load iTerm2 shell integration
if [ "${TERM_PROGRAM}" = "iTerm.app" ]; then
  source "${S_DOTFILE_ROOT}/vendor/iterm2/bash"
fi

# Load fzf support.
[ -f ~/.fzf.bash ] && source ~/.fzf.bash
