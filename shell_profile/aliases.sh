#!/bin/sh
# Author: Scott MacDonald
# -----------------------
# This file contains a set of useful shell aliases that should be included by all interactive
# shell session (bash and zsh). Some of these were written by me, others were collected in
# various form on the internet or from friend's dotfiles.
#
# TODO: Detect if the shell supports color and only enable color flags if this is true.

# v - Edit a file using the editor specified by the environment var $EDITOR.
# vi - Same as `v` command
alias v='/usr/bin/env "$EDITOR"'
alias vi='/usr/bin/env "$EDITOR"'

### ls
# `la`/`ll`/`lls` below inherit color via the `ls` alias (recursive first-word
# alias expansion), so they don't need to repeat the color flag.
if is_osx; then
    alias ls='ls -G'
else
    alias ls='ls --color'
fi

# List all files (including hidden files).
#  -a, --all      [do not ignore entries starting with '.']
alias la='ls -a'

# List files in a tabular form.
#  -a, --all      [do not ignore entries starting with `.`]
#  -l             [use a long listing format]
#  -F, --classify [append indicator (*/=>@|) to entries]
alias ll='ls -alF'

# List files in a tabular form with human readable sizes.
#  -a, --all      [do not ignore entries starting with `.`]
#  -l             [use a long listing format]
#  -F, --classify [append indicator (*/=>@|) to entries]
#  -h             [use human readable sizes]
alias lls='ls -alFh'

# go two directories up.
alias ...='../..'
alias ..2='../../'

# go three directories up.
alias ....='../../..'
alias ..3='../../..'

# go four directories up.
alias .....='../../../..'
alias ..4='../../../..'

# Get my local IP address.
if is_osx; then
    alias localip="ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'"
else
    alias localip="ip -o addr show up primary scope global | grep -o 'inet6\? [0-9a-f\.:]*' | cut -f 2 -d ' '"
fi

# Show active network interfaces.
# TODO: Make this work on Linux.
if is_osx; then
    alias ifactive="ifconfig | pcregrep -M -o '^[^\t:]+:([^\n]|\n\t)*status: active'"
fi

# Show a list of open ports on this machine.
if is_osx; then
    alias openports='netstat -an -p tcp -p udp'
else
    alias openports='netstat --all --numeric --programs --inet --inet6'
fi

# Get the size of a file in bytes.
# TODO: Find a way to report file size in largest useful increment (byte, kilo, mega etc).
if is_osx; then
    alias filesize="stat -f '%z bytes'"
else
    alias filesize="stat -c '%s bytes'"
fi

# Get a report on free disk space.
#  -h: Human readable output.
alias diskfree='df -h'

# Set du (disk usage) command to use -c [grand total] and -h [human readable] by default.
alias du='du -c -h'

# Make rm, mv, cp all confim intention to overwrite/delete for extra safety.
#  Use -f to override.
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'

# Colorize grep output.
alias grep='grep --color=auto'
alias fgrep='grep -F --color=auto'
alias egrep='grep -E --color=auto'
alias zgrep='zgrep --color=auto'
alias zegrep='zegrep --color=auto'
alias zfgrep='zfgrep --color=auto'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Prints the current path, with one directory per line (delegates to show_path).
alias printpath='show_path'

# Force shell to reload. This is brute force, not sure if recommended...
alias reloadshell="exec \"\${SHELL}\" -l"

# Start the screen saver.
if is_osx; then
    alias lock="/System/Library/CoreServices/ScreenSaverEngine.app/Contents/MacOS/ScreenSaverEngine"
elif [ "$XDG_CURRENT_DESKTOP" = "KDE" ]; then
    alias lock="qdbus org.freedesktop.ScreenSaver /ScreenSaver Lock"
elif [ "$XDG_CURRENT_DESKTOP" = "ubuntu:GNOME" ]; then
    alias lock="dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock"
else
    alias lock="echo 'TODO: Implement me'"
fi 

# Application shortcuts.
if is_osx; then
    alias chrome='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome'
    alias safari='/Applications/Safari.app/Contents/MacOS/Safari'
fi