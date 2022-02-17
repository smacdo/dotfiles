#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Continuous integration script for the dotfiles repository.
#
# Working directory must be root of dotfiles.

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

test_zsh() {
  old_ZDOTDIR="$ZDOTDIR"
  # TODO: Make relative.
  export ZDOTDIR="$HOME/.dotfiles/"

  if [ ! -f "$ZDOTDIR/.zshrc" ]; then
    echo "ERROR: could not find .zshrc in dotfiles repo"
    exit 1
  fi

  output=$(zsh -i -c "echo 'success'; exit 0" 2>&1)
  
  if [ "$output" != "success" ]; then
    echo "ERROR: zsh run failed; expected output 'success' but got '$output'"
    exit 2
  else
    echo "zsh ok"
  fi

  export ZDOTDIR="$old_ZDOTDIR"
}

test_bash() {
  # TODO: Test .bash_profile
  bashrc_path="$HOME/.dotfiles/.bashrc"

  if [ ! -f "$bashrc_path" ]; then
    echo "ERROR: could not find .bashrc in dotfiles repo"
    exit 1
  fi

  export DOTFILE_CI_TEST_MODE=1
  output=$(bash --rcfile "$HOME/.dotfiles/.bashrc" --login -c "echo 'success'; exit 0" 2>&1)

  if [ "$output" != "success" ]; then
    echo "ERROR: bashrc check failed; expected output 'success' but got '$output'"
    exit 1
  else
    echo "bashrc ok"
  fi
}

# TODO: test sh

################################################################################
# Run shellcheck for a given script.
################################################################################
main() {
  test_bash
  test_zsh

  for s in \
        "$(basename "$0")" \
        ".bash_profile" \
        ".bashrc" \
        "bootstrap.sh" \
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
        "sh/cli.sh" \
        "shell_profile/aliases.sh" \
        "shell_profile/exports.sh" \
        "shell_profile/functions.sh" \
        "shell_profile/paths.sh" \
        "shell_profile/xdg.sh" \
        ; do
    lint_shell_script "$s"
  done

  # TODO: Determine if any errors were present when linting (as opposed to
  # warnings), and print that result down here.

  echo "*** SUCCESS! ***"
}

main "$*"; exit
