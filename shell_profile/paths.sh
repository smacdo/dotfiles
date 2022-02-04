#!/bin/sh
################################################################################
# Adds a directory to the PATHS environment variable only if it was not already
# added.
#
# Ref: https://unix.stackexchange.com/a/124447
################################################################################
add_path_front() {
    if [ -z "$1" ]; then
        echo "ERROR: Missing path to add"
        return 1
    fi

    case ":${PATH:=$1}:" in
        *:"$1":*)   ;;
        *) PATH="$1:$PATH"   ;;
    esac
}

add_path_back() {
    if [ -z "$1" ]; then
        echo "ERROR: Missing path to add"
        return 1
    fi

    case ":${PATH:=$1}:" in
        *:"$1":*)   ;;
        *) PATH="$PATH:$P1"   ;;
    esac
}

# Support local homebrew installs (~/homebrew)
if [ -d "$HOME/homebrew/bin" ]; then
  add_path_front "$HOME/homebrew/bin"
fi

# Support dotfile scripts (~/.dotfiles/bin)
if [ -d "$S_DOTFILE_ROOT" ]; then 
  add_path_front "$S_DOTFILE_ROOT/bin"
fi

# Add dotfile scripts (~/bin)
if [ -d "$HOME/bin" ]; then
  add_path_front "$HOME/bin"
fi


