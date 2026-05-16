#!/bin/sh
# Author: Scott MacDonald
# Purpose: Pretty print a file starting at a specific line number suitable.
#
# rgcat path/to/file:line_number args...
#
# This script was originally written as a preview formatter for a ripgrep tool,
# although it can be used for other purposes too.
################################################################################
# TODO: Bold or otherwise format the selected line?
# TODO: Send selected text to a syntax highlighter?

################################################################################
# Prints usage information to stderr and then exits the process.
################################################################################
usage_and_die() {
  printf "Pretty print several lines of a file (ripgrep cat)"
  printf "Usage: %s path/to/file:line_number\n" "$(basename "$0")" >&2
  exit 2
}

################################################################################
# Prints an error message to stderr.
#
# Arguments
#  $1..$N  Text to print.  
################################################################################
err() {
  echo "ERROR: " "$@"
}

################################################################################
# Main function.
################################################################################
main() {
  # Extract the file path and line number from the first argument.
  if [ -z "$1" ]; then
    usage_and_die
  fi

  file=$(echo "$1" | cut -d':' -f1)
  line=$(echo "$1" | cut -d':' -f2)

  # Make sure the file is readable
  if [ ! -r "$file" ]; then
    err "Could not read file '$file'"
    usage_and_die
  fi

  # TODO: Can we check if line number is a positive integer value?
  if [ -z "$line" ]; then
    err "Line number is missing"
    usage_and_die
  fi

  # Grab escape codes for bold / unbold to aid in highlighting the current line.
  hl_s=$(printf '\033[1m')
  hl_e=$(printf '\033[0m')

  # Extract and format lines.
  sed -n "$line,$((line + 10))"p "$file" | # Extract 10 lines starting at...
    nl -d '\n' -v "$line" |                # Prefix each line with line no.
    sed -E "s/^([[:space:]]*$line)(.*)$/$hl_s\1\2$hl_e/"
}

main "$@"
