#!/bin/sh
# Author: Scott MacDonald <scott@smacdo.com>
# Purpose: Get weather infor for display in a terminal status bar like tmux.
################################################################################
# Information about wttr.in, including the formatting options used below can be
# found at https://github.com/chubin/wttr.in
#
# The format used below has the following data arranged in order:
# Location;Condition;Temp;Precip;Moon;Sunset;Sunrise
WEATHER=$(curl -s wttr.in/"${WEATHER_LOCATION}"?format="%l;%c;%C;%t;%p;%P;%m;%s;%S;%h")

# Split results into different variables since the weather status is dynamic.
LOCATION=$(echo "$WEATHER" | cut -d ';' -f1)
COND=$(echo "$WEATHER" | cut -d ';' -f2)
COND_FULL=$(echo "$WEATHER" | cut -d ';' -f3)
TEMP=$(echo "$WEATHER" | cut -d ';' -f4)
PRECIP=$(echo "$WEATHER" | cut -d ';' -f5)
PRESSURE=$(echo "$WEATHER" | cut -d ';' -f6)
MOON=$(echo "$WEATHER" | cut -d ';' -f7)
SUNSET=$(echo "$WEATHER" | cut -d ';' -f8)
SUNRISE=$(echo "$WEATHER" | cut -d ';' -f9)
HUMIDITY=$(echo "$WEATHER" | cut -d ';' -f10)

SHORT_LOCATION=$(echo "$LOCATION" | cut -d ',' -f1)

# Display the short status by default, unless the user asks for a full info
# dump.
if [ "$1" = "full" ]; then
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
