if is_osx; then
    alias ls='ls -G'
else
    alias ls='ls --color'
fi

alias ll='ls -lh'
alias la='ls -la'

alias -g ...='../..'
alias -g ....='../../..'
alias -g .....='../../../..'

alias filesize="stat -f '%z bytes'"

alias df="df -h"
alias diskfree="df -h"
alias grep='grep --color=auto'
alias diff='git diff'

alias myip="dig +short myip.opendns.com @resolver1.opendns.com"
