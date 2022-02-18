#!/bin/sh
# Git utility functions.

################################################################################
# Checkout a git repository to a target directory, and update it to point at the
# given tag.
#
# Arguments:
#  1. NAME     Friendly name of the repository (for pretty printing).
#  2. TAG      Tag to update the repository to..
#  3. GIT_URL  URL to clone repository from.
#  4. DEST     Destination directory to clone repository to.
################################################################################
fetch_git_tag() {
  NAME=$1
  TAG=$2
  GIT_URL=$3
  DEST=$4

  # Name, url and destination are required.
  # TODO: Detect when TAG is missing and omit the argument in call to git.
  if [ -z "${NAME}" ]; then
    echo "${red}Argument 'NAME' missing for 'fetch_git_tag' call${normal}"
    exit 1
  fi

  if [ -z "${GIT_URL}" ]; then
    echo "${red}Argument 'GIT_URL' missing for 'fetch_git_tag' call${normal}"
    exit 1
  fi

  if [ -z "${GIT_URL}" ]; then
    echo "${red}Argument 'DEST' missing for 'fetch_git_tag' call${normal}"
    exit 1
  fi

  # Clone the repository if the directory doesn't already exist.
  # TODO: Can we do a checkout only for that tag? And can we update a prev
  #       checkout to a different tag?
  if [ ! -d "$DEST" ]; then
    echo "${blue}Cloning git repository for $NAME${normal}"
    git clone "$GIT_URL" "$DEST" || return 1
  else
    echo "${yellow}Destination exists, skipping checkout.${normal}"
  fi

  # Update to the requested tag.
  echo "${blue}Updating ${NAME} to tag ${TAG}${normal}"
  (cd "$DEST" && git -c advice.detachedHead=false checkout "tags/${TAG}")
}

main "$@"; exit
