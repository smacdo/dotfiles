# Top Level Scripts
## Bootstrap
- [x] Replace occurrences of .dotfiles with a environment variable
- Add option to cancel (skip) the backup/delete interactive prompt.
- Check if target exists, is a symlink and was symlinked somewhere in dotfiles repo for safe_symlink.
- download_file: Download to temporary location, and compare to dest. Prompt user if there is mismatch.

## Linting
- [x] Lint shell scripts with shellcheck
- Suppress the "All checks passed!" output from mypy. 
- Print out a summary of the files with failing lints at the end.
- Lint `run_tests.py`

## Testing
- [x] Add script to automate dotfile updating, syncing
- ~~Finish post init scripts~~
- Discover and run python unit tests in bin/ scripts
- run_pydotlib_tests: Search for pydotlib modules without having to hardcode the names.
- Print docker output when a docker test run fails
- Refactor docker script code into pydotlib module.
- Docker test: Run bootstrap.py to validate functionality for debian, fedora and ubuntu
- Docker test: post bootstrap, check if bash OK
- Docker test: post bootstrap, check if ZSH OK
- Docker test: post bootstrap, check if vim OK
- Docker test: post bootstrap, check if neovim OK
- Docker test: post bootstrap, check if tmux OK
- Docker test: post bootstrap, check if git OK

## Misc
- Export dotfiles as a tarball/zip for machines that cannot connect to internet. The archive should include out of tree files, and be made to expand in user home dir, eg
  - ./.dotfiles/...
  - ./.config/neovim
  - ...
- Export the _pydotlib so python bin scripts can use them.

# Configs
## Neovim
- Create crontab script to nuke backups after ~ 90 days?

# Bugs
- neovim not detecting BUCK file type
- neovim should detect hg commit message, and then not hard linebreak on them

# Misc
- Github action to run linter
- Github action to run tests

# Bin Scripts
- Script that line breaks excessively long command lines
- backup: Simple script that creates foo.bak_N while avoiding race conditions
- mksh:
  - source the author name for an dotfile envvar $S_DEFAULT_AUTHOR
