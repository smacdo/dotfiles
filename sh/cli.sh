#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Shared functions for postsetup scripts for different *nix distros.
###############################################################################
# Configure formatted text output if available.
# 1. Check if stdout is a terminal
if test -t 1; then
  # 2. Check if colors are supported.
  colorCount=$(tput colors)

  if test -n "${colorCount}" && test "${colorCount}" -ge 0; then
    normal="$(tput sgr0)"
    bold="$(tput bold)"
    red="$(tput setaf 1)"
  fi
fi

###############################################################################
# Prints error text to the console.
#
# Arguments:
#  $*: Error message.
###############################################################################
error() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S%z') ${bold}${red}ERROR${normal}]: "\
    "${red}$*${normal}" >&2
}

###############################################################################
# Prints error text to the console and then exits the process.
#
# Arguments:
#  $1: Exit code. 
#  $*: Error message.
###############################################################################
exit_with_message() {
  exit_code="$1"
  shift;

  if [ -z "$exit_code" ]; then
    exit_code=1
  fi

  error "$@"
  exit "$exit_code"
}

###############################################################################
# Enables or disable verbose mode.
#
# Arguments:
#  $1: 0 to disable verbose mode, 1 to enable. (Optional, default is 1).
#
# Globals:
#  VERBOSE
###############################################################################
set_verbose() {
  if [ -z "$1" ]; then
    export VERBOSE=1
  else
    export VERBOSE="$1"
  fi
}

###############################################################################
# Print verbose text (if enabled) to stdout.
#
# Arguments:
#  $*: Message to show.
#
# Globals:
#  VERBOSE: The message is only printed to stdout if VERBOSE=1
###############################################################################
verbose() {
  if [ "$VERBOSE" = "1" ]; then
    echo "$@"
  fi
}

###############################################################################
# Prints an action message to stdout.
#
# Arguments:
#  $*: Message to show.
###############################################################################
print_action() {
  echo "$@"
}

###############################################################################
# Terminates process if user is not root.
###############################################################################
die_if_not_root() {
  if [ "$(id -u)" != 0 ]; then
    exit_with_message 10 "This script must be run as root (sudo)"
  fi
}

