#!/bin/bash

set -e
FILE=$(dirname $1)/$(basename $1 .py )

./pyc ${FILE}.py 
if [ ! "$VERBOSE" = "0" ]; then
  cat ${FILE}.s 
fi

make -s -C ./clib

gcc -m32 -o output ${FILE}.s ./clib/*.o -lm
./output < ${FILE}.in > ${FILE}.out 
python ${FILE}.py < ${FILE}.in > ${FILE}.expected || true

set +e
if [ ! "$VERBOSE" = "0" ]; then
  echo "output:"
  cat ${FILE}.out
  echo "#####################"
  echo "expected:"
  cat ${FILE}.expected
  echo "#####################"
  echo "out vs expected"
fi

if [ ! "$VERBOSE" = "0" ]; then
  diff ${FILE}.out ${FILE}.expected
  if [ $? == 0 ]; then
    echo "test passed"
  else
    echo "test failed"
  fi
else
  diff ${FILE}.out ${FILE}.expected
fi

