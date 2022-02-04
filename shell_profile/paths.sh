#!/bin/sh
# This file configures the $PATH environment variable for a shell session.

################################################################################
# Add a new directory to the front of the PATH environment variable if it was
# not already present.
#
# Arguments:
#  $1: The path to add. If it does not exist it will not be added.
#
# Ref: https://unix.stackexchange.com/a/124447
################################################################################
add_path_front() {
    if [ -z "$1" ]; then
        echo "ERROR: Missing path to add"
        return 1
    fi

    if [ -d "$1" ]; then
      case ":${PATH:=$1}:" in
          *:"$1":*)   ;;
          *) PATH="$1:$PATH"   ;;
      esac
    fi
}

################################################################################
# Add a new directory to the end of the PATH environment variable if it was not
# already present.
#
# Arguments:
#  $1: The path to add. If it does not exist it will not be added.
################################################################################
add_path_back() {
    if [ -z "$1" ]; then
        echo "ERROR: Missing path to add"
        return 1
    fi
    
    if [ -d "$1" ]; then
      case ":${PATH:=$1}:" in
          *:"$1":*)   ;;
          *) PATH="$PATH:$1"   ;;
      esac
    fi
}

# The rust tool 'cargo' install binaries to the user's home directory.
# (prepended in case cargo needs to override system installed rustc).
add_path_back "$HOME/.cargo/bin"

# Support local homebrew installs (~/homebrew)
add_path_front "$HOME/homebrew/bin"

# Also support scripts from dotfiles (this will override ~/homebrew).
add_path_back "$S_DOTFILE_ROOT/bin"

# Also support scripts in user bin (overriding previous).
add_path_back "$HOME/bin"



