# About
This repository is my collection of shell scripts and configuration files that
I use across various *nix machines. It takes the work out of installing
everything manually, and automatically configures everything to my preferred
workflow on both Linux, and Mac.

Feel free to copy anything you see in this repository. Credit is always welcome
but not required. I've tried to comment most of the files here to help other
readers learn from my experience. See the section on using this repository for
more details (please read before forking!). 

# Forking this repository
Please do not blindly fork this repository! I strongly recommend you read
through my dotfiles, and copy anything you like over to your own dotfiles
repository.

If you are starting from scratch (you don't have your own dotfiles repository
yet), then I recommend you do the following:

  1. Create a new dotfiles repository for yourself
  2. Copy the `./bootstrap.sh` and `./setup.sh` scripts that automate new machine
  setup.
  3. Create new files for each of the matching configs (`.bashrc`, `.vimrc`, 
  etc) that you want, and copy over any interesting configuration settings.
  4. Modify `./bootstrap.sh` and `./setup.sh` to match your new setup.
  5. Continue copying what you need from my (and other peoples!) dotfile
  repositories.
  5. Profit!!

Feel free to contact me if you have questions!

# Instructions
## Registering SSH key with GitHub
Make sure to do this prior to cloning if you are on a machine that you want to
push dotfile updates from. Original instructions were copied from the [GitHub
official documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).

```
curl https://raw.githubusercontent.com/smacdo/dotfiles/master/bin/generate-ssh-key.sh | sh -s
```

## Setup
First you need to clone the dotfiles repository to your machine, and symbolically
link standard shell config files (.vimrc, .bashrc, .zshrc etc) to files found in
this repository.

```
git clone git@github.com:smacdo/dotfiles.git ~/.dotfiles
cd ~/.dotfiles && ./bootstrap.py
```	

Restart or reload your shell. This step varies depending on the shell you are
using, for example on bash you should run `source ~/.bashrc` and on zsh you want
to run `source ~/.zshrc`.

The next shell script will install "core" programs (bash, zsh, neovim, fzf,
ripgrep, etc). It will also detect your current desktop environment (MacOS or
Gnome) and update the default settings to match what I like.

```
cd ~/.dotfiles
./setup.sh -p core
```

**Important note**: For MacOS machines where you want homebrew to install packages
to your home directory (rather than system wide), you want to add the `-H` flag
to setup: `./setup.sh -H -p core`.

With that done you should be good to go! Don't forget to tell (neo)vim to install
plugins the first time you start it up by running `:PlugInstall`.

# Manual Configuration Notes
These notes are here because I haven't fully automated all my machine
configuration yet. Maybe I'll do that someday.

## MacOS
* Settings -> Security & Privacy -> Full Disk Access -> + "Visual Studio Code"
* Configure Terminal
  * Profiles -> Basic -> Font -> JetBrains Mono 11
* Install iTerm2
* Configure iTerm2
  * General -> Startup -> Window restoration policy -> Only Restore Hotkey Window
  * General -> Closing -> Quit when all windows are closed [x]
  * General -> Closing -> Confirm "Quit iTerm2" [ ]
  * Keys -> Navigation Shortcuts -> Shortcut to choose a split pane = ^ Number
  * Keys -> Hotkey -> Create a dedicated hotkey window...
  * General -> Profiles -> Default
    * Colors -> Color Presets (Smoooooth)
    * Text -> Font -> JetBrains Mono Regular 12
    * Text -> Use built-in Powerline glyphs [x]
    * Terminal -> Scrollback lines unlimited scrollback [x]
    * Terminal -> Flash visual bell [x]
    * Keys -> Left Option Key = Esc+a

## Packages
* lesspipe
