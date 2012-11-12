#!/bin/bash

FILE=$(dirname $1)/$(basename $1 .py )

TIME="/usr/bin/time -f '%e'"
COMP_T=/tmp/pyc_test_compile_time
RUN_T=/tmp/pyc_test_run_time
ERR_TEST=/tmp/pyc_errtest

if [ ! -f ${FILE}.py ]; then
  echo "no such test: $FILE"
  exit 1
fi

if [ -f ${FILE}.s ]; then
  rm ${FILE}.s
fi
$TIME ./pyc $2 ${FILE}.py 2>$COMP_T
if [ ! -f ${FILE}.s ]; then
  echo "pyc failed to produce output file"
  exit 1
fi

if [ ! "$VERBOSE" = "0" ]; then
  cat ${FILE}.s 
fi

make -s -C ./clib
if [ $? -ne 0 ]; then
  echo "clib make failed"
  exit 1
fi

gcc -m32 -o output ${FILE}.s ./clib/*.o -lm
if [ $? -ne 0 ]; then
  echo "compilation failed"
  exit 1
fi

./output < ${FILE}.in > $ERR_TEST 2>&1
if [ $? -ne 0 ]; then
  echo "program error"
  cat $ERR_TEST
  exit 1
fi

$TIME ./output < ${FILE}.in > ${FILE}.out 2>$RUN_T

python ${FILE}.py < ${FILE}.in > ${FILE}.expected || true

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


