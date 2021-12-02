#!/bin/sh
# rgcat path/to/file:line_number args...
# 'ripgrep cat'
#
# Given a file name and line number this script will print out  N lines starting
# at the given line number.
# TODO: Document and finish
# TODO: Error checking, help etc
FILE=$(echo "$1" | cut -d':' -f1)
LINE=$(echo "$1" | cut -d':' -f2)
sed -n "$LINE","$(($LINE + 10))"p "$FILE"
