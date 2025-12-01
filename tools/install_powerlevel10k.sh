#!/bin/sh
dest_dir=${XDG_DATA_HOME:-~/.local/share}/powerlevel10k
mkdir -p "$dest_dir"
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$dest_dir"
