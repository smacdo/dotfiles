# Set terminal title bar.
function set_titlebar() {
  echo -n $'\e]0;'"$*"$'\a'
}

# Returns 0 if OS is OSX otherwise returns 1.
function is_osx() {
    [[ "$OSTYPE"] =~ ^darwin ]] || return 1
}

# Returns 1 if OS is Fedora otherwise returns 1.
function is_fedora {
    [[ -f "/etc/os-release" ]] || return 1
    [[ "$(cat /etc/os-release | grep "^ID=" | cut -d'=' -f2)" =~ fedora ]] || return 1
}

# Returns 1 if OS is Unbutu otherwise returns 1.
function is_ubuntu() {
    [[ "$(cat /etc/issue 2> /dev/null)" =~ Ubuntu ]] || return 1
}

# Reeturns 1 if OS is Ubuntu desktop edition, otherwise returns 1.
function is_ubuntu_desktop() {
    dpkg -l ubuntu-desktop >/dev/null 2>&1 || return 1
}
