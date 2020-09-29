#!/bin/bash
###########################################################################
# Author: Scott MacDonald
#
# Downloads an imgur gallery to the current directory
# Inspiration from http://www.reddit.com/r/ScriptSwap/comments/qi5wv/small_script_to_download_imgur_album/
###########################################################################
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 http://path/to/imgur/album"
    exit 1
fi

source=$1

echo "Fetching imgur gallery..."
urls=`curl "$source" -s | grep 'alt="" src=' | sed 's/.*src="\(.*\)".*/\1/g;s/s\./\./g'`

echo "Saving individual images..."
for i in $urls
do
    echo Downloading: $i
    curl -O -s $i
done
