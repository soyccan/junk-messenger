#!/bin/sh
conda env export -n junk-messenger \
    | sed -E 's/=[^=]*$//g' \
    | grep -v prefix \
    | tee env.yml