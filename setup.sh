#!/bin/bash
# Author: Scott MacDonald <scott@smacdo.com>
# 
# Configures a *nix environment to use the scripts and configuration values
# contained in this git repository. Once this script is run, further system
# bootstrapping can be performed with scripts found in `postinit`.

# Check if stdout is a terminal.
if test -t 1; then
    # Check if colors are supported.
    colorCount=$(tput colors)

    if test -n "$colorCount" && test "$colorCount" -ge 0; then
        bold="$(tput bold)"
        underline="$(tput smul)"
        standout="$(tput smso)"
        normal="$(tput sgr0)"
        black="$(tput setaf 0)"
        red="$(tput setaf 1)"
        green="$(tput setaf 2)"
        yellow="$(tput setaf 3)"
        blue="$(tput setaf 4)"
        magenta="$(tput setaf 5)"
        cyan="$(tput setaf 6)"
        white="$(tput setaf 7)"
    fi
fi

# Bail out if this doesn't look like the checkout directory.
if [[ ! -f "./setup.sh" ]] || [[ ! -f "./README" ]]; then
  echo "${red}Please run this script from the root directory of the git " \
    "checkout${normal}"
  exit 1
fi

# Ask the user for confirmation before continuing.
checkout_dir=$PWD

echo "This script will configure your environment to use the settings and other"
echo "goodies contained in this dotfiles repository."
echo " "
echo "It looks like the current directory is: $checkout_dir"

read -rp "${bold}Is this the root directory of the git checkout? (y|n)${normal} "

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Load XDG values prior to setup.
. "${checkout_dir}/shell_profile/xdg.sh"

# Create common directories
echo "${magenta}Creating directories...${normal}"

mkdir -vp "${XDG_STATE_HOME}/vim/backups"
mkdir -vp "${XDG_STATE_HOME}/vim/tmp"

################################################################################
# Safely symlink a file by checking for potential errors and interactively
# asking the user how to fix aforementioned bad situations.
#
# Globals:
#
# Arguments:
#  1. SOURCE   Path to the source file (the original physical file).
#  2. TARGET   Path to the target file (a new file that will be a symlink).
#
# Outputs:
#  Zero if the symlink was created, otherwise a non-zero error value.
################################################################################
safe_symlink()
{
    SOURCE=$1
    TARGET=$2

    # Make sure source and target were given.
    if [ $# -lt 2 ]; then
        echo "${red}ERROR: Missing source and or target arguments${normal}"
        exit 1
    fi

    if [ -z "$TARGET" ]; then
        echo "${red}ERROR: Target argument not given or empty${normal}"
        exit 1
    fi

    if [ -z "$SOURCE" ]; then
        echo "${red}ERROR: Source argument not given or empty${normal}"
        exit 1
    fi

    # Check if target already exists before symlinking.
    if [ ! -f "$TARGET" ] && [ ! -d "$TARGET" ]; then
        # Target does not exist, go ahead and symlink.
        echo "${blue}Symlinking $TARGET => $SOURCE${normal}"
        ln -s "$SOURCE" "$TARGET"
    else
        # Target file exists. Check for these conditions:
        #  1. Is Symlink => Skip if symlink points to $SOURCE, else error.
        #  2. Is regular file => Back it up to $TARGET.bak (if $TARGET.bak does not exist).
        #  3. Else => Error.
        local FOUND_CONDITION=0

        if [ "$(readlink -- "$TARGET")" = "$SOURCE" ]; then
            echo "${yellow}$TARGET is already symlinked to $SOURCE.${normal}"
            FOUND_CONDITION=1
        fi

        if [ ! -e "$TARGET.bak" ] && [ $FOUND_CONDITION -eq 0 ]; then
            # Ask user for permission.
            read -rp "${bold}Can I rename $TARGET to $TARGET.bak before "\
                "symlinking? (y|n)${normal} "
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi

            # Rename existing target file.
            echo "${blue}Renaming $TARGET to $TARGET.bak${normal}"
            mv "$TARGET" "${TARGET}.bak"

            # Now symlink target.
            echo "${blue}Creating symlink $TARGET => $SOURCE${normal}"
            ln -s "$SOURCE" "$TARGET"

            FOUND_CONDITION=1
        fi

        # If we couldn't handle the $TARGET existing by this point, just error.
        if [ $FOUND_CONDITION -eq 0 ]; then
            echo "${red}ERROR: $TARGET already exists. Please remove it and " \
                "re-run the script${normal}".
            exit 1
        fi
    fi
}

# Symlink useful dotfiles
echo "${magenta}Symlinking dotfiles...${normal}"

safe_symlink "$checkout_dir/.gitconfig" "$HOME/.gitconfig"
safe_symlink "$checkout_dir/.vimrc" "$HOME/.vimrc"
safe_symlink "$checkout_dir/.vim" "$HOME/.vim"
safe_symlink "$checkout_dir/.bash_profile" "$HOME/.bash_profile"
safe_symlink "$checkout_dir/.bashrc" "$HOME/.bashrc"
safe_symlink "$checkout_dir/.zshrc" "$HOME/.zshrc"
safe_symlink "$checkout_dir/.p10k.zsh" "$HOME/.p10k.zsh"
safe_symlink "$checkout_dir/zsh_files" "$HOME/.zsh"
safe_symlink "$checkout_dir/.dircolors" "$HOME/.dircolors"
safe_symlink "$checkout_dir/.tmux.conf" "$HOME/.tmux.conf"
safe_symlink "$checkout_dir/.inputrc" "$HOME/.inputrc"
safe_symlink "$checkout_dir/.profile" "$HOME/.profile"

# Create machine local configuration files.
if [[ -f "${HOME}/.shell_profile.sh" ]]; then
    echo "${yellow}${bold}WARNING: ${HOME}/.shell_profile.sh exists!${normal}"
else
    touch "${HOME}/.shell_profile.sh"
fi

# Install fonts
# TODO: Make this a configurable option.
mkdir -pv "$HOME/.fonts/"

safe_symlink "$checkout_dir/fonts/liberation" "$HOME/.fonts/liberation"
safe_symlink "$checkout_dir/fonts/ubuntu" "$HOME/.fonts/ubuntu"
safe_symlink "$checkout_dir/fonts/consola" "$HOME/.fonts/consola"

# Clone plugins locally (rather than have them checked into the dotfiles repo).
echo "${magenta}Cloning plugins locally...${normal}"

################################################################################
# Checkout a git repository to a target directory, and update it to point at the
# given tag.
#
# Arguments:
#  1. NAME     Friendly name of the repository (for pretty printing).
#  2. TAG      Tag to update the repository to..
#  3. GIT_URL  URL to clone repository from.
#  4. DEST     Destination directory to clone repository to.
################################################################################
fetch_git_tag() {
    NAME=$1
    TAG=$2
    GIT_URL=$3
    DEST=$4

    # TODO: Argument validation.
    
    # Clone the repository if the directory doesn't already exist.
    if [ ! -d "$DEST" ]; then
        echo "${blue}Cloning git repository for $NAME${normal}"
        git clone "$GIT_URL" "$DEST" || return 1
    else
        echo "${yellow}Destination exists, skipping checkout.${normal}"
    fi

    # Update to the requested tag.
    echo "${blue}Updating ${NAME} to tag ${TAG}${normal}"
    (cd "$DEST" && git -c advice.detachedHead=false checkout "tags/${TAG}")
}

fetch_git_tag powerlevel10k "v1.15.0" \
    "https://github.com/romkatv/powerlevel10k.git" \
    "${XDG_DATA_HOME}/dotfiles/zsh/powerlevel10k"

fetch_git_tag ZshSyntaxHighlighting "0.7.1" \
    "https://github.com/zsh-users/zsh-syntax-highlighting.git" \
    "${XDG_DATA_HOME}/dotfiles/zsh/zsh-syntax-highlighting"
