#!/bin/bash

# Helping script that processes a .qdimacs file (with path $1) using QRATPre+
# and saves the result in a .qdimacs file (with path $2).

> $2
../tools/qratpreplus/qratpre+ --print-formula $1 >> $2
sleep 1

