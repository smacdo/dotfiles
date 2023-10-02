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
#
# NOTE: The new preferred local dir for homebrew is `.homebrew`. Continue to
#       support the older directory but only add it if it is detected. Add the
#       other path by default to allow the case of booting into this profile,
#       installing Homebrew locally and then commands should "just work".
if [ -d "$HOME/homebrew/bin" ]; then
  add_path_front "$HOME/homebrew/bin"
fi

add_path_front "$HOME/.homebrew/bin"
add_path_front "$HOME/.homebrew/sbin"

# Also support scripts from dotfiles (this will override ~/homebrew).
add_path_back "$S_DOTFILE_ROOT/bin"

# Also support scripts in user bin (overriding previous).
add_path_back "$HOME/bin"



