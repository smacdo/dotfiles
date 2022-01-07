#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Configure MacOS to my liking.
#===============================================================================
# Dotfile inspirations came from the following:
# https://github.com/mathiasbynens/dotfiles
#
# TODO
#  Tell VSCode to use iTerm2 as default terminal
#  https://stackoverflow.com/a/51409237
#===============================================================================

# Don't continue if the S_DOTFILE_ROOT env variable is not present which
# indicates the dotfiles setup is probably busted.
if [ -z "$S_DOTFILE_ROOT" ]; then
  echo "$$S_DOTFILE_ROOT is not set - you need to run setup and restart your shell"
  exit 1
fi

# Pull in shared functions.
. "$S_DOTFILE_ROOT"/shell_profile/functions.sh

# Only run on MacOS systems.
if ! is_osx; then
  echo "This script only works for MacOS machines"
  exit 1
fi

# Close any open System preference windows to prevent them from overriding any
# settings this script touches.
osascript -e 'tell application "System Preferences" to quit'

# Ask for the superuser password at the start.
sudo -v

# Keep-alive: update existing sudo time stamp if set, otherwise do nothing.
# Ref: https://gist.github.com/cowboy/3118588
while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

################################################################################
# Install fonts
################################################################################
# This install fonts for the current user. If you would rather install them for
# the entire system then change to /Library/Fonts.
# 
# Do not overwrite any existing fonts if they already exist in target.
echo "Installing fonts..."

cp -n "$S_DOTFILE_ROOT"/fonts/consola/* ~/Library/Fonts
cp -n "$S_DOTFILE_ROOT"/fonts/hack/* ~/Library/Fonts
cp -n "$S_DOTFILE_ROOT"/fonts/jetbrains/* ~/Library/Fonts

################################################################################
# System settings
###############################################################################
echo "Applying system settings..."

# Enable dark mode.
osascript -e 'tell application "System Events"
  tell appearance preferences
    set dark mode to true
  end tell
end tell'

# Always show scrollbars
defaults write NSGlobalDomain AppleShowScrollBars -string "Always"

# Always show the menu bar.
defaults write NSGlobalDomain _HIHideMenuBar -bool false

# Adjust toolbar title rollover delay.
# (This is where you have to hover your cursor over the folder icon for a split
#  second in the file dialog before being able to edit the path).
defaults write NSGlobalDomain NSToolbarTitleViewRolloverDelay -float 0

# Increase window resize speed for Cocoa applications
defaults write NSGlobalDomain NSWindowResizeTime -float 0.001

# Expand save panel by default
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode2 -bool true

# Expand print panel by default
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint -bool true
defaults write NSGlobalDomain PMPrintingExpandedStateForPrint2 -bool true

# Save to disk (not to iCloud) by default
defaults write NSGlobalDomain NSDocumentSaveNewDocumentsToCloud -bool false

# Automatically quit printer app once the print jobs complete
defaults write com.apple.print.PrintingPrefs "Quit When Finished" -bool true

# Display ASCII control characters using caret notation in standard text views
# Try e.g. `cd /tmp; unidecode "\x{0000}" > cc.txt; open -e cc.txt`
defaults write NSGlobalDomain NSTextShowsControlCharacters -bool true

# Disable automatic termination of inactive apps
defaults write NSGlobalDomain NSDisableAutomaticTermination -bool true

# Reveal IP address, hostname, OS version, etc. when clicking the clock
# in the login window
sudo defaults write /Library/Preferences/com.apple.loginwindow AdminHostInfo HostName

# Trackpad: map bottom right corner to right-click
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad TrackpadCornerSecondaryClick -int 2
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad TrackpadRightClick -bool true
defaults -currentHost write NSGlobalDomain com.apple.trackpad.trackpadCornerClickBehavior -int 1
defaults -currentHost write NSGlobalDomain com.apple.trackpad.enableSecondaryClick -bool true

# Save screenshots to the desktop
defaults write com.apple.screencapture location -string "${HOME}/Desktop"

# Save screenshots in PNG format (other options: BMP, GIF, JPG, PDF, TIFF)
defaults write com.apple.screencapture type -string "png"

# Disable shadow in screenshots
defaults write com.apple.screencapture disable-shadow -bool true

# Enable subpixel font rendering on non-Apple LCDs
# Reference: https://github.com/kevinSuttle/macOS-Defaults/issues/17#issuecomment-266633501
defaults write NSGlobalDomain AppleFontSmoothing -int 1

# Enable HiDPI display modes (requires restart)
sudo defaults write /Library/Preferences/com.apple.windowserver DisplayResolutionEnabled -bool true

# Finder: disable window animations and Get Info animations
defaults write com.apple.finder DisableAllAnimations -bool true

# Set home as the default location for new Finder windows
defaults write com.apple.finder NewWindowTarget -string "PfLo"
defaults write com.apple.finder NewWindowTargetPath -string "file://${HOME}"

# Finder: show all filename extensions
defaults write NSGlobalDomain AppleShowAllExtensions -bool true

# Finder: show status bar
defaults write com.apple.finder ShowStatusBar -bool true

# Finder: show path bar
defaults write com.apple.finder ShowPathbar -bool true

# Display full POSIX path as Finder window title
defaults write com.apple.finder _FXShowPosixPathInTitle -bool true

# Disable the warning when changing a file extension
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false

# Avoid creating .DS_Store files on network or USB volumes
defaults write com.apple.desktopservices DSDontWriteNetworkStores -bool true
defaults write com.apple.desktopservices DSDontWriteUSBStores -bool true

# Use list view in all Finder windows by default
# Four-letter codes for the other view modes: `icnv`, `clmv`, `glyv`
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"

# Show the ~/Library folder
chflags nohidden ~/Library && xattr -d com.apple.FinderInfo ~/Library

# Expand the following File Info panes:
# “General”, “Open with”, and “Sharing & Permissions”
defaults write com.apple.finder FXInfoPanesExpanded -dict \
	General -bool true \
	OpenWith -bool true \
	Privileges -bool true

# Enable highlight hover effect for the grid view of a stack (Dock)
defaults write com.apple.dock mouse-over-hilite-stack -bool true

# Set the icon size of Dock items to 36 pixels
defaults write com.apple.dock tilesize -int 36

# Change minimize/maximize window effect
defaults write com.apple.dock mineffect -string "scale"

# Minimize windows into their application’s icon
defaults write com.apple.dock minimize-to-application -bool true

# Enable spring loading for all Dock items
defaults write com.apple.dock enable-spring-load-actions-on-all-items -bool true

# Show indicator lights for open applications in the Dock
defaults write com.apple.dock show-process-indicators -bool true

# Don’t animate opening applications from the Dock
defaults write com.apple.dock launchanim -bool false

# Speed up Mission Control animations
defaults write com.apple.dock expose-animation-duration -float 0.1

# Don’t group windows by application in Mission Control
# (i.e. use the old Exposé behavior instead)
defaults write com.apple.dock expose-group-by-app -bool false

# Don’t automatically rearrange Spaces based on most recent use
defaults write com.apple.dock mru-spaces -bool false

# Remove the auto-hiding Dock delay
defaults write com.apple.dock autohide-delay -float 0

# Remove the animation when hiding/showing the Dock
defaults write com.apple.dock autohide-time-modifier -float 0

# Automatically hide and show the Dock
defaults write com.apple.dock autohide -bool true

# Make Dock icons of hidden applications translucent
defaults write com.apple.dock showhidden -bool true

# Don’t show recent applications in Dock
defaults write com.apple.dock show-recents -bool false

################################################################################
# Terminal & iTerm 2                                                           #
################################################################################
echo "Applying iTerm2 settings..."
# Don’t display the annoying prompt when quitting iTerm
defaults write com.googlecode.iterm2 PromptOnQuit -bool false

# TODO: Other settings.


################################################################################
# VSCode                                                                       #
################################################################################
# Find VSCode directory on machine.
VSCODE_DIR="$HOME/Library/Application Support/VS Code @ FB"

if [ ! -d "$VSCODE_DIR" ]; then
  VSCODE_DIR="$HOME/Library/Application Support/Code"
fi

# TODO: Refactor into functions section, add header formatting.
add_vscode_snippet() {
  SNIPPETS_FILENAME="$1.code-snippets"

  if [ ! -f "$VSCODE_DIR/User/snippets/$SNIPPETS_FILENAME" ]; then
    mkdir -p "$VSCODE_DIR/User/snippets/"
    ln -s \
      "$S_DOTFILE_ROOT/settings/$SNIPPETS_FILENAME" \
      "$VSCODE_DIR/User/snippets/$SNIPPETS_FILENAME"
  fi
}

SNIPPETS_FILE_NAME="VSCodeGlobalSnippets.code-snippets"

if [ -d "$VSCODE_DIR" ]; then
  # Copy default settings if they do not exist.
  if [ ! -f "$VSCODE_DIR/User/settings.json" ]; then
    echo "Copying VSCode default settings..."
    cp \
      "$S_DOTFILE_ROOT"/settings/VSCodeSettings.json
      "$VSCODE_DIR/User/settings.json"
  fi

  # Global snippets.
  echo "Linking VSCode snippets..." 
  add_vscode_snippet VSCodeGlobalSnippets
  add_vscode_snippet VSCodeCSnippets
fi

################################################################################
# Misc applications                                                            #
################################################################################
echo "Applying other application settings..."

## Google Chrome & Google Chrome Canary:
# Disable the all too sensitive backswipe on Magic Mouse
defaults write com.google.Chrome AppleEnableMouseSwipeNavigateWithScrolls -bool false
defaults write com.google.Chrome.canary AppleEnableMouseSwipeNavigateWithScrolls -bool false

# Use the system-native print preview dialog
defaults write com.google.Chrome DisablePrintPreview -bool true
defaults write com.google.Chrome.canary DisablePrintPreview -bool true

## Apple Music:
# Don't show notification when a new song starts.
defaults write com.apple.Music "userWantsPlaybackNotifications" -bool "false" && killall Music

################################################################################
# Post settings.                                                               #
################################################################################
echo "Restarting affected applications..."
# Kill affected applictions
for app in "Activity Monitor" \
	"cfprefsd" \
	"Dock" \
	"Finder" \
	"Google Chrome Canary" \
	"Google Chrome" \
	"Safari" \
	"SystemUIServer" \
	"Terminal"; \
    do
	killall "${app}" &> /dev/null

echo "Done. Note that some of these changes require a logout/restart to take effect."

