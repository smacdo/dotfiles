#!/usr/bin/env bash
#==============================================================================#
# Author: Scott MacDonald
# Purpose: Installs vscode with initial settings, extensions and color theme.
# Usage: ./install_vscode.sh
#==============================================================================#
# vim: set filetype=sh :
set -e
set -u

# shellcheck disable=SC3040
(set -o pipefail 2> /dev/null) && set -o pipefail 

# ==============================================================================
# CONFIGURATION — Edit these values to customize your install
# ==============================================================================

# Catppuccin flavor: latte | frappe | macchiato | mocha
CATPPUCCIN_FLAVOR="macchiato"

# Editor rulers (shown as vertical lines in the editor)
RULER_COLUMNS='[80, 100]'

# ==============================================================================
# EXTENSIONS — Add extension IDs here to install them automatically
# Format: "publisher.extension-name"
# ==============================================================================

EXTENSIONS=(
    "anthropic.claude-code"         # Claude Code AI assistant
    "vadimcn.vscode-lldb"           # CodeLLDB — native debugger (Rust, C, C++)
    "ms-azuretools.vscode-docker"   # Docker support
    "ms-python.python"              # Python language support
    "rust-lang.rust-analyzer"       # Rust language support
    "catppuccin.catppuccin-vsc"     # Catppuccin color theme

    # -- Add more extensions below this line -----------------------------------

)

# ==============================================================================
# HELPERS
# ==============================================================================

info()    { echo "[INFO]  $*"; }
success() { echo "[OK]    $*"; }
warn()    { echo "[WARN]  $*"; }
bail()    { echo "[ERROR] $*" >&2; exit 1; }

# ==============================================================================
# CHECKS
# ==============================================================================

check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        bail "This script must be run as root. Try: sudo $0"
    fi
    if [[ -z "${SUDO_USER:-}" ]]; then
        bail "SUDO_USER is not set. Run this script via sudo, not directly as root."
    fi
    success "Running as root (on behalf of $SUDO_USER)."
}

DISTRO_FAMILY=""

check_platform() {
    # Check for Linux
    if [[ "$(uname -s)" != "Linux" ]]; then
        bail "Unsupported OS: $(uname -s). This script only supports Linux."
    fi
    success "Platform is Linux."

    if [[ ! -f /etc/os-release ]]; then
        bail "Cannot determine Linux distribution (/etc/os-release not found)."
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    case "${ID:-}" in
        debian|ubuntu|linuxmint|pop)
            DISTRO_FAMILY="debian"
            success "Detected Debian-based distribution: ${PRETTY_NAME:-$ID}"
            ;;
        fedora|rhel|centos)
            DISTRO_FAMILY="rpm"
            success "Detected RPM-based distribution: ${PRETTY_NAME:-$ID}"
            ;;
        *)
            bail "Unsupported distribution: ${PRETTY_NAME:-$ID}. Supported: Debian/Ubuntu and Fedora/RHEL/CentOS."
            ;;
    esac
}

# ==============================================================================
# VSCODE INSTALLATION
# ==============================================================================

install_vscode() {
    if command -v code &>/dev/null; then
        success "VSCode is already installed ($(sudo -u "$SUDO_USER" code --version | head -1)). Skipping install."
        return
    fi

    case "$DISTRO_FAMILY" in
        debian) install_vscode_apt ;;
        rpm)    install_vscode_dnf ;;
        *)      bail "install_vscode: unsupported DISTRO_FAMILY=$DISTRO_FAMILY" ;;
    esac
}

install_vscode_apt() {
    info "Installing VSCode dependencies..."
    apt-get install -y wget gpg apt-transport-https

    local keyring_path="/usr/share/keyrings/microsoft-archive-keyring.gpg"

    if [[ ! -f "$keyring_path" ]]; then
        info "Adding Microsoft GPG key..."
        wget -qO- https://packages.microsoft.com/keys/microsoft.asc \
            | gpg --dearmor -o "$keyring_path"
        success "GPG key added."
    else
        success "Microsoft GPG key already present. Skipping."
    fi

    local sources_file="/etc/apt/sources.list.d/vscode.list"

    if [[ ! -f "$sources_file" ]]; then
        info "Adding Microsoft VSCode apt repository..."
        echo "deb [arch=amd64,arm64,armhf signed-by=${keyring_path}] https://packages.microsoft.com/repos/code stable main" \
            > "$sources_file"
        success "Repository added."
    else
        success "VSCode repository already configured. Skipping."
    fi

    info "Running apt-get update..."
    apt-get update -q

    info "Installing code..."
    apt-get install -y code
    success "VSCode installed successfully."
}

install_vscode_dnf() {
    info "Importing Microsoft GPG key..."
    rpm --import https://packages.microsoft.com/keys/microsoft.asc
    success "GPG key imported."

    local repo_file="/etc/yum.repos.d/vscode.repo"

    if [[ ! -f "$repo_file" ]]; then
        info "Adding Microsoft VSCode dnf repository..."
        cat > "$repo_file" <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
        success "Repository added."
    else
        success "VSCode repository already configured. Skipping."
    fi

    info "Refreshing dnf metadata..."
    dnf check-update || true  # check-update returns 100 when updates are available

    info "Installing code..."
    dnf install -y code
    success "VSCode installed successfully."
}

# ==============================================================================
# EXTENSION INSTALLATION
# ==============================================================================

install_extensions() {
    info "Installing VSCode extensions..."

    # code --list-extensions is run as the invoking user, not root
    local current_extensions
    current_extensions=$(sudo -u "$SUDO_USER" code --list-extensions 2>/dev/null || true)

    for ext in "${EXTENSIONS[@]}"; do
        # Strip inline comments (anything after whitespace + #)
        ext="${ext%%[[:space:]]*#*}"
        ext="${ext// /}"  # trim spaces

        [[ -z "$ext" ]] && continue

        if echo "$current_extensions" | grep -qi "^${ext}$"; then
            success "Extension already installed: $ext"
        else
            info "Installing extension: $ext"
            sudo -u "$SUDO_USER" code --install-extension "$ext" --force
        fi
    done
}

# ==============================================================================
# USER SETTINGS
# ==============================================================================

apply_settings() {
    local settings_dir
    settings_dir=$(eval echo "~$SUDO_USER/.config/Code/User")
    local settings_file="$settings_dir/settings.json"

    if [[ -f "$settings_file" ]]; then
        success "settings.json already exists — skipping to avoid overwriting your settings."
        info "  To apply defaults manually, see the settings block in this script."
        return
    fi

    info "Creating initial settings.json..."
    mkdir -p "$settings_dir"

    cat > "$settings_file" <<EOF
{
    "editor.rulers": ${RULER_COLUMNS},
    "workbench.colorTheme": "Catppuccin ${CATPPUCCIN_FLAVOR^}",
    "github.copilot.enable": { "*": false },
    "github.copilot.inlineSuggest.enable": false
}
EOF

    chown -R "$SUDO_USER":"$SUDO_USER" "$settings_dir"
    success "settings.json written to $settings_file"
}

# ==============================================================================
# MAIN
# ==============================================================================

main() {
    echo "=============================================="
    echo " VSCode Installer (Debian / RPM-based Linux)"
    echo "=============================================="
    echo ""

    check_root
    check_platform
    install_vscode
    install_extensions
    apply_settings

    echo ""
    echo "=============================================="
    success "All done!"
    echo "=============================================="
}

main "$@"
