#!/bin/bash
#############################################################################
# Automated installation script
#  - This script will set up common directories, dot files and other system
#    settings
#############################################################################

# Bail out if this doesn't look like the checkout directory.
if [[ ! -f "./setup.sh" ]] || [[ ! -f "./README" ]]; then
  echo "Please run this script from the root directory of the git checkout"
  exit 1
fi

# Ask the user for confirmation before continuing.
checkout_dir=$PWD

echo "This script will automatically update your system to use common directories, "
echo "various dotfiles (zsh, vimrc, etc) and other assorted goodies. "
echo " "
echo "The current directory is: $checkout_dir"
echo " "

read -p "Is this the root directory of the git checkout? (y|n) "
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Create common directories
echo "Creating common directories..."

mkdir -vp $HOME/.zsh_local
mkdir -vp $HOME/.vim_runtime/backups
mkdir -vp $HOME/.vim_runtime/tmp

# Safely symlink file
safe_symlink()
{
    SOURCE=$1
    TARGET=$2

    # Make sure source and target were given.
    if [ $# -lt 2 ]; then
        echo "ERROR: Missing source and or target arguments"
        exit 1
    fi

    if [ -z "$TARGET" ]; then
        echo "ERROR: Target argument not given or empty"
        exit 1
    fi

    if [ -z "$SOURCE" ]; then
        echo "ERROR: Source argument not given or empty"
        exit 1
    fi

    # Check if target already exists before symlinking.
    if [ ! -f "$TARGET" ] && [ ! -d "$TARGET" ]; then
        # Target does not exist, go ahead and symlink.
        echo "Symlinking $TARGET => $SOURCE"
        ln -s $SOURCE $TARGET
    else
        # Target file exists. Check for these conditions:
        #  1. Is Symlink => Skip if symlink points to $SOURCE, else error.
        #  2. Is regular file => Back it up to $TARGET.bak (if $TARGET.bak does not exist).
        #  3. Else => Error.
        local FOUND_CONDITION=0

        if [ "$(readlink -- "$TARGET")" = "$SOURCE" ]; then
            echo "$TARGET is already symlinked to $SOURCE."
            FOUND_CONDITION=1
        fi

        if [ ! -e "$TARGET.bak" ] && [ $FOUND_CONDITION -eq 0 ]; then
            # Ask user for permission.
            read -p "Can I rename $TARGET to $TARGET.bak before symlinking? (y|n) "
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi

            # Rename existing target file.
            echo "Renaming $TARGET to $TARGET.bak"
            mv $TARGET $TARGET.bak

            # Now symlink target.
            echo "Creating symlink $TARGET => $SOURCE"
            ln -s $SOURCE $TARGET

            FOUND_CONDITION=1
        fi

        # If we couldn't handle the $TARGET existing by this point, just error.
        if [ $FOUND_CONDITION -eq 0 ]; then
            echo "ERROR: $TARGET already exists. Please remove it and re-run the script".
            exit 1
        fi
    fi
}

# Symlink useful dotfiles
echo "Symlinking dotfiles..."

safe_symlink "$checkout_dir/.vimrc" "$HOME/.vimrc"
safe_symlink "$checkout_dir/.vim" "$HOME/.vim"
safe_symlink "$checkout_dir/.bash_profile" "$HOME/.bash_profile"
safe_symlink "$checkout_dir/.bashrc" "$HOME/.bashrc"
safe_symlink "$checkout_dir/.zshrc" "$HOME/.zshrc"
safe_symlink "$checkout_dir/zsh_files" "$HOME/.zsh"
safe_symlink "$checkout_dir/.dircolors" "$HOME/.dircolors"
safe_symlink "$checkout_dir/.inputrc" "$HOME/.inputrc"

# Install fonts
# TODO: Make this a configurable option.
mkdir -pv $HOME/.fonts/

safe_symlink "$checkout_dir/fonts/liberation" "$HOME/.fonts/liberation"
safe_symlink "$checkout_dir/fonts/ubuntu" "$HOME/.fonts/ubuntu"
safe_symlink "$checkout_dir/fonts/consola" "$HOME/.fonts/consola"
