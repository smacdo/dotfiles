is_osx || return 1

# Copy contents to clipboard after trimming newlines
alias clip="tr -d '\n' | pbcopy"

# Start the screen saver.
alias screensaver="/System/Library/CoreServices/ScreenSaverEngine.app/Contents/MacOS/ScreenSaverEngine"
