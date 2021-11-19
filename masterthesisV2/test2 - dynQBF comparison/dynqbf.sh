#!/bin/bash

# Helping script that solves a .qdimacs file (with path $1) using dynQBF
# and saves the result in a file (with path $2).

echo "start $0."
> $2
../tools/dynqbf-v1.1.1/dynqbf-v1.1.1_x86-64_static -f $1 --print-decomposition >> $2
sleep 1
echo "end $0."

