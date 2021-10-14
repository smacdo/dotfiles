#!/bin/bash
# Installs Homebrew and adds functions to install recipes.
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

# Update Homebrew.
echo "Updating Homebrew..."
brew doctor
brew update

# Install common packages for Mac OS
brew install powerlevel10k
brew install htop fzf neovim ripgrep tmux zsh mosh
brew install zoom

brew install --cask sublime-text
brew install --cask iterm2
brew install --cask messenger-native

# Install developer packages for Mac OS
#brew install cmake clang-format
brew install --cask visual-studio-code
