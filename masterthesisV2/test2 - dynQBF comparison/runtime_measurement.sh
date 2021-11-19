#!/bin/bash

# Helping script that runs dynqbf $2 times on a .qdimacs file (with path $1) with varying seed.

echo "start $0."
echo "0/$2"
for i in $(seq 1 $2); do
    ../tools/dynqbf-v1.1.1/dynqbf-v1.1.1_x86-64_static -f $1 > /dev/null
    echo "$i/$2"
done
echo "end $0."

