#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Prints weather information suitable for display in a status bar.
################################################################################
# Information about wttr.in, including the formatting options used below can be
# at https://github.com/chubin/wttr.in
#
# The format used below has the following data arranged in order:
# Location;Condition;Temp;Precip;Moon;Sunset;Sunrise

# TODO: Fallback for cache if XDG_STATE_HOME not defined + create the cache file
#       if it didn't already exist.


################################################################################
# Write error text to stderr.
# 
# Arguments:
#  $* - Text to write.
# Output:
#  Text.
################################################################################
error() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

################################################################################
# Test if file X was modified in the last Y seconds.
# 
# Arguments:
#  $1 TIME_IN_SECS:  Accepted time window in seconds.
#  $2 FILE_TO_CHECK: Path to file to check.
# Outputs:
#  Writes a message if an error condition is encountered.
# Returns:
#  0 if file has been modified in the last Y seconds.
#  1 if file was not modified in the last Y seconds.
#  2 if argument(s) are missing.
#  3 if the file does not exist.
################################################################################
is_file_newer_than() {
  TIME_IN_SEC=$1
  FILE_TO_CHECK=$2

  # Test parameters were passed.
  if [ -z "${TIME_IN_SEC}" ]; then
    error "ARG 1 (TIME_IN_SECS) was not provided to is_file_newer_than"
    return 2
  fi

  if [ -z "${FILE_TO_CHECK}" ]; then
    error "ARG 2 (FILE_TO_CHECK) was not provided to is_file_newer_than"
    return 2
  fi

  if [ ! -f "${FILE_TO_CHECK}" ]; then
    error "ERROR: File does not exist '${FILE_TO_CHECK}'"
    return 3
  fi

  # Get the number of seconds since file was last modified.
  FILE_LASTMOD_SEC=$(stat "${FILE_TO_CHECK}" -c %Y)

  # Get the current number of seconds.
  NOW_SEC=$(date +%s)

  # Find the number of seconds that have elapsed since the file was modified.
  DELTA_SEC=$(("${NOW_SEC}" - "${FILE_LASTMOD_SEC}"))

  # Return 0 (success) if the last modified time is less than or equal to the
  # requested number of seconds, otherwise return 1 (error).
  if [ "${DELTA_SEC}" -le "$TIME_IN_SEC" ]; then
    return 0
  else
    return 1
  fi
}

################################################################################
# Get the latest weather data for a location.
#
# Globals:
#  WEATHER_LOCATION - Optional location used if no location arguent given.
# Arguments:
#  $1 - Name of location to look up, otherwise global WEATHER_LOCATION is used.
# Outputs:
#  Semicolon delimitted array of weather values for requested location.
################################################################################
get_latest_weather_data() {
  LOCATION=${1:-${WEATHER_LOCATION}}
  curl -s wttr.in/"${LOCATION}"?format="%l;%c;%C;%t;%p;%P;%m;%s;%S;%h"\
    || return 1

}

################################################################################
# Get recent weather data for a location; from the cache if a recent result was
# stored otherwise a query to the weather web service will be made.
#
# Globals:
#  WEATHER_LOCATION - Optional location used if no location arguent given.
#  XDG_STATE_HOME   - Optional location to store user cache values.
# Arguments:
#  $1 - Name of location to look up, otherwise global WEATHER_LOCATION is used.
#  $2 - Number of seconds before doing a web request. 300 seconds by default.
# Outputs:
#  Semicolon delimitted array of weather values for requested location.
################################################################################
get_weather_data() {
  LOCATION=${1:-${WEATHER_LOCATION}}
  MAX_SEC=${2:-300} # 5 minutes by default.

  CACHE_FILE="${XDG_STATE_HOME}/scott-last-weather"

  # Check if there is a cached weather result that is readable.
  if [ -r "${CACHE_FILE}" ]; then
    # and if the cache is still warm enough to reuse.
    if is_file_newer_than "${MAX_SEC}" "${CACHE_FILE}"; then
      # and if the location matches
      CACHED_WEATHER=$(cat "${CACHE_FILE}")
      SAVEDLOC=$(echo "${CACHED_WEATHER}" | cut -d ';' -f1)

      if [ "${SAVEDLOC}" = "${LOCATION}" ]; then
        cat "${CACHE_FILE}"
        return 0
      fi
    fi
  fi

  # Get the result from wttr, and write to the cache.
  LATEST_WEATHER=$(get_latest_weather_data "${LOCATION}")
  WEATHER="${LOCATION};${LATEST_WEATHER}"

  # Write latest results to cache, but only if cache file is writable.
  # Note that it's not an error if the cache file isn't writable.
  if [ -w "${CACHE_FILE}" ] || [ -w "$(dirname "${CACHE_FILE}")" ]; then
    echo "${WEATHER}" > "${CACHE_FILE}"
  fi

  # Print the weather aata since it is not possible to return string data in
  # a shell script.
  echo "${WEATHER}"
}

################################################################################
# Print the recent weather data for a location in a form that is suitable for
# a status bar.
#
# Globals:
#  WEATHER_LOCATION - Optional location used if no location arguent given.
#  XDG_STATE_HOME   - Optional location to store user cache values.
# Arguments:
#  $1 - Name of location to look up, otherwise global WEATHER_LOCATION is used.
#  $2 - Number of seconds before doing a web request. 300 seconds by default.
# Outputs:
#  Weather text suitable for a status bar.
################################################################################
main() {
  LOCATION=${1:-${WEATHER_LOCATION}}
  MAX_SEC=${2:-300} # 5 minutes by default.

  # Get 
  WEATHER=$(get_weather_data "${LOCATION}" "${MAX_SEC}")

  # Split results into different variables since the weather status is dynamic.
  LOCATION=$(echo "$WEATHER" | cut -d ';' -f2)
  COND=$(echo "$WEATHER" | cut -d ';' -f3)
  COND_FULL=$(echo "$WEATHER" | cut -d ';' -f4)
  TEMP=$(echo "$WEATHER" | cut -d ';' -f5)
  PRECIP=$(echo "$WEATHER" | cut -d ';' -f6)
  PRESSURE=$(echo "$WEATHER" | cut -d ';' -f7)
  MOON=$(echo "$WEATHER" | cut -d ';' -f8)
  SUNSET=$(echo "$WEATHER" | cut -d ';' -f9)
  SUNRISE=$(echo "$WEATHER" | cut -d ';' -f10)
  HUMIDITY=$(echo "$WEATHER" | cut -d ';' -f11)

  SHORT_LOCATION=$(echo "$LOCATION" | cut -d ',' -f1)

  # Display the short status by default, unless the user asks for a full info
  # dump.
  if [ "$3" = "full" ]; then
      echo "LOCATION   : $LOCATION"
      echo "CONDITIONS : $COND  $COND_FULL"
      echo "TEMPERATURE: $TEMP"
      echo "PRECIP     : $PRECIP"
      echo "HUMIDITY   : $HUMIDITY"
      echo "PRESSURE   : $PRESSURE"
      echo "MOON       : $MOON"
      echo "SUNSET     : $SUNSET"
      echo "SUNRISE    : $SUNRISE"
  else
      echo "$SHORT_LOCATION $TEMP $COND "
  fi
}

main "$@"; exit
