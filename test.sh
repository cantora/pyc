#!/bin/bash

FILE=$(dirname $1)/$(basename $1 .py )
./pyc ${FILE}.py && cat ${FILE}.s && { for i in *.c; do gcc -m32 -c $i; done; } && gcc -m32 -o output ${FILE}.s runtime.o hashtable.o hashtable_utility.o hashtable_itr.o -lm && ./output < ${FILE}.in > ${FILE}.out && python ${FILE}.py < ${FILE}.in > ${FILE}.expected && diff ${FILE}.out ${FILE}.expected

if [ $? == 0 ]; then
  echo "test passed"
else
  echo "test failed"
fi

