#!/bin/sh
# Author: Scott MacDonald
# Purpose: Locate TODO fragments in source code files for editing.
################################################################################
# TODO: Support FIXME, XXX
# TODO: Support custom paths, etc
# TODO: Support grep if rg not found
# TODO: Support multiple selections.
# TODO: Dotfile path to rgcat.sh
TODOFMT="TODO(\(.*\))?:"
PICK=$(rg "$TODOFMT" --no-heading --line-number | fzf --preview 'rgcat.sh {}')
file=$(echo "$PICK" | cut -d':' -f1)
line=$(echo "$PICK" | cut -d':' -f2)

# TODO: Fallback if EDITOR not defined.
# TODO: Don't launch editor if fzf cancelled (error check)
# TODO: Check file readable
if [ -n "$file" ]; then
  $EDITOR +"$line" "$file"
fi
