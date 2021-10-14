#!/bin/sh
################################################################################
# Adds a directory to the PATHS environment variable only if it was not already
# added.
#
# Ref: https://unix.stackexchange.com/a/124447
################################################################################
appendToPath() {
    if [ -z "$1" ]; then
        echo "ERROR: Missing path to add"
        return 1
    fi

    case ":${PATH:=$1}:" in
        *:"$1":*)   ;;
        *) PATH="$1:$PATH"   ;;
    esac
}

appendToPath "$HOME/bin"
appendToPath "$S_DOTFILE_ROOT/bin"
