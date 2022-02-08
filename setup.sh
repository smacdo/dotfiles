#!/bin/sh
USE_LOCAL_BREW=0

# TODO: Check for superuser privs (at least on fedora)

# Include local code libs.
. shell_profile/functions.sh

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
  # Only run this on MacOS platforms.
  if is_osx; then
    print_action Installing packages: "$@"
    "$HOME"/homebrew/bin/brew install "$@"
  fi
}

install_pkg_fedora() {
  # Only run this on Fedora platforms.
  if is_fedora; then
    print_action Installing packages: "$@"
    dnf install "$@"
  fi
}

init_homebrew() {
  # Exit without init if homebrew is already installed.
  command -v brew >/dev/null 2>&1 ] && return 0

  # Install local homebrew, or system wide homebrew?
  if [ "$USE_LOCAL_BREW" -eq 1 ]; then
    # Local homebrew.
    print_action "Installing Homebrew (user local)"
    mkdir "$HOME"/homebrew && \
      curl -L https://github.com/Homebrew/brew/tarball/master | \
      tar xz --strip 1 -C "$HOME"/homebrew
  else
    # System homebrew install.
    print_action "Installing Homebrew (global)"
    /bin/bash -c \
      "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  # TODO: Needed?
  # export PATH=${HOME}/homebrew/bin:${PATH}
}

install_zsh_powerlevel() {
  # Don't proceed without a path to the dotfiles checkout.
  if [ -z "$S_DOTFILE_ROOT" ]; then
    error "Expected environment variable `S_DOTFILE_ROOT` not set"
    return 1
  fi

  # Install via git clone.
  # TODO: Should this be locked to a release tag?
  p10kdir="$S_DOTFILE_ROOT"/.external/powerlevel10k
  
  if [ -d "$p10kdir" ]; then
    # Already installed, pull any updates.
    echo "Powerlevel10k installed - will pull updates"
    current_dir=`pwd`
    cd "$p10kdir"
    git pull
    cd "$current_dir"
  else 
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$p10kdir"
  fi
}

install_core_packages() {
  # Bash and ZSH shells with additional plugins.
  install_pkg_mac \
    bash bash-completion \
    zsh zsh-completions zsh-syntax-highlighting romkatv/powerlevel10k/powerlevel10k

  install_pkg_fedora \
    bash bash-completion \
    zsh zsh-syntax-highlighting

  if is_fedora; then
    install_zsh_powerlevel
  fi

  # Common command line tools.
  install_pkg_mac fzf git git-lfs htop neovim ripgrep terminal-notifier tmux vim wget

  # GNU core utilities to simplify cross platform scripts.
  install_pkg_mac coreutils findutils grep gnu-sed gawk

    # Post install configuration for MacOS.
  if is_osx; then
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
  fi

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
  echo "Usage: $0 -hV [-t package_name]"
  echo " -h     Show this help message"
  echo " -H     Install homebrew locally (~/homebrew)"
  echo " -V     Verbose mode"
  echo
  echo "Available packages: "
  echo "  core      Core terminal utiliies for every machine"
}

install_package() {
  package="$1"

  # TODO: Only init if mac.
  is_osx && init_homebrew

  if [ "$package" == "core" ]; then
    install_core_packages
  else
    error "Unknown package '$package'"
    exit
  fi
}

start() {
  while getopts "hHVp:" opt; do
    case "${opt}" in
      h)
        # ${OPTARG}
        help
        exit
        ;;
      H)
        USE_LOCAL_BREW=1
        ;;
      V)
        VERBOSE=1
        ;;
      p)
        install_package "${OPTARG}"
        ;;
      *)
        error "Unknown option"
        echo
        usage
        exit
        ;;
    esac
  done

  shift $((OPTIND-1))

  finished

  # TODO
  # if no options selected print usage
}

start "$@" ;

if [ -n "$VERBOSE" ]; then
  echo "Done!"
fi
