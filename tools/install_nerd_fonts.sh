#!/bin/sh
#==============================================================================#
# Author: Scott MacDonald
# Purpose: Install JetBrainsMono Nerd Font for the current user.
# Usage: ./tools/install_nerd_fonts.sh
#==============================================================================#
# vim: set filetype=sh :
set -eu

# shellcheck disable=SC3040
(set -o pipefail 2>/dev/null) && set -o pipefail

FONT_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/JetBrainsMono.zip"
FONT_NAME="JetBrainsMono"
OS_NAME=$(uname -s)

case "$OS_NAME" in
  Darwin)
    FONT_DIR="$HOME/Library/Fonts"
    ;;
  Linux)
    case "$(uname -r)" in
      *[Mm]icrosoft*)
        echo "Install the font in Windows so the terminal hosting WSL can use it." >&2
        exit 1
        ;;
    esac
    FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/$FONT_NAME"
    ;;
  *)
    echo "Unsupported operating system: $OS_NAME" >&2
    exit 1
    ;;
esac

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 is required to install Nerd Fonts." >&2
    exit 1
  fi
}

require_command curl
require_command unzip
if [ "$OS_NAME" = "Linux" ]; then
  require_command fc-cache
fi

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/install-nerd-fonts.XXXXXX")
TMP_ZIP="$TMP_DIR/$FONT_NAME.zip"
trap 'rm -rf "${TMP_DIR:?}"' EXIT
trap 'exit 1' HUP INT TERM

echo "Downloading JetBrainsMono Nerd Font..."
curl -fL --retry 3 -o "$TMP_ZIP" "$FONT_URL"

echo "Installing fonts to $FONT_DIR..."
mkdir -p "$FONT_DIR"
unzip -jo "$TMP_ZIP" "*.ttf" -d "$FONT_DIR"

if [ "$OS_NAME" = "Linux" ]; then
  echo "Refreshing font cache..."
  fc-cache -f "$FONT_DIR"
elif [ -d "$HOME/.local/share/fonts/$FONT_NAME" ]; then
  echo "The previous macOS install at ~/.local/share/fonts/$FONT_NAME is unused and safe to remove." >&2
fi

echo "Done. Select 'JetBrainsMono Nerd Font' in your terminal settings."
