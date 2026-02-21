# Debian 13 New Installation
## rustup
```
curl https://sh.rustup.rs -sSf | sh -s
```

## wezterm
```
$ curl https://sh.rustup.rs -sSf | sh -s
$ curl -LO https://github.com/wezterm/wezterm/releases/download/20240203-110809-5046fc22/wezterm-20240203-110809-5046fc22-src.tar.gz
$ tar -xzf wezterm-20240203-110809-5046fc22-src.tar.gz
$ cd wezterm-20240203-110809-5046fc22
$ ./get-deps
$ cargo build --release
$ cargo run --release --bin wezterm -- start
```
