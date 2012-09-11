#!/bin/bash

set -e

FILE=$(dirname $1)/$(basename $1 .py )

./pyc ${FILE}.py 
cat ${FILE}.s 
for i in ./clib/*.c; do 
  bash -c "cd $(dirname $i) && gcc -m32 -c $i"
done

#runtime.o hashtable.o hashtable_utility.o hashtable_itr.o
gcc -m32 -o output ${FILE}.s ./clib/*.o -lm 

