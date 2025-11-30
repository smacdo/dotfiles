#!/bin/sh
# Configures XDG environment variables if not already configured

#==============================================================================#
# Defines an XDG environment variable, if it was not already defined. The XDG
# directory will be created if it does not exist.
#
# Argument:
#  $1: The XDG environment variable name.
#  $2: The current value of the XDG environment variable.
#  $3: A default value to use if there is not existing value.
#==============================================================================#
xdg_define()
{
    ENV_NAME=$1
    CURRENT_VAL=$2
    DEFAULT_DIR=$3

    # Export environment variable if one does not exist.
    if [ -z "${CURRENT_VAL}" ]; then
        export "${ENV_NAME}"="${DEFAULT_DIR}"
        ACTUAL_VAL="${DEFAULT_DIR}"
    else
        ACTUAL_VAL="${CURRENT_VAL}"
    fi

    # Create the directory if it does not exist.
    if [ ! -d "${ACTUAL_VAL}" ]; then
        mkdir -p "${ACTUAL_VAL}"
    fi
}

xdg_define "XDG_DATA_HOME" "${XDG_DATA_HOME}" "${HOME}/.local/share"
xdg_define "XDG_CONFIG_HOME" "${XDG_CONFIG_HOME}" "${HOME}/.config"
xdg_define "XDG_STATE_HOME" "${XDG_STATE_HOME}" "${HOME}/.local/state"
xdg_define "XDG_CACHE_HOME" "${XDG_CACHE_HOME}" "${HOME}/.cache"