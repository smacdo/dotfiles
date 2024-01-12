#!/bin/sh
USE_LOCAL_BREW=0

# TODO: Warn if running as root.

# Include local code libs.
. shell_profile/functions.sh
. sh/cli.sh

# packages include:
#  gnupg
#  fzf  htop  mosh neovim  vim

################################################################################
# Installs one or more homebrew packages for MacOS. Does nothing if the host
# operating system is not MacOS.
#
# Arguments:
#  $*: Name of homebrew package(s) to install.
################################################################################
install_pkg_mac() {
  # Only run this on MacOS platforms.
  # Assumes Homebrew is installed and available in $PATH.
  if is_osx; then
    print_action Installing packages: "$@"
    brew install "$@"
  fi
}

################################################################################
# Installs one or more Redhat packages. Does nothing if the host operating
# system is not Redhat.
#
# Arguments:
#  $*: Name of RedHat package(s) to install.
################################################################################
install_pkg_redhat() {
  # Only run this on Redhat platforms.
  if is_redhat; then
    print_action Installing packages: "$@"
    sudo dnf install "$@"
  fi
}

################################################################################
# Downloads and installs Homebrew if it is not already installed.
#
# Globals:
#  USE_LOCAL_BREW: Will tell Homebrew to use ~/homebrew if set to 1.
################################################################################
init_homebrew() {
  # Exit without init if homebrew is already installed.
  command -v brew >/dev/null 2>&1 && return 0

  # Install local homebrew, or system wide homebrew?
  if [ "$USE_LOCAL_BREW" -eq 1 ]; then
    # Local homebrew.
    print_action "Installing Homebrew (user local)"
    dir_to_return_to=$(pwd)
    mkdir "$HOME"/.homebrew && \
      cd "$HOME"/.homebrew && \
      curl -L https://github.com/Homebrew/brew/tarball/master | \
      tar xz --strip 1 -C "$HOME"/.homebrew &&
      cd "$dir_to_return_to" || exit 1
  else
    # System homebrew install.
    print_action "Installing Homebrew (global)"
    /bin/bash -c \
      "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
}

update_package_manager() {
  # TODO: Print message showing actions
  is_osx && init_homebrew
  is_redhat && sudo dnf update
}

################################################################################
# Clones a copy of the zsh powerlevel10k repository to `.dotfiles/.external`.
#
# Some distributions of Linux (like Redhat or Debian) lack a package for
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
    current_dir=$(pwd)
    cd "$p10kdir" ||  exit 1
    git pull
    cd "$current_dir" || exit 1
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
    zsh zsh-completions zsh-syntax-highlighting powerlevel10k

  install_pkg_redhat \
    bash bash-completion \
    zsh zsh-syntax-highlighting

  if is_redhat; then
    install_zsh_powerlevel
  fi

  # Common command line tools.
  # TODO: Move terminal-notifier to a desktop package.
  install_pkg_mac fzf git git-lfs htop neovim ripgrep terminal-notifier tmux vim wget \
    imagemagick
  install_pkg_redhat fzf git-lfs htop neovim ripgrep tmux vim vim-enhanced wget \
    imagemagick

  # GNU core utilities to simplify cross platform scripts.
  # (Should already be installed on Linux distros).
  install_pkg_mac coreutils findutils grep gnu-sed gawk

  # Install shellcheck to verify shell scripts are OK.
  install_pkg_mac shellcheck
  install_pkg_redhat ShellCheck

  # TODO: Install screenlocker on GUI systems.
  # cargo install screenlocker

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

  if is_redhat; then
    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
    sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'

    sudo dnf check-update
    sudo dnf install code
  fi
}

install_cpp() {
  install_pkg_mac make cmake llvm clang-format doxygen ninja
  install_pkg_redhat make automake gcc gcc-c++ doxygen ninja
}

################################################################################
# Change the default gnome settings to the way I like it.
################################################################################
apply_settings_gnome() {
  # Gnome window buttons.
  gsettings set org.gnome.desktop.wm.preferences button-layout ":minimize,maximize,close"
  # Gnome dark mode.
  gsettings set org.gnome.desktop.interface gtk-theme Adwaita-dark
  echo "Gnome settings applied!"
}

################################################################################
# Prints help information to stdout.
################################################################################
help() {
  echo "Multipurpose automated machine configuration tool"
  echo "https://github.com/smacdo/dotfiles"
  echo
  echo "Usage: $0 -hV [-p package_name]"
  echo " -h     Show this help message"
  echo " -H     Install homebrew locally (~/homebrew)"
  echo " -p x   Installs package [x], see section below for a list"
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

################################################################################
# Prints helpful instructions to the user after the tool has finished running.
################################################################################
finished() {
  echo "Finished! You should restart your shell before continuing."
  echo "  source ~/.bashrc   # bash shell"
  echo "  source ~/.zshrc    # zsh shell"
}

################################################################################
# Installs a cross platrform package.
#
# Arugments
#  $1: Name of the package to install.
################################################################################
install_package() {
  package="$1"

  update_package_manager
  install_build_tools

  if [ "$package" = "core" ]; then
    install_core_packages
  elif [ "$package" = "vscode" ]; then
    install_vscode
  else
    error "Unknown package '$package'"
    exit
  fi
}

################################################################################
# Configure a machine to build native binaries for C, C++, and Rust.
################################################################################
install_build_tools() {
  # Install C and C++ build tools for the platform.
  if is_osx; then
    # MacOS: Install XCode binaries via the command line.
    if [ ! -d "$('xcode-select' -print-path 2>/dev/null)" ]; then
      print_action "installing XCode binaries..."
      sudo xcode-select -switch /Library/Developer/CommandLineTools
    else
      # TODO: Verbose only
      echo "xcode binaries already installed"
    fi
  elif is_redhat; then
    # TODO: Query if installed
    install_pkg_redhat make automake gcc gcc-c++
  else
    error "install_build_tools lacks support for this platform"
    exit
  fi

  # Install Rust via rustup web script. This is officially maintained by the
  # Rust foundation so it should be safe to trust...
  # TODO: Can we silence the text about env var path not being set up?
  if is_osx || is_redhat; then
    if ! command -v rustup > /dev/null 2>&1 ; then
      print_action "installing rust..."
      curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
    else
      # TODO: Verbose only.
      echo "rust already installed"
    fi
  else
    error "install_rust support missing for this platform"
    exit
  fi
}

################################################################################
# Configure environment settings.
#
# Arguments
#  $1: Name of the desktop environment to configure.
################################################################################
apply_settings_for() {
  desktop="$1"

  if [ "$desktop" = "gnome" ]; then
    apply_settings_gnome
  else
    error "Unknown desktop '$desktop'"
  fi
}

################################################################################
# Configure local settings for dotfiles.
################################################################################
configure_local_configs() {
  # Configure local version control values.
  printf "Name for version control: "
  read -r VC_USERNAME

  printf "Email for version control: "
  read -r VC_EMAIL

  VC_EMAIL=$(printf "%s" "$VC_EMAIL" | sed 's/@/\\@/')

  # TODO: Confirm before applying.

  # Apply name and email settings to local version control configs.
  # TODO: Verify file exists first? Warn if not?
  perl -pi -e "s/^\s+name = .*$/  name = $VC_USERNAME/" ~/.my_gitconfig
  perl -pi -e "s/^\s+email = .*$/  email = $VC_EMAIL/" ~/.my_gitconfig
}

################################################################################
# Script main.
################################################################################
start() {
  while getopts "bhlHVp:s:" opt; do
    case "${opt}" in
      b)
        install_build_tools
        ;;
      h)
        # ${OPTARG}
        help
        exit
        ;;
      l)
        configure_local_configs
        ;;
      H)
        USE_LOCAL_BREW=1
        ;;
      V)
        set_verbose
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
        help 
        exit
        ;;
    esac
  done

  # Show usage and exit if no options were passed.
  if [ "$OPTIND" -eq 1 ]; then
    help
    exit
  fi

  shift $((OPTIND-1))

  finished
}

start "$@" ;

if [ -n "$VERBOSE" ]; then
  echo "Done!"
fi
