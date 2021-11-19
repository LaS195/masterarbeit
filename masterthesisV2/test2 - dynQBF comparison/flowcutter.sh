#!/bin/bash

# Helping script that calculates a tree decomposition from a .gr file (with path $1) using flowcutter
# and saves the result in a .gr file (with path $2). flowcutter gets a certain time for this ($3, in seconds).

> $2
../tools/flow-cutter-pace17/flow_cutter_pace17 $1 >> $2 &
sleep $3
kill "$!"
sleep 1
