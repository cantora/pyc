#!/bin/bash

FILE=$(dirname $1)/$(basename $1 .py )

TIME="/usr/bin/time -f '%e'"
COMP_T=/tmp/pyc_test_compile_time

$TIME ./pyc --IR -n ${FILE}.py 2>$COMP_T
if [ ! "$VERBOSE" = "0" ]; then
  cat ${FILE}.txt
fi

python -c '
import sys
import re
with open(sys.argv[1], "r") as f:
  i = 1
  for stmt in f:
    stmt = stmt.strip()
    m = re.match(r".*#(\d+)", stmt)
    if not m:
      print "failed to find lineno at line %d in stmt: %s" % (i, stmt)
      exit(1)

    code_lineno = int(m.group(1))
    if code_lineno != i:
      print "invalid lineno at line %d: %d" % (i, code_lineno)
      exit(1)
    i += 1

  exit(0)
' ${FILE}.txt
RESULT=$?

TIME_RESULT="compile=$(cat $COMP_T)"
FNAME=$(basename $FILE)
if [ $RESULT == 0 ]; then
  echo "[x] $TIME_RESULT $FNAME"
else
  echo "[-] $TIME_RESULT $FNAME"
fi


