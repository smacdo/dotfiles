# Author: Scott MacDonald <scott@smacdo.com>
#
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Export the dotfiles path as an environment variable to avoid hardcoding
# paths.
# TODO: zshenv
export S_DOTFILE_ROOT="$HOME/.dotfiles"

#==============================================================================
# Source shell vendor neutral configuration files. These files are shared
# between the different shells like bash, and zsh to reduce duplication.
#
# If you want to have machine specific stuff the best place to put it is in
# ~/.my_shell_profile.sh or ~/.my_zshrc
for file in "${S_DOTFILE_ROOT}"/shell_profile/\
{xdg.sh,paths.sh,exports.sh,functions.sh,aliases.sh,private_branch.sh}; do
    # -r test if FILE exists and is readable.
    # -f test if FILE exists and is a file.
    [ -r "$file" ] && [ -f "$file" ] && source "$file"
done;
unset file

# Load .dotfiles shared zsh modules.
for file in ~/.zsh/*.zsh; do
    . "$file"
done
unset file

#==============================================================================
# Make sure we can store a decent amount of history lines
HISTSIZE=20000
SAVEHIST=20000
HISTFILE=~/.local/state/zsh_history

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
elif [[ -f /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source /usr/local/opt/powerlevel10k/powerlevel10k.zsh-theme
elif [[ -f "$S_DOTFILE_ROOT"/.external/powerlevel10k/powerlevel10k.zsh-theme ]]; then
    source "$S_DOTFILE_ROOT"/.external/powerlevel10k/powerlevel10k.zsh-theme
else
    echo "WARNING: powerlevel10k not installed"
fi

# Load powerlevel10k, a ZSH plugin for making fancy prompts.
# To customize run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Load iTerm2 shell integration script.
if [ "${TERM_PROGRAM}" = "iTerm.app" ]; then
    source "${S_DOTFILE_ROOT}/vendor/iterm2/zsh"
fi

# Additional ZSH completions.
if is_osx; then
  if type brew &>/dev/null; then
    FPATH=$(brew --prefix)/share/zsh-completions:$FPATH
    autoload -Uz compinit
  fi
fi

# Load fzf support.
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

# Finish zsh auto completion init.
compinit

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

# Load any optional per-machine config profiles at the end to allow them to 
# override this default config profile.
[ -r "${HOME}/.my_shell_profile.sh" ] && [ -f "${HOME}/.my_shell_profile.sh" ]\
&& source "${HOME}/.my_shell_profile.sh"

[ -r "${HOME}/.my_zshrc.sh" ] && [ -f "${HOME}/.my_zshrc.sh" ]\
&& source "${HOME}/.my_zshrc.sh"

