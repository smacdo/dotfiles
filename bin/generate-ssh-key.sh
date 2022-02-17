#!/bin/sh
# Generates a ssh key for the current machine if it does not exist. Automates
# the initial GitHub SSH key registration process for a new machine, see [1].
#
# [1] https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
keyname="id_ed25519"
privateFilePath="${HOME}/.ssh/${keyname}"
publicFilePath="${privateFilePath}.pub"

if [ ! -f "${HOME}/.ssh/${keyname}" ]; then
  printf "GitHub e-mail address: "
  read -r email
  ssh-keygen -t ed25519 -C "${email}" -f "$privateFilePath"
  echo "Created new ssh key $keyname"
else
  echo "Using existing ssh key $keyname"
fi

# Double check that file was created as expected.
if [ ! -f "$publicFilePath" ]; then
  echo "ERROR: Could not find public key: $publicFilePath"
  exit 1
fi

# Add key to the ssh-agent.
configPath="${HOME}/.ssh/config"

if [ ! -f "$configPath" ]; then
  touch "$configPath"
fi

if ! grep -qF "IdentityFile ~/.ssh/$keyname" "$configPath"; then
  echo "Adding entry for $keyname to $configPath"

  echo "Host *" >> "$configPath"
  echo " IgnoreUnknown UseKeychain" >> "$configPath" 
  echo " AddKeysToAgent yes" >> "$configPath"
  echo " UseKeychain yes" >> "$configPath"
  echo " IdentityFile ~/.ssh/$keyname" >> "$configPath"
fi

echo "Adding $keyname to ssh-agent"
ssh-add -K "$privateFilePath"

# Show the public key and put it in the clipboard.
# For MacOS, you can use copy contents of the public key to the clipboard with
# `pbcopy < ~/.ssh/$keyname.pub`
echo "SSH public key path: $publicFilePath"
echo "Value: $(cat "$publicFilePath")"
echo
echo "Register this key on GitHub using the following URL: "
echo "https://github.com/settings/keys"
