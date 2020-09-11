#TODO: Fix for mac not supported
#alias ls='ls --color'
alias ll='ls -lh'
alias la='ls -la'

alias -g ...='../..'
alias -g ....='../../..'
alias -g .....='../../../..'

alias grep='grep --color=auto'
alias diff='git diff'

# webcat
[[ -x $(which wget) ]] && alias wcat='wget -q -O - '
