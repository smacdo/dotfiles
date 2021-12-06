#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Continuous integration script for the dotfiles repository.
#
# Working directory must be root of dotfiles.
# TODO: Shellcheck myself

check_result() {
  # TODO: Make custom continue or abort
  if [ "$1" -ne 0 ]; then
    echo "FAIL (code $1): $2 $3"
    exit "$?"
  else
    echo "OK $2 $3"
  fi
}

################################################################################
# Run shellcheck for a given script.
################################################################################
lint_shell_script() {
  # SC1090 - ignore warning for can't follow non-constant source.
  # SC1091 - ignore warning for included files that cannot be found.
  shellcheck "$1" -e SC1090 -e SC1091
  check_result $? "shellcheck" "$1"
}

################################################################################
# Run shellcheck for a given script.
################################################################################
main() {
  for s in \
        "$(basename "$0")" \
        ".bash_profile" \
        ".bashrc" \
        "setup.sh" \
        "bin/code" \
        "bin/colors" \
        "bin/delete_dsstore_recursive.sh" \
        "bin/find_todo.sh" \
        "bin/generate-ssh-key.sh" \
        "bin/find_todo.sh" \
        "bin/rgcat.sh" \
        "bin/subl" \
        "bin/weather_status.sh" \
        "shell_profile/aliases.sh" \
        "shell_profile/exports.sh" \
        "shell_profile/functions.sh" \
        "shell_profile/paths.sh" \
        "shell_profile/xdg.sh" \
        ; do
    lint_shell_script "$s"
  done

  echo "*** SUCCESS! ***"
}

main "$*"; exit
