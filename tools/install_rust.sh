#!/bin/sh
if command -v rustup >/dev/null 2>&1; then
  echo "rustup already installed"
  exit 0
fi

if command -v curl >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path
elif command -v wget >/dev/null 2>&1; then
  wget --https-only --secure-protocol=TLSv1_2 -qO- https://sh.rustup.rs | sh -s -- -y --no-modify-path
else
  echo "curl or wget is required to install rust" >&2
  exit 1
fi
