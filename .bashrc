#############################################################################
# Scott's .bashrc                                                           #
#############################################################################
# Bail out if shell is not running interactively.
[ -z "$PS1" ] && return

# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to  reduce duplication.
#
# If you want to have machine specific stuff the best place to put it is in
# ~/.shell_local.
for file in $HOME/.shell_profile/.{paths,functions,exports,aliases,private}; do
    # -r test if FILE exists and is readable.
    # -f test if FILE exists and is a file.
    [ -r "$file" ] && [ -f "$file" ] && source "$file"
done;
unset file

# Flash the screen instead of playing an audio bell.
set bell-style visible

# Use case insensitive globbing when expanding pathnames.
shopt -s nocaseglob

# Autocorrect typos in path names when using `cd`
shopt -s cdspell

# Automatically 'cd' when entering just a path.
shopt -s autocd

# Sometimes bash doesn't get the resize signal from a terminal emulator after the terminal
# window is resized. This opton orces bash to recheck the window size after each command and
# update LINES, COLUMNS if needed.
shopt -s checkwinsize

# Append to bash history file rather than overwriting it.
shopt -s histappend

# Prevent shell output from overwriting regular files
# Use `>|` to override, eg `echo "output" >| file.txt"
set -o noclobber

# Set larger history file sizes.
HISTSIZE=10000
HISTFILESIZE=20000

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
    local        GRAY="\[\033[0;37m\]"
    local       GREEN="\[\033[0;32m\]"
    local LIGHT_GREEN="\[\033[1;32m\]"
    local  LIGHT_BLUE="\[\033[1;34m\]"
    local RESET_COLOR="\[\033[0m\]"

    # \u: The current user name.
    # \h: The machine hostname up to first dot.
    # \w: Current working directory.
    export PS1="$GREEN\u@\h$GRAY:$LIGHT_BLUE\w$RESET_COLOR\$ "
}

set_colored_prompt

# Make less more friendly for non-text input files, see lesspipe(1).
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"
