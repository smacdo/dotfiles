#!/bin/sh


# packages include:
#  gnupg
#  fzf  htop  mosh neovim  vim

print_action() {
  echo "$@"
}

error() {
  echo "ERROR: $@"
}

verbose() {
  if [ -n "$VERBOSE" ]; then
    echo "$@"
  fi
}

install_pkg_mac() {
  print_action Installing packages: "$@"
  "$HOME"/homebrew/bin/brew install "$@"
}

init_homebrew() {
  # TODO: Only do this if corp machine, or maybe by option?
  if [ ! -d "$HOME/homebrew" ] ; then
    print_action Installing Homebrew
    mkdir "$HOME"/homebrew && \
      curl -L https://github.com/Homebrew/brew/tarball/master | \
      tar xz --strip 1 -C "$HOME"/homebrew
  else
    verbose Homebrew already installed, skipping installation
  fi

  # TODO: Make this permanent
  export PATH=${HOME}/homebrew/bin:${PATH}
}

install_terminal_core() {
  # Bash and ZSH shells.
  install_pkg_mac bash bash-completion zsh zsh-completions \
    zsh-syntax-highlighting

  # Common command line tools.
  install_pkg_mac fzf git git-lfs htop neovim ripgrep terminal-notifier tmux \
    vim wget

  # TODO: Only run if exists. Run once?
  # TODO: Support system install variant.
  if [ -d "$HOME/homebrew" ]; then
    "$HOME"/homebrew/opt/fzf/install
    # TODO: Only run this if the line does not already exist in .vimrc.
    echo "set rtp+=$HOME/homebrew/opt/fzf" >> ~/.my_vimrc
  else
    error "implement fzf post init for system wide homebrew install"
  fi

  # ZSH completions post-install config:
  rm -f "$HOME"/.zcompdump; compinit
  chmod -R go-w "$HOME"/homebrew/share/zsh

  # GNU core utilities to simplify cross platform scripts.
  install_pkg_mac coreutils findutils grep gnu-sed gawk

  # TODO in bash this is hash -r and in zsh it is rehash
  # TODO move this to the core loop since it has to run more often
  rehash

}

install_cpp_clang() {
  install_pkg_mac make cmake
}

install_shell_scripting() {
  install_pkg_mac shellcheck
}

help() {
  echo "--- help ---"
}

usage() {
  echo "Configure and install packages on a machine to fit a given profile"
  echo "Usage: $0 -hV"
  echo " -h     Show this help message"
  echo " -V     Verbose mode"
}

start() {
  while getopts ":h:V" opt; do
    case "${opt}" in
      h)
        # ${OPTARG}
        help
        ;;
      V)
        VERBOSE=1
        ;;
      *)
        usage
        ;;
    esac
  done

  shift $((OPTIND-1))

  init_homebrew
  install_terminal_core

  # TODO
  # if no options selected print usage
}

start "$@" ;

if [ -n "$VERBOSE" ]; then
  echo "Done!"
fi
