#!/usr/bin/env bash
# Author: Scott MacDonald <root@smacdo.com>
# Purpose: Shared bash shell configuration.
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
[[ -z "$DOTFILE_CI_TEST_MODE" ]] && [[ $- != *i* ]] && return

#==============================================================================#
# Sources the first valid file from a list of potential source files. Once a
# valid file is sourced the remaining paths are skipped.
#
# Args:
#    - one or more paths to a bash or shell script file.
#==============================================================================#
source_first() {
  for path in "$@"; do
    # TODO: double check that `-f` works for symlinked files.
    # -f checks if the path is a file.
    # -r checks if the path is readable by the user.
    if [ -f "${path}" ] && [ -r "${path}" ]; then
        source "${path}"
        unset path
        return
    fi
  done
  unset path
}

# Export the dotfiles path as an environment variable to avoid hardcoding paths.
# TODO: Is it possible to support installations other than ~/.dotfiles ?
if [ -z ${S_DOTFILE_ROOT+x} ]; then
  export S_DOTFILE_ROOT="$HOME/.dotfiles"
fi

# Load optional per-machine override configs before applying additional dotfile
# configurations.
#
# Only use these configurations if you need to specify a per-machine config
# _prior_ to this custom .bashrc. If your overrides are not order sensitive then
# see instructions near the bottom of this script.
source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/0_my_shell_profile.sh" \
  "${HOME}/.0_my_shell_profile.sh"

source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/0_my_bashrc.sh" \
  "${HOME}/.0_my_bashrc.sh"


# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to reduce duplication.
#
# If you want to have machine specific stuff the best place to put it is in
# ~/.my_shell_profile.sh or ~/.my_bash_rc. These files are sourced at the end
# this config.
for file in $S_DOTFILE_ROOT/shell_profile/\
{xdg.sh,paths.sh,env.sh,functions.sh,aliases.sh}; do
    source_first "$file"
done;
unset file

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
shopt -s histappend
PROMPT_COMMAND="history -a; $PROMPT_COMMAND"  # Append new commands each time prompt is displayed.

HISTSIZE=10000          # Ten thousand entries for in-memory storage.
HISTFILESIZE=1000000    # One million entries
HISTCONTROL=ignoredups  # Do not write duplicate commands to history.
HISTFILE=${XDG_STATE_HOME:-${HOME}/.local/state}/bash_history_actual # Use non-standard name to avoid wiping out history file.

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
# TODO: Finish this for debian, fedora, windows installs.
if is_osx; then
  if type brew &>/dev/null; then
    [[ -r "$(brew --prefix)/etc/profile.d/bash_completion.sh" ]] && \
      . "$(brew --prefix)/etc/profile.d/bash_completion.sh"
  fi
fi

[[ -r "/usr/share/bash-completion/bash_completion" ]] && \
    . "/usr/share/bash-completion/bash_completion"

# Load iTerm2 shell integration
if [ "${TERM_PROGRAM}" = "iTerm.app" ]; then
  source "${S_DOTFILE_ROOT:${HOME}/.dotfiles/}/vendor/iterm2/bash"
fi

# Load fzf support.
[ -f ~/.fzf.bash ] && source ~/.fzf.bash

# Apply optional per-machine configuration settings at the end of .bashrc. These
# files should not be checked in the dotfiles repo because they are meant to
# apply to individual machine set ups.
#
# You can use the `my_shell_profile.sh` option if you want options to apply to
# bash and zsh. Otherwise for bash specific changes use `my_bashrc.sh`.
source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/my_shell_profile.sh" \
  "${HOME}/.my_shell_profile.sh"

source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/my_bashrc.sh" \
  "${HOME}/.my_bashrc.sh"

### end of config - there should be no lines below this one! ###
