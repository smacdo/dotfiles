#!/bin/sh
################################################################################
# This file defines environment variables that are common to all shell sessions.
#
# NOTE: This file might be sourced more than once, especially for interactive
# login shell session.
################################################################################
# Set the dotfile path if it hasn't already been defined.
# TODO: Is it possible to support installations other than ~/.dotfiles ?

if [ -z "${S_DOTFILE_ROOT+x}" ]; then
  export S_DOTFILE_ROOT="$HOME/.dotfiles"
fi

# Make neovim -> vim -> nano -> vi the default editor.
# (Weird note that `nvim -s` is not silent despite the man page on OSX stating
#  it doesn't print output!)
if which nvim >/dev/null; then
  export EDITOR='nvim'
else
  if which vim >/dev/null; then
    export EDITOR='vim'
  else
    if which nano >/dev/null; then
      export EDITOR='nano'
    else
      export EDITOR='vi'
    fi
  fi
fi

### TODO: Only apply these settings for interactive shells. ###
# Hide the "default interactive shell is now zsh" warning on macOS.
export BASH_SILENCE_DEPRECATION_WARNING=1

# Some programs require this environment variable to show color.
export CLICOLOR=1

# ls colors (MacOS)
export LSCOLORS=ExFxCxDxBxegedabagacad

# View more types of files with `less` if `lesspipe` is installed.
# Example: `less foo.zip`
if [ -x /opt/homebrew/bin/lesspipe.sh ]; then
  export LESSOPEN="|/opt/homebrew/bin/lesspipe.sh %s"
elif [ -x /usr/bin/lesspipe.sh ]; then
  export LESSOPEN="|/usr/bin/lesspipe.sh %s"
fi