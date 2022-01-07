#!/bin/sh
# Author: Scott MacDonald <scott@smacd.com>
# Purpose: Recursively deletes any .DS_Store files found at the given path, or
#          the current working directory if no path is specified.
#
# Usage: ./delete_dsstore_recursive path/to/dir
################################################################################
find "${1:-.}" -name '*.DS_Store' -type f -ls -delete
