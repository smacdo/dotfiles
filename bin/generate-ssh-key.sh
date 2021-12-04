#!/bin/sh
# Generates a ssh key for the current machine, if it does not already exist.
keyname="id_ed25519"

if [ ! -f "${HOME}/.ssh/${keyname}" ]; then
  echo "No public key found, creating a new one..."
  printf "E-mail address: "
  read -r email
  ssh-keygen -t ed25519 -C "${email}" -f "${HOME}/.ssh/${keyname}"
fi

if [ -f "${HOME}/.ssh/${keyname}" ]; then
  cat "${HOME}/.ssh/${keyname}.pub"
else
  echo "ERROR: Could not find public key"
fi
