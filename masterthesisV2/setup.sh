#!/bin/bash

# setup file

cd tools
unzip dynqbf-v1.1.1-x86_64-static
git clone https://github.com/kit-algo/flow-cutter-pace17.git
cd flow-cutter-pace17
./build.sh
cd ..
git clone https://github.com/lonsing/qratpreplus.git
cd qratpreplus
make
cd ../..
