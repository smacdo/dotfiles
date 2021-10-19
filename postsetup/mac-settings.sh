#!/bin/sh
####

# TODO: Verify running in admin mode

# Dark mode
osascript -e 'tell app "System Events" to tell appearance preferences to set dark mode to not dark mode'

# Auto hide the doc
defaults write NSGlobalDomain _HIHideMenuBar -bool true

# killall Finder
