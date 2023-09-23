#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Continuous integration script for the dotfiles repository.
#
# Working directory must be root of dotfiles.

# TODO: Change references of .dotfiles to a custom specifiable value.

################################################################################
# Checks the provided exit code is success (zero), or exits with the non-zero
# exit code.
#
# Arguments
#  $1: The non-zero exit code.
#  $2: Name of the program that produced the exit code.
#  $3: A helpful message describing why the program was invoked.
################################################################################
check_result() {
  # TODO: Make custom continue or abort
  if [ "$1" -ne 0 ]; then
    echo "$2 $3 FAIL (code $1)"
    exit "$1"
  else
    echo "$2 $3 OK"
  fi
}

################################################################################
# Check if the actual output matches the expected output, or exits with a error
# code 3.
#
# Arguments:
#  $1: The program or action that generated the output.
#  $2: The expected output.
#  $3: The actual outpu:
################################################################################
check_output() {
  action="$1"
  expected="$2"
  actual="$3"

  if [ "$expected" != "$actual" ]; then
    echo "ERROR: $action failed; expected output '$expected' but got '$actual'"
    return 3
  fi
}

################################################################################
# Check that a file exists, or exit with an error if it does not.
#
# Arguments:
#  $1: Path to the file.
################################################################################
check_file_exists() {
  if [ ! -f "$1" ]; then
    echo "ERROR: could not find path to $1"
    exit 1
  fi
}

################################################################################
# Runs the shellcheck tool on a given shell script file.
# If shellcheck exits with a non-zero value an error will be printed.
# 
# Arguments
#  $1: Path to shell script.
#
# Returns the exit code of shellcheck.
################################################################################
lint_shell_script() {
  # SC1090 - ignore warning for can't follow non-constant source.
  # SC1091 - ignore warning for included files that cannot be found.
  shellcheck "$1" -e SC1090 -e SC1091
  check_result $? "shellcheck" "$1"
}


################################################################################
# Check that zsh shell runs with no unexpected output when using the current
# dotfile zsh configuration.
#
# Prints an error and exits with a non-zero status if the test fails.
################################################################################
test_zsh() {
  old_ZDOTDIR="$ZDOTDIR"
  export ZDOTDIR="$HOME/.dotfiles/"
  check_file_exists "$ZDOTDIR/.zshrc"

  output=$(zsh -i -c "echo 'success'; exit 0" 2>&1)
  export ZDOTDIR="$old_ZDOTDIR"

  check_output "zshrc" "success" "$output" || exit $?
}

################################################################################
# Check that bash shell runs with no unexpected output when using the current
# dotfile zsh configuration.
#
# Prints an error and exits with a non-zero status if the test fails.
################################################################################
test_bash() {
  # TODO: Test .bash_profile (interactive, login)
  # .bashrc is interactive, non-login
  bash_profile_path="$HOME/.dotfiles/.bash_profile"
  bashrc_path="$HOME/.dotfiles/.bashrc"

  check_file_exists "$bash_profile_path"
  check_file_exists "$bashrc_path"

  export DOTFILE_CI_TEST_MODE=1

  output=$(bash --rcfile "$bash_profile_path" -c "echo 'success'; exit 0" 2>&1)
  check_output "bashprofile" "success" "$output" || exit $?

  output=$(bash --rcfile "$bashrc_path" --login -c "echo 'success'; exit 0" 2>&1)
  check_output "bashrc" "success" "$output" || exit $?
}

# TODO: test sh

################################################################################
# Tests everything.
################################################################################
main() {
  # First check shell configurations.
  test_bash && echo "bash OK"
  test_zsh && echo "zsh OK"

  # Run shellcheck lint on all scripts ready for use.
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
