#!/bin/sh
#==============================================================================#
# Author: Scott MacDonald
# Purpose: 
# Usage: ./install_nerd_fonts
#==============================================================================#
# vim: set filetype=sh :
set -e
set -u

# shellcheck disable=SC3040
(set -o pipefail 2> /dev/null) && set -o pipefail 

FONT_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/JetBrainsMono.zip"
FONT_DIR="$HOME/.local/share/fonts/JetBrainsMono"
TMP_ZIP="/tmp/JetBrainsMono.zip"

echo "Downloading JetBrainsMono Nerd Font..."
curl -Lo "$TMP_ZIP" "$FONT_URL"

echo "Installing fonts to $FONT_DIR..."
mkdir -p "$FONT_DIR"
unzip -o "$TMP_ZIP" "*.ttf" -d "$FONT_DIR"

echo "Cleaning up..."
rm "$TMP_ZIP"

echo "Refreshing font cache..."
fc-cache -fv "$FONT_DIR"

echo "Done! JetBrainsMono Nerd Font installed."
