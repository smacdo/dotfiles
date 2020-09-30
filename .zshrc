#############################################################################
# Scott's zshrc                                                             #
#############################################################################
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

#==============================================================================
# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to reduce duplication.
#
# If you want to have machine specific stuff the best place to put it is in
# ~/.shell_local.
for file in $HOME/.shell_profile/.{path,functions,exports,aliases,private}; do
    # -r test if FILE exists and is readable.
    # -f test if FILE exists and is a file.
    [ -r "$file" ] && [ -f "$file" ] && source "$file"
done;
unset file

# Load .dotfiles shared zsh modules.
for file in ~/.zsh/*.zsh; do
    . $file
done
unset file

# Load local only zsh moduls.
setopt null_glob

for file in ~/.zsh_local/*.zsh; do
    . $file
done
unset file

#==============================================================================
# Make sure we can store a decent amount of history lines
HISTSIZE=2000
SAVEHIST=2000
HISTFILE=~/.zsh_history

setopt SHARE_HISTORY      # Share history across multiple zsh sessions.
setopt APPEND_HISTORY     # Append to history file instead of overwriting.
setopt INC_APPEND_HISTORY # Update history after every command.
setopt HIST_FIND_NO_DUPS  # Ignore duplicates when searching
setopt HIST_REDUCE_BLANKS # Remove blank lines from history.

# Load the tab autocompletion system
autoload -Uz compinit
compinit

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
zstyle ':completion:*' cache-path ${HOME}/.zsh_cache

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
if [[ -f /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme
elif [[ -f $HOME/.dotfiles/vendor/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source $HOME/.dotfiles/vendor/powerlevel10k/powerlevel10k.zsh-theme
else
    echo "WARNING: powerlevel10k not installed"
fi


# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
