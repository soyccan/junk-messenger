#!/bin/sh
if [ -e build ]; then
    rm -rf build
fi
mkdir -p build
cd build
cmake ..
cmake --build .
