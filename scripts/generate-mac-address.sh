#!/bin/bash
echo -n '00:';for i in {1..4};do printf "%02x:" $((RANDOM%256));done;printf "%02x\n" $((RANDOM%256))
