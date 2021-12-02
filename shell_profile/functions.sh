##!/bin/sh
## Author: Scott MacDonald <scott@smacdo.com
## Created: 09/29/2020 
## Purpose: Shell functions shared between bash/zsh/etc.

### Operating system check functions.
# Detect the operating system by checking for the existence of various files.
# Sadly there does not appear to be a way to uniformly check what operating
# system and distro we are running (especially without relying on the user to
# have pre-installed anything), so this my attempt at a workable solution.
UNAME=$(uname | tr "[:upper:]" "[:lower:]")

if [[ "$UNAME" == "linux" ]]; then
    export DOT_OS="linux"

    # Use LSB to identify distribution if installed (it's not always installed
    # by default).
    if [ -f /etc/lsb-release -o -d /etc/lsb-release.d ]; then
        export DOT_DIST=$(lsb_release -i | cut -d: -f2 | sed s/'^\t'// | tr "[:upper:]" "[:lower:]")
        export DOT_DIST_VERSION=$(lsb_release -r | cut -d: -f2 | sed s/'^\t'//) 
    elif [ -n "$(uname -a | grep Ubuntu)" ]; then
        export DOT_DIST="ubuntu"
    elif [ -f /etc/redhat-release ]; then
        export DOT_DIST="redhat"
    elif [ -f /etc/debian_version ]; then
        export DOT_DIST="debian"
        export DOT_DIST_VERSION=$(cat /etc/debian_version)
    else
        export DOT_DIST=$(uname -s | tr "[:upper:]" "[:lower:]")
        export DOT_DIST_VERSION=$(uname -r)
    fi
elif [[ "$UNAME" == "darwin" ]] ; then
    export DOT_OS="macos"
    export DOT_DIST=$UNAME
    export DOT_DIST_VERSION=$(sysctl kern.osrelease | cut -c 17- )
    export DOT_DIST_REVISION=$(sysctl kern.osrevision | cut -c 18- )
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
*)
    echo "WARN: Could not detect architecture via 'uname -m'!"
    export DOT_ARCH_BITS=0
    export DOT_ARCH=0
    ;;
esac

is_osx() {
    [[ "$DOT_OS" == "macos" ]] || return 1
}

is_linux() {
    [[ "$DOT_OS" == "linux" ]] || return 1
}

is_redhat() {
    [[ "$DOT_DIST" == "redhat" ]] || return 1
}

is_ubuntu() {
    [[ "$DOT_DIST" == "ubuntu" ]] || return 1
}

is_cygwin() {
    # TODO: Move platform detection to above code block.
    [[ $(uname -s) =~ ^CYGWIN* ]] || return 1
}

# Ask user to confirm before continuing. Returns 0 for yes, 1 for no.
# First parameter is the text to confirm with.
prompt_confirm() {
    while true; do
        read -r -n 1 -p "${1:-Continue?} [y|n]: " REPLY
        case $REPLY in
            [yY]) echo ; return 0 ;;
            [nN]) echo ; return 1 ;;
            *) printf "\033[31m %s \n\033[0m" "Unrecognized response"
        esac
    done
}

# Ensure software packages are up to date.
update_packages() {
    if [[ is_ubuntu ]]; then
        sudo apt update
    elif [[ is_redhat ]]; then
        sudo dnf check-update
    elif [[ is_osx ]]; then
        echo "TODO: Implement me"
        return 1
    else
        echo "ERROR: Unsupported os/dist"
        return 1
    fi
}

# Update software packages and upgrade to latest version.
upgrade_packages() {
    prompt_confirm "Upgrade all installed packages to latest version?"
    update_packages || return 1

    if [[ is_ubuntu ]]; then
        sudo apt upgrade
    elif [[ is_redhat ]]; then
        sudo dnf update
    elif [[ is_osx ]]; then
        echo "TODO: Implement me"
        return 1
    else
        echo "ERROR: Unsupported os/dist"
        return 1
    fi
}

# Set the terminal title bar (if the terminal emulator supports it).
set_titlebar() {
    echo $'\033]0;'$*$'\007'
}

# Cd into directory and then ls it.
cdl() {
    local dir="$1"
    local dir="${dir:=$HOME}" # if dir empty then set to $HOME (emulate `cd `)
    if [[ -d "$dir" ]]; then
        cd "$dir" >/dev/null
        if is_osx ; then
            ls -G -lF
        else
            ls --color -lF
        fi
    else
        echo "cdl: $dir: Directory not found"
    fi
}

################################################################################
# cd to the dotfiles checkout.
################################################################################
cdd() {
  if [ -z "$S_DOTFILE_ROOT" ]; then
    echo '$S_DOTFILE_ROOT not defined' >&2
  else
    cd "$S_DOTFILE_ROOT"
  fi
}

# Create a directory and enter it.
mkd() {
    mkdir -p "$@" && cd "$_" || return
}

# Create a directory in /tmp and enter it.
mkdtmp() {
    cd "$(mktemp -d)" || return
}

# ssh and start a screen session on the remote server
sshs() {
	if [[ -z $* ]]; then
		echo 'Usage: sshs [options] [user@]hostname'
		echo 'SSH and automatically start a GNU screen session on the remote server'
	else
		ssh -t "$@" screen -DRU
	fi
}

# One function to extract the contents of different archive formats.
# THIS WILL EXTRACT THE FILES INTO YOUR CURRENT DIRECTORY!
extract() {
	if [[ -z $1 ]]; then
		echo 'Usage: extract ARCHIVE'
		echo 'Extract files from ARCHIVE to the current directory'
	elif [[ -r $1 ]]; then
		case $1 in
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

# Recursively search for a file with the named pattern starting in the current directory.
ff() {
	if [[ -z $1 ]]; then
		echo 'Usage: ff PATTERN'
		echo 'Recursively search for a file named PATTERN in the current directory'
	else
		find . -type f -iname "$1"
	fi
}

# Change to the directory containing the given file path.
cdf() {
	if [ -z "$1" ]; then
		echo 'Usage: cdf PATTERN'
		echo 'cd into the directory basepath of the given file'
	else
        cd "$(dirname "$1")" || return
	fi
}

# Reload/start shell
reload() {
    exec "${SHELL}" "$@"
}

################################################################################
# Show autodetected OS info
################################################################################
osinfo() {
  echo "DOT_OS          : $DOT_OS"
  echo "DOT_DIST        : $DOT_DIST"
  echo "DOT_DIST_VERSION: $DOT_DIST_VERSION"
}

################################################################################
# Fuzzy search current processes and kill selected entries.
################################################################################
fkill() {
  if [ "$UID" != "0" ]; then
    pid=$(ps -fH -u "$UID" --sort -pid | sed 1d | fzf -m | awk '{print $2}')
  else
    pid=$(ps -efH --sort -pid | sed 1d | fzf -m | awk '{print $2}')
  fi

  if [ -n "$pid" ]; then
    echo "$pid" | xargs kill -"${1:-9}"
  fi
}

