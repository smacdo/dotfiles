#############################################################################
# Scott's zshrc                                                             #
# -------------                                                             #
#    Maintainer: Scott MacDonald <scott@whitespaceconsideredharmful.com>    #
#    Version   : 1.0                                                        #
#############################################################################
# Our default is always, and will always, be vi
export EDITOR=vim

# Give me colors on the terminal
export CLICOLOR=1

# Make sure we can store a decent amount of history lines
HISTSIZE=2000
SAVEHIST=2000
HISTFILE=~/.zsh_history

setopt SHARE_HISTORY      # Share history across multiple zsh sessions.
setopt APPEND_HISTORY     # Append to history file instead of overwriting.
setopt INC_APPEND_HISTORY # Update history after every command.
setopt HIST_FIND_NO_DUPS  # Ignore duplicates when searching
setopt HIST_REDUCE_BLANKS # Remove blank lines from history.

# Load all extra zsh modules
for file in ~/.zsh/*.zsh; do
    . $file
done

# Load local zsh modules
setopt null_glob

for file in ~/.zsh_local/*.zsh; do
    . $file
done

# Load the tab autocompletion system
autoload -Uz compinit
compinit

setopt COMPLETE_ALIASES # autocompletion of cli switches for aliases

# 
autoload -Uz promptinit
promptinit

prompt redhat
bindkey -v  # use vi-style command line editing
stty -ixon  # disable ^S/^Q (XON/XOFF) flow control

zstyle ':completion:*' group-name ''
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt %SAt %p: Hit TAB for more, or the character to insert%s

# message formatting
zstyle ':completion:*:descriptions' format '%U%B%d%b%u'
zstyle ':completion:*:warnings' format '%BNo matches for: %d%b'

# describe options in full
zstyle ':completion:*:options' description 'yes'
zstyle ':completion:*:options' auto-description '%d'

# use completion caching
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path ${HOME}/.zsh_cache

# case-insensitive completion (uppercase from lowercase & underscores from dashes)
zstyle ':completion:*' matcher-list 'm:{a-z-}={A-Z_}'

# enable powerful pattern-based renaming
autoload zmv

setopt autocd                # change to a diretory if typed alone
setopt no_beep               # disable beep on all errors
setopt EXTENDED_GLOB
setopt CORRECT_ALL # Suggest corrections to mistyped commands and paths.
setopt NOMATCH # Turn errors back on for empty globbing with init finished.
