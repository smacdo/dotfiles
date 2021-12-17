#!/bin/bash
# Author: Scott MacDonald
# Purpose: Installs Homebrew along with commonly used applications.
#===============================================================================

################################################################################
#
################################################################################
check_brew_ok() {
  brew doctor && return 0
  # TODO: Prompt user to continue with the issues listed.
  echo "Please address brew issues before re-running this script"
  exit 1
}

if [[ ! is_osx ]]; then
    echo "This script only works on MacOS boxes."
    return 1
fi

# Install Homebrew if not installed.
if [[ ! "$(type -p brew)" ]]; then
    echo "Installing homebrew..."
    true | /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
else
    echo "Homebrew already installed!"
fi

# Report an error if still not installed.
if [[ ! "$(type -p brew)" ]]; then
    echo "ERROR: Homebrew failed to install :("
    return 1
fi

# Check for any brew issues before continuing onward to installing packages.
# TODO: Add command line option to skip this check.

# Update Homebrew.
echo "Updating Homebrew..."
brew doctor
brew update

# Get brew dir prefix.
BREW_PREFIX=$(brew --prefix)

# Install GNU core utilities for simpler crossplatform scripts.
brew install coreutils findutils grep

# Install GNU `sed`, overwriting the built-in `sed`.
brew install gnu-sed

# Install a more modern version of bash.
brew install bash bash-completion@2

# Install common packages for Mac OS
brew install vim git git-lfs htop fzf neovim ripgrep tmux zsh mosh highlight

brew install --cask 1password
brew install --cask sublime-text
brew install --cask iterm2

# also: --cask workplace-chat
#              microsoft-outlook

# Install developer packages for Mac OS
brew install cmake clang-format
brew install --cask visual-studio-code

# All done!
brew cleanup
