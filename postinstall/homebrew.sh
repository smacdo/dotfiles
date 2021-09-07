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

echo "Homebrew is installed!"
