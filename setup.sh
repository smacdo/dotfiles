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

################################################################################
# Clones a copy of the zsh powerlevel10k repository to `.dotfiles/.external`.
#
# Some distributions of Linux (like Fedora or Debian) lack a package for
# powerlevel10k so we need to manually install it. Othertimes it makes sense to
# package up the .dotfiles directory to copy it to a server that doesn't have
# access to the full internet. In all of those cases it makes sense to install
# powerlevel10k locally.
################################################################################
install_zsh_powerlevel() {
  # Don't proceed without a path to the dotfiles checkout.
  if [ -z "$S_DOTFILE_ROOT" ]; then
    error "Expected environment variable S_DOTFILE_ROOT not set"
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

################################################################################
# Installs basic packages required for all environments including desktops and
# servers.
# 
# Most of the scripts in bin/ as well as vim, tmux configuration expect this
# core set of packages to be installed.
################################################################################
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
  # TODO: Move terminal-notifier to a desktop package.
  install_pkg_mac fzf git git-lfs htop neovim ripgrep terminal-notifier tmux vim wget
  install_pkg_fedora fzf git-lfs htop neovim ripgrep tmux vim vim-enhanced wget

  # GNU core utilities to simplify cross platform scripts.
  # (Should already be installed on Linux distros).
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

################################################################################
# Installs the Visual Studio code program on the local computer.
# Use `code` to invoke it from the command line.
################################################################################
install_vscode() {
  ## Visual Studio Code
  # Ref: https://code.visualstudio.com/docs/setup/linux#_rhel-fedora-and-centos-based-distributions
  print_action "Install Visual Studio Code"

  if is_fedora; then
    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
    sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'

    dnf check-update
    sudo dnf install code
  fi
}

install_cpp() {
  install_pkg_mac make cmake llvm clang-format
  install_pkg_fedora make automake gcc gcc-c++
}

################################################################################
# Change the default gnome settings to the way I like it.
################################################################################
apply_settings_gnome() {
  gsettings set org.gnome.desktop.wm.preferences button-layout ":minimize,maximize,close"
  echo "Gnome settings applied!"
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
  echo " -s x   Apply settings for [x] desktop"
  echo " -V     Verbose mode"
  echo
  echo "Available desktops: "
  echo "  gnome"
  echo
  echo "Available packages: "
  echo "  core      Core terminal utiliies for every machine"
  echo "  vscode"
}

install_package() {
  package="$1"

  is_osx && init_homebrew
  is_fedora && dnf update

  if [ "$package" == "core" ]; then
    install_core_packages
  elif [ "$package" == "vscode" ]; then
    install_vscode
  else
    error "Unknown package '$package'"
    exit
  fi
}

apply_settings_for() {
  desktop="$1"

  if [ "$desktop" = "gnome" ]; then
    apply_settings_gnome
  else
    error "Unknown desktop '$desktop'"
  fi
}

start() {
  while getopts "hHVp:s:" opt; do
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
      s)
        apply_settings_for "${OPTARG}"
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
