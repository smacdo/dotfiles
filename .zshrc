# Author: Scott MacDonald <root@smacdo.com>
# Purpose: Shared zsh shell configuration.
################################################################################
# zshrc is used to configure a user's shell (aliases, functions, settings, etc)
# intended for use in an interactive shell.

#==============================================================================#
# Sources the first valid file from a list of potential source files. Once a
# valid file is sourced the remaining paths are skipped.
#
# Args:
#    - one or more paths to a zsh or shell script file.
#==============================================================================#
source_first() {
  for x in "$@"; do
    # TODO: double check that `-f` works for symlinked files.
    # -f checks if the path is a file.
    # -r checks if the path is readable by the user.
    if [ -f "${x}" ] && [ -r "${x}" ]; then
        source "${x}"
        unset x
        return
    fi
  done
  unset x
}

# Export the dotfiles path as an environment variable to avoid hardcoding paths.
# TODO: Is it possible to support installations other than ~/.dotfiles ?
if [ -z ${S_DOTFILE_ROOT+x} ]; then
  export S_DOTFILE_ROOT="$HOME/.dotfiles"
fi

# Load optional per-machine override configs before applying additional dotfile
# configurations.
#
# Only use these configurations if you need to specify a per-machine config
# _prior_ to this custom .zshrc. If your overrides are not order sensitive then
# see instructions near the bottom of this script.
source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/0_my_shell_profile.sh" \
  "${HOME}/.0_my_shell_profile.sh"

source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/0_my_zshrc.sh" \
  "${HOME}/.0_my_zshrc.sh"

# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to reduce duplication.
for file in "${S_DOTFILE_ROOT:-$HOME/.dotfiles}"/shell_profile/\
{xdg.sh,paths.sh,env.sh,functions.sh,aliases.sh,private_branch.sh}; do
    source_first "$file"
done;
unset file

# Load .dotfiles shared zsh modules.
for file in ~/.zsh/*.zsh; do
    . "$file"
done
unset file

#==============================================================================
# Make sure we can store a decent amount of history lines
HISTSIZE=10000          # Ten thousand entries for in-memory storage.
SAVEHIST=1000000        # One million entries
HISTFILE=${XDG_STATE_HOME:-${HOME}/.local/state}/zsh_history

setopt SHARE_HISTORY      # Share history across multiple zsh sessions.
setopt APPEND_HISTORY     # Append to history file instead of overwriting.
setopt INC_APPEND_HISTORY # Update history after every command.
setopt HIST_FIND_NO_DUPS  # Ignore duplicates when searching
setopt HIST_REDUCE_BLANKS # Remove blank lines from history.

# Use ctrl-x ctrl-e to edit the command line with $EDITOR (bash emulation).
autoload -U edit-command-line
zle -N edit-command-line
bindkey '^xe' edit-command-line
bindkey '^x^e' edit-command-line

# Load the tab autocompletion system
autoload -Uz compinit

setopt COMPLETE_ALIASES # autocompletion of cli switches for aliases

zstyle ':completion:*' group-name ''
zstyle ':completion:*' list-colors '${(s.:.)LS_COLORS}'
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s

# message formatting
zstyle ':completion:*:descriptions' format '%U%B%d%b%u'
zstyle ':completion:*:warnings' format '%BNo matches for: %d%b'

# describe options in full
zstyle ':completion:*:options' description 'yes'
zstyle ':completion:*:options' auto-description '%d'

# use completion caching
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path "${HOME}/.zsh_cache"

# case-insensitive completion (uppercase from lowercase & underscores from dashes)
zstyle ':completion:*' matcher-list 'm:{a-z-}={A-Z_}'

# enable powerful pattern-based renaming
autoload zmv

setopt autocd                # change to a diretory if typed alone
setopt no_beep               # disable beep on all errors
setopt EXTENDED_GLOB
setopt CORRECT_ALL           # Suggest corrections to mistyped commands and paths.
setopt NOMATCH               # Turn errors back on for empty globbing with init finished.

# Prevent shell output from overwriting regular files.
# Use `>|` to override, eg `echo "output" >| file.txt"
set -o noclobber

# Use the powerlevel10k theme or warn if not installed.
if is_osx; then
  if type brew &>/dev/null; then
    if [[ -f "$(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme" ]]; then
        source "$(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme"
    elif [[ -f "$(brew --prefix)/opt/powerlevel10k/powerlevel10k.zsh-theme" ]]; then
        source "$(brew --prefix)/opt/powerlevel10k/powerlevel10k.zsh-theme"
    fi
  fi
elif [[ -f "${XDG_DATA_HOME:-~/.local/share}"/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source "${XDG_DATA_HOME:-~/.local/share}"/powerlevel10k/powerlevel10k.zsh-theme
elif [[ -f /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme
fi

# Load powerlevel10k, a ZSH plugin for making fancy prompts.
# To customize run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Make less more friendly for non-text input files, see lesspipe(1).
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Additional ZSH completions.
# TODO: Finish this for debian, fedora, ubuntu installs.
if is_osx; then
  if type brew &>/dev/null; then
    FPATH=$(brew --prefix)/share/zsh-completions:$FPATH
    autoload -Uz compinit
  fi
fi

# Load iTerm2 shell integration script.
if [ "${TERM_PROGRAM}" = "iTerm.app" ]; then
    source "${S_DOTFILE_ROOT}/vendor/iterm2/zsh"
fi

# Load fzf support.
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Finish zsh auto completion init.
compinit

# Apply optional per-machine configuration settings at the end of .bashrc. These
# files should not be checked in the dotfiles repo because they are meant to
# apply to individual machine set ups.
#
# You can use the `my_shell_profile.sh` option if you want options to apply to
# bash and zsh. Otherwise for zsh specific changes use `my_zshrc.sh`.
source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/my_shell_profile.sh" \
  "${HOME}/.my_shell_profile.sh"

source_first \
  "${XDG_CONFIG_HOME:-${HOME}/.config}/dotfiles/my_zshrc.sh" \
  "${HOME}/.my_zshrc.sh"

# Load zsh syntax highlighting plugin. According to install instructions this
# line must be last in the .zshrc file.
# TODO: Source the correct path on Debian, Fedora, Windows.
if is_osx; then
  if type brew &>/dev/null; then
    [[ ! -f "$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]]\
      || source "$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
  fi
else
  [[ ! -f "/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]]\
    || source "/usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi

### end of config - there should be no lines below this one! ###