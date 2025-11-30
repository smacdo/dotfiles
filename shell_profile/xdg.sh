#!/bin/bash
# Configures XDG environment variables if not already configured
# TODO: Rewrite this for `sh` not `bash`.
xdg_define()
{
    ENV_NAME=$1
    CURRENT_VAL=$2
    DEFAULT_DIR=$3

    # Export environment variable if one does not exist.
    if [[ -z "${CURRENT_VAL}" ]]; then
        export "${ENV_NAME}"="${DEFAULT_DIR}"
    fi

    # Create directory for value if it does not exist.
    if [[ ! -d "${DEFAULT_DIR}" ]]; then
        mkdir -p "${DEFAULT_DIR}"
    fi
}

xdg_define "XDG_DATA_HOME" "${XDG_DATA_HOME}" "${HOME}/.local/share"
xdg_define "XDG_CONFIG_HOME" "${XDG_CONFIG_HOME}" "${HOME}/.config"
xdg_define "XDG_STATE_HOME" "${XDG_STATE_HOME}" "${HOME}/.local/state"
xdg_define "XDG_CACHE_HOME" "${XDG_CACHE_HOME}" "${HOME}/.cache"
