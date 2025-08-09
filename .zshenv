if [ -z ${S_DOTFILE_ROOT+x} ]; then
  export S_DOTFILE_ROOT="$HOME/.dotfiles"
fi

source ${S_DOTFILE_ROOT}/shell_profile/paths.sh
source ${S_DOTFILE_ROOT}/shell_profile/env.sh
