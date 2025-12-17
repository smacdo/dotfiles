#!/bin/sh
## Author: Scott MacDonald <root@smacdo.com>
## Created: 09/29/2020
## Purpose: Shell functions shared between bash/zsh/etc.

#------------------------------------------------------------------------------#
# Detect the operating system by checking for the existence of various files.  #
# Sadly there does not appear to be a way to uniformly check what operating    #
# system and distro we are running (especially without relying on the user to  #
# have pre-installed anything), so this my attempt at a workable solution.     #
#                                                                              #
# After running the following environment variables may be set:                #
#   DOT_OS:    linux, macos or unknown.                                        #
#   DOT_DIST:  debian, redhat, ubuntu, darwin (if DOT_OS = macos), or unknown. #
#   DOT_DIST_VERSION: major version/release number.                            #
#   DOT_DIST_REVISION: minor version/release number (only for macos).          #
#   DOT_WSL:   1 if WSL1 is detected, 2 if WSL2 is detected.                   #
#------------------------------------------------------------------------------#
detect_os() {
  UNAME=$(uname | tr "[:upper:]" "[:lower:]")

  if [ "$UNAME" = "linux" ]; then
      export DOT_OS="linux"

      # Use LSB to identify distribution if installed (it's not always installed
      # by default).
      if [ -f /etc/lsb-release ] || [ -d /etc/lsb-release.d ]; then
          DOT_DIST=$(lsb_release -i | cut -d: -f2 | sed s/'^\t'// | tr "[:upper:]" "[:lower:]")
          export DOT_DIST
          DOT_DIST_VERSION=$(lsb_release -r | cut -d: -f2 | sed s/'^\t'//)
          export DOT_DIST_VERSION
      elif uname -a | grep -q Ubuntu ; then
          export DOT_DIST="ubuntu"
      elif [ -f /etc/redhat-release ]; then
          export DOT_DIST="redhat"
      elif [ -f /etc/debian_version ]; then
          export DOT_DIST="debian"
          DOT_DIST_VERSION=$(cat /etc/debian_version)
          export DOT_DIST_VERSION
      else
          DOT_DIST=$(uname -s | tr "[:upper:]" "[:lower:]")
          export DOT_DIST
          DOT_DIST_VERSION=$(uname -r)
          export DOT_DIST_VERSION
      fi

      # Check if we are running in a WSL (Windows Subsystem for Linux) environment.
      KERNEL_RELEASE=$(uname -r)

      case "$KERNEL_RELEASE" in
          *microsoft-standard-WSL2*)
              DOT_WSL=2
              export DOT_WSL
              ;;
          *Microsoft*)
              DOT_WSL=1
              export DOT_WSL
              ;;
          *)
              ;;
      esac

  elif [ "$UNAME" = "darwin" ] ; then
      export DOT_OS="macos"
      export DOT_DIST="$UNAME"
      DOT_DIST_VERSION=$(sysctl kern.osrelease | cut -c 17- )
      export DOT_DIST_VERSION
      DOT_DIST_REVISION=$(sysctl kern.osrevision | cut -c 18- )
      export DOT_DIST_REVISION
  else
      # Could not detect the operating system or distro :(
      export DOT_OS="unknown"
      export DOT_DIST="unknown"
  fi

  case $(uname -m) in
  x86_64)
      export DOT_ARCH_BITS=64
      export DOT_ARCH=x86_64
      ;;
  i*86)
      export DOT_ARCH_BITS=32
      export DOT_ARCH=x86_32
      ;;
  arm64)
      export DOT_ARCH_BITS=64
      export DOT_ARCH=arm64
      ;;
  *)
      echo "WARN: Could not detect architecture via 'uname -m'!"
      export DOT_ARCH_BITS=0
      export DOT_ARCH=0
      ;;
  esac
}

# Run `detect_os` once at shell start to set the expected environment variables.
detect_os

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a MacOS environment, 1 otherwise.               #
#------------------------------------------------------------------------------#
is_osx() {
    [ "$DOT_OS" = "macos" ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a Linux environment, 1 otherwise.               #
#------------------------------------------------------------------------------#
is_linux() {
    [ "$DOT_OS" = "linux" ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a Redhat Linux environment, 1 otherwise.        #
#------------------------------------------------------------------------------#
is_redhat() {
    [ "$DOT_DIST" = "redhat" ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a Fedora Linux environment, 1 otherwise.        #
#------------------------------------------------------------------------------#
is_fedora() {
    [ "$DOT_DIST" = "fedora" ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a Redhat or Fedora environment, 1 otherwise.    #
#------------------------------------------------------------------------------#
is_dnf() {
    is_redhat || is_fedora || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in an Ubuntu Linux environment, 1 otherwise.       #
#------------------------------------------------------------------------------#
is_ubuntu() {
    [ "$DOT_DIST" = "ubuntu" ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a WSL1 environment, 1 otherwise.                #
#------------------------------------------------------------------------------#
is_wsl1() {
  [ "${DOT_WSL:-0}" = 1 ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a WSL2 environment, 1 otherwise.                #
#------------------------------------------------------------------------------#
is_wsl2() {
  [ "${DOT_WSL:-0}" = 2 ] || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a WSL1 or WSL2 environment, 1 otherwise.        #
#------------------------------------------------------------------------------#
is_wsl() {
  is_wsl1 || is_wsl2 || return 1
}

#------------------------------------------------------------------------------#
# Returns 0 if the shell is in a Windows Cygwin environment, 1 otherwise.      #
#------------------------------------------------------------------------------#
is_cygwin() {
    expr "$(uname -s)" : '^CYGWIN*' > /dev/null || return 1
}

#------------------------------------------------------------------------------#
# Print $PATH with one entry shown per line.                                   #
#------------------------------------------------------------------------------#
show_path() {
    echo "$PATH" | tr : '\n'
}

#------------------------------------------------------------------------------#
# Ask user to confirm before continuing. Returns 0 for yes, 1 for no.          #
# First parameter is the text to confirm with.                                 #
#------------------------------------------------------------------------------#
prompt_confirm() {
    while true; do
        printf "%s [y|n]: " "${1:-Continue?}"
        read -r REPLY
        case $REPLY in
            [yY]) echo ; return 0 ;;
            [nN]) echo ; return 1 ;;
            *) printf "\033[31m %s \n\033[0m" "Unrecognized response"
        esac
    done
}

#------------------------------------------------------------------------------#
# cd into directory and then ls it.                                            #
#------------------------------------------------------------------------------#
cdl() {
    dir="$1"
    dir="${dir:=$HOME}" # if dir empty then set to $HOME (emulate `cd `)
    if [ -d "$dir" ]; then
        cd "$dir" >/dev/null || return
        if is_osx ; then
            ls -G -lF
        else
            ls --color -lF
        fi
    else
        echo "cdl: $dir: Directory not found"
    fi
}

#------------------------------------------------------------------------------#
# cd to the dotfiles checkout.                                                 #
#------------------------------------------------------------------------------#
cdd() {
  if [ -z "$S_DOTFILE_ROOT" ]; then
    echo "\$S_DOTFILE_ROOT not defined" >&2
  else
    cd "$S_DOTFILE_ROOT" || return
  fi
}

#------------------------------------------------------------------------------#
# Create a directory and enter it.                                             #
#------------------------------------------------------------------------------#
mkd() {
    # NOTE: this was `cd "$_"` but `$_` is not supported in POSIX sh.
    mkdir -p "$@" && cd "$@" || return
}

#------------------------------------------------------------------------------#
# Create a directory in /tmp and enter it.                                     #
#                                                                              #
# The directory is pushed on to the dirs stack, so you can use `popd` to return#
# to the previous directory when you are done with the temp directory.         #
#------------------------------------------------------------------------------#
mktmp() {
    temp_dir="$(mktemp -d)"
    if type pushd >/dev/null ; then
      # shellcheck disable=SC3044
      pushd "$temp_dir" >/dev/null || return
    else
      cd "$temp_dir" || return
    fi
}

#------------------------------------------------------------------------------#
# One function to extract the contents of different archive formats.           #
# THIS WILL EXTRACT THE FILES INTO YOUR CURRENT DIRECTORY!                     #
#------------------------------------------------------------------------------#
extract() {
	if [ -z "$1" ]; then
		echo 'Usage: extract ARCHIVE'
		echo 'Extract files from ARCHIVE to the current directory'
	elif [ -r "$1" ]; then
		case "$1" in
			*.rar)      unrar x "$1"     ;;
			*.tar)      tar -xvf "$1"    ;;
			*.tar.bz2)  tar -xjvf "$1"   ;;
			*.bz2)      bzip2 -d "$1"    ;;
			*.tar.gz)   tar -xzvf "$1"   ;;
			*.gz)       gunzip -d "$1"   ;;
			*.tgz)      tar -xzvf "$1"   ;;
			*.Z)        uncompress "$1"  ;;
			*.zip)      unzip "$1"       ;;

			*) echo "ERROR: '$1' is not a known archive type"  ;;
		esac
	else
		echo "ERROR: '$1' is not a valid file"
	fi
}

#------------------------------------------------------------------------------#
# Recursively search for a file with the named pattern starting in the current #
# directory.                                                                   #
#------------------------------------------------------------------------------#
ff() {
	if [ -z "$1" ]; then
		echo 'Usage: ff PATTERN'
		echo 'Recursively search for a file named PATTERN in the current directory'
	else
		find . -type f -iname "$1"
	fi
}

#------------------------------------------------------------------------------#
# Change to the directory containing the given file path.                      #
#------------------------------------------------------------------------------#
cdf() {
	if [ -z "$1" ]; then
		echo 'Usage: cdf PATTERN'
		echo 'cd into the directory basepath of the given file'
	else
        cd "$(dirname "$1")" || return
	fi
}

#------------------------------------------------------------------------------#
# Show autodetected OS info                                                    #
#------------------------------------------------------------------------------#
osinfo() {
  echo "DOT_OS          : $DOT_OS"
  echo "DOT_DIST        : $DOT_DIST"
  echo "DOT_DIST_VERSION: $DOT_DIST_VERSION"
}

#------------------------------------------------------------------------------#
# Fuzzy search current processes and kill selected entries.                    #
#------------------------------------------------------------------------------#
fkill() {
  if is_osx; then
    # macOS uses BSD ps with different flags
    if [ "$(id -u)" != "0" ]; then
      pid=$(ps -u "$(id -u)" -o pid,command | sed 1d | fzf -m | awk '{print $1}')
    else
      pid=$(ps -e -o pid,command | sed 1d | fzf -m | awk '{print $1}')
    fi
  else
    # Linux uses GNU ps
    if [ "$(id -u)" != "0" ]; then
      pid=$(ps -fH -u "$(id -u)" --sort -pid | sed 1d | fzf -m | awk '{print $2}')
    else
      pid=$(ps -efH --sort -pid | sed 1d | fzf -m | awk '{print $2}')
    fi
  fi

  if [ -n "$pid" ]; then
    echo "$pid" | xargs kill -"${1:-9}"
  fi
}

#------------------------------------------------------------------------------#
# Colored man pages.                                                           #
#------------------------------------------------------------------------------#
man() {
  # mb: Begin bold; use bold + green fg.
  # md: Begin blink: use bold + teal fg.
  # me: End bold/blink: Reset.
  # so: Begin reverse video: yellow on blue.
  # se: End reverse video: End standout, reset fg bg color.
  # us: Start underline, with white fg.
  # ue: End underline, reset formatting.

  env \
    LESS_TERMCAP_mb="$(tput bold; tput setaf 2)"               \
    LESS_TERMCAP_md="$(tput bold; tput setaf 6)"               \
    LESS_TERMCAP_me="$(tput sgr0)"                             \
    LESS_TERMCAP_so="$(tput smso; tput setaf 3; tput setab 4)" \
    LESS_TERMCAP_se="$(tput rmso; tput sgr0)"                  \
    LESS_TERMCAP_us="$(tput smul; tput setaf 5)"               \
    LESS_TERMCAP_ue="$(tput rmul; tput sgr0)"                  \
    GROFF_NO_SGR=1                                             \
    man "$@"
}
