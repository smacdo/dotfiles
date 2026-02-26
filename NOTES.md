# Notes

## OS Setup

### Debian 13

#### rustup
```
curl https://sh.rustup.rs -sSf | sh -s
```

#### wezterm
```
$ curl https://sh.rustup.rs -sSf | sh -s
$ curl -LO https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22-src.tar.gz
$ tar -xzf wezterm-20240203-110809-5046fc22-src.tar.gz
$ cd wezterm-20240203-110809-5046fc22
$ ./get-deps
$ cargo build --release
$ cargo run --release --bin wezterm -- start
```

## Settings
Some quick notes on settings for various programs on my machines that I may not have time to
automate.

### VSCode

#### Macbook
extensions
 - c/c++ (these are old, check if they are still best for C++ dev)
    - ms-vscode.cpptools  (maybe not by default anymore, need to explore alternatives)
    - ms-vscode.cpp-devtools (same, explore if still needed)
    - ms-vscode.cpptools-themes
    - xaver.clang-format
    - twxs.cmake
    - ms-vscode.cmake-tools
 - catppuccin.catppuccin-vsc
 - catppuccin.catppuccin-vsc-icons
 - anthropic.claude-code
 - github.vscode-pull-request-github
 - ms-azuretools.vscode-docker
 - web 
   - dbaeumer.vscode-eslint
   - esbenp.prettier-vscode
 - tamasfe.even-better-toml
 - python
   - ms-python.vscode-pylance
   - ms-python.python
   - ms-python.debugpy
   - ms-python.vscode-python-envs
 - mechatroner.rainbow-csv
 - rust
   - charliermarsh.ruff
   - rust-lang.rust-analyzer
   - redhat.vscode-yaml


settings.json

```
{
    "claudeCode.preferredLocation": "panel",

    "files.autoSave": "onWindowChange",
    "editor.rulers": [
        80,
        100,
        120
    ],
    // formatOnSave modifications seems to be finicky, I noticed rust and maybe python didn't work out of box
    "editor.formatOnSave": true,
    "editor.formatOnSaveMode": "modifications",

    "[rust]": {
        "editor.defaultFormatter": "rust-lang.rust-analyzer",
        "editor.formatOnSave": true,
        "editor.formatOnSaveMode": "file",
        "editor.tabSize": 4
    },
    "rust-analyzer.check.command": "clippy",

    "typescript.inlayHints.propertyDeclarationTypes.enabled": true,
    "typescript.inlayHints.variableTypes.enabled": true,
    "typescript.inlayHints.parameterNames.suppressWhenArgumentMatchesName": false,
    "typescript.inlayHints.variableTypes.suppressWhenTypeMatchesName": false,

    // maybe not anymore? leave to language defaults
    "editor.tabSize": 2,
    "editor.minimap.enabled": false,
    "editor.fontSize": 13,
    "editor.fontFamily": "JetBrainsMono Nerd Font, JetBrainsMono, Menlo, Monaco, 'Courier New', monospace",
}
```
