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
  2. Copy the `./bootstrap.py` script that automates new machine setup.
  3. Create new files for each of the matching configs (`.bashrc`, `.vimrc`,
  etc) that you want, and copy over any interesting configuration settings.
  4. Modify `./bootstrap.py` to match your new setup.
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

### Prerequisites

- **macOS**: install [Homebrew](https://brew.sh/) first. These dotfiles assume `brew` is already on your `PATH` and do not install it for you.

### Bootstrap

Clone the dotfiles repository to your machine, then symbolically link standard shell config files (`.vimrc`, `.bashrc`, `.zshrc`, etc.) to files found in this repository.

```
git clone git@github.com:smacdo/dotfiles.git ~/.dotfiles
cd ~/.dotfiles && ./bootstrap.py
```	

Restart or reload your shell. This step varies depending on the shell you are
using, for example on bash you should run `source ~/.bashrc` and on zsh you want
to run `source ~/.zshrc`.

`bootstrap.py` only handles symlinks, vim plugin manager, p10k, and a few other
configs — it does not install system packages. Install the tools you want with
your platform's package manager (Homebrew, apt, dnf). The optional helpers in
`tools/` install a few extras:

```
./tools/install_uv.sh             # uv (used by lint_all.py)
./tools/install_rust.sh           # rustup
./tools/install_nerd_fonts.sh     # JetBrainsMono Nerd Font
./tools/install_powerlevel10k.sh  # zsh powerlevel10k theme
sudo ./tools/install_vscode.sh    # VS Code (Debian/Ubuntu, Fedora/RHEL/CentOS)
```

Don't forget to tell (neo)vim to install plugins the first time you start it up
by running `:PlugInstall`.

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

## Meeting Reminders (next-meeting)
The `next-meeting` script shows upcoming Google Calendar meetings in the tmux
status bar and optionally in the Claude Code status line. It supports two
calendar backends: `gcal` (google_mux, preferred on devservers) and `gcalcli`
(for personal machines). The script auto-detects which is available.

### Setup
On devservers (`gcal` / google_mux): already installed. Restart tmux.

On personal machines, this feature is optional. If you want meeting reminders,
install and authenticate `gcalcli`:

1. Install: `pip install gcalcli` or `brew install gcalcli`
2. Authenticate: `gcalcli init`
3. Restart tmux or run `tmux source ~/.tmux.conf`

`bootstrap.py` does not install calendar tooling.

Run `next-meeting` with no arguments for a quick list of today's meetings.

### Configuration
All settings are optional environment variables, set in
`~/.config/dotfiles/my_shell_profile.sh`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_MEETING_SHOW` | 30 | Show in tmux when within N minutes |
| `NEXT_MEETING_WARN` | 5 | Yellow warning threshold (minutes) |
| `NEXT_MEETING_CRITICAL` | 2 | Red critical threshold (minutes) |
| `NEXT_MEETING_CACHE_TTL` | 120 | Seconds between calendar refreshes |
| `NEXT_MEETING_ALERT_AT` | 5,0 | Fire tmux alerts at these minute marks |

## Packages
* lesspipe

## Troubleshooting
### Exception urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1020)>
MacOS Python installations (especially from brew, python.org) ship without bundling the system's certificate store. You will need to run the following once to initialize the certifacte store:

   open /Applications/Python\ 3.X/Install\ Certificates.command

so for Python 3.13, you'd run:

   open /Applications/Python\ 3.13/Install\ Certificates.command

Try re-running the script, and it should work.
