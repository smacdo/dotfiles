#!/bin/sh
#==============================================================================#
# Author: Scott MacDonald
# Purpose: Verify bootstrap.py created the expected symlinks, dirs, and configs
# Usage: ./verify_bootstrap.sh
#==============================================================================#
# vim: set filetype=sh :
set -e
set -u

# shellcheck disable=SC3040
(set -o pipefail 2> /dev/null) && set -o pipefail

failures=0

check_symlink() {
  link="$1"
  expected_target="$2"

  if [ ! -L "$link" ]; then
    echo "FAIL: $link is not a symlink"
    failures=$((failures + 1))
    return
  fi

  actual_target="$(readlink "$link")"
  if [ "$actual_target" != "$expected_target" ]; then
    echo "FAIL: $link -> $actual_target (expected $expected_target)"
    failures=$((failures + 1))
    return
  fi

  echo "OK: $link -> $expected_target"
}

check_dir() {
  dir="$1"

  if [ ! -d "$dir" ]; then
    echo "FAIL: directory $dir does not exist"
    failures=$((failures + 1))
    return
  fi

  echo "OK: $dir exists"
}

check_file_contains() {
  file="$1"
  expected="$2"

  if [ ! -f "$file" ]; then
    echo "FAIL: $file does not exist"
    failures=$((failures + 1))
    return
  fi

  if ! grep -q "$expected" "$file"; then
    echo "FAIL: $file does not contain '$expected'"
    failures=$((failures + 1))
    return
  fi

  echo "OK: $file contains '$expected'"
}

home="$HOME"
dotfiles="$home/.dotfiles"

echo "=== Checking symlinks ==="
check_symlink "$home/.bashrc"       "$dotfiles/.bashrc"
check_symlink "$home/.bash_profile" "$dotfiles/.bash_profile"
check_symlink "$home/.gitconfig"    "$dotfiles/.gitconfig"
check_symlink "$home/.tmux.conf"    "$dotfiles/.tmux.conf"
check_symlink "$home/.vimrc"        "$dotfiles/settings/nvim/init.vim"
check_symlink "$home/.vim"          "$dotfiles/.vim"

echo ""
echo "=== Checking XDG state dirs ==="
check_dir "$home/.local/state/vim/backups"
check_dir "$home/.local/state/vim/tmp"

echo ""
echo "=== Checking .my_gitconfig ==="
check_file_contains "$home/.my_gitconfig" "Testy McTestFace"
check_file_contains "$home/.my_gitconfig" "testy@test.com"

echo ""
if [ "$failures" -ne 0 ]; then
  echo "FAILED: $failures check(s) failed"
  exit 1
fi

echo "All checks passed"
