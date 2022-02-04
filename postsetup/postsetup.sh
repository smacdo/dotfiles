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
    zsh-syntax-highlighting \
    romkatv/powerlevel10k/powerlevel10k

  # Common command line tools.
  install_pkg_mac fzf git git-lfs htop neovim ripgrep terminal-notifier tmux \
    vim wget

  # TODO: Only run if exists. Run once?
  # TODO: Support system install variant.
  if [ -f "$(brew --prefix)/opt/fzf/install" ]; then
    "$(brew --prefix)"/opt/fzf/install

    # Add fzf config to local vimrc.
    vimrc_fzf_line="set rtp+=$(brew --prefix)/opt/fzf"
    grep -qxF "$vimrc_fzf_line" ~/.my_vimrc || echo "$vimrc_fzf_line" >> ~/.my_vimrc
  else
    error "implement fzf post init for system wide homebrew install"
  fi

  # ZSH completions post-install config:
  chmod -R go-w "$(brew --prefix)"/share/zsh

  # GNU core utilities to simplify cross platform scripts.
  install_pkg_mac coreutils findutils grep gnu-sed gawk
}

install_cpp_clang() {
  install_pkg_mac make cmake llvm clang-format
}

install_shell_scripting() {
  install_pkg_mac shellcheck
}

help() {
  echo "--- help ---"
}

finished() {
  echo "Finished! You should restart your shell before continuing."
  echo "  source ~/.bashrc   # bash shell"
  echo "  source ~/.zshrc    # zsh shell"
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
  finished

  # TODO
  # if no options selected print usage
}

start "$@" ;

if [ -n "$VERBOSE" ]; then
  echo "Done!"
fi
