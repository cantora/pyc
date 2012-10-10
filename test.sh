#!/bin/bash

set -e
FILE=$(dirname $1)/$(basename $1 .py )

TIME="/usr/bin/time -f '%e'"
COMP_T=/tmp/pyc_test_compile_time
RUN_T=/tmp/pyc_test_run_time

$TIME ./pyc ${FILE}.py 2>$COMP_T
if [ ! "$VERBOSE" = "0" ]; then
  cat ${FILE}.s 
fi

make -s -C ./clib

gcc -m32 -o output ${FILE}.s ./clib/*.o -lm
$TIME ./output < ${FILE}.in > ${FILE}.out 2>$RUN_T
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

TIME_RESULT="compile=$(cat $COMP_T) run=$(cat $RUN_T)"
FNAME=$(basename $FILE)
diff ${FILE}.out ${FILE}.expected
if [ $? == 0 ]; then
  echo "[x] $TIME_RESULT $FNAME"
else
  echo "[-] $TIME_RESULT $FNAME"
fi


