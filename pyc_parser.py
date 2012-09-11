#!/usr/bin/env python

#import compiler
#def parse(src):
	#return compiler.parse(src)

import pyc_ply_parser
def parse(src):
	return pyc_ply_parser.parse(src)