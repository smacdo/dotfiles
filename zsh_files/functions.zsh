# Shared function should go in .dotfiles/.functions. ZSH specific functions go here.

################################################################################
# A variation on ZSH's default "kill-word" command that treats path separator
# '/' as a word boundary.
# Ref: https://unix.stackexchange.com/a/319854
################################################################################
backward-kill-dir () {
    local WORDCHARS=${WORDCHARS/\/}
    zle backward-kill-word
    zle -f kill
}

# Bind the nicer kill word command to ALT + BACKSPACE.
zle -N backward-kill-dir
bindkey '^[^?' backward-kill-dir
