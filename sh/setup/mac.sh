#!/bin/bash
# Author: Scott MacDonald
# Purpose:

# TODO: Rename to macos.sh
# TODO: Use err

# Double check that this is MacOS before proceeding.
if [[ ! is_osx ]]; then
    echo "This script only works on MacOS boxes."
    return 1
fi

if [[ -z "$S_DOTFILE_ROOT" ]]; then
  echo "$$S_DOTFILE_ROOT is not set - you might need to restart your shell"
  return 1
fi

# Install fonts.
# (Do not overwrite any fonts that already exist in ~/Library/Fonts).
echo "Installing fonts..."

cp -n "${S_DOTFILE_ROOT}/fonts/consola"/* ~/Library/Fonts
cp -n "${S_DOTFILE_ROOT}/fonts/hack"/* ~/Library/Fonts
cp -n "${S_DOTFILE_ROOT}/fonts/jetbrains"/* ~/Library/Fonts

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

# Update Homebrew.
echo "Updating Homebrew..."
brew doctor
brew update

# Install common packages for Mac OS
brew install vim
brew install htop fzf neovim ripgrep tmux zsh mosh
brew install zoom

brew install --cask sublime-text
brew install --cask iterm2
brew install --cask messenger-native

# also: --cask workplace-chat
#              microsoft-outlook

# Install developer packages for Mac OS
#brew install cmake clang-format
brew install --cask visual-studio-code
