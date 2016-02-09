#!/bin/bash

files="./test/*"
for filepath in $files; do
  if [ -d $filepath ]; then
    echo $(basename ${filepath})
   python test.py ${filepath} >& log/$(basename ${filepath}).log
  fi
done
