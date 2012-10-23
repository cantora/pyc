#!/usr/bin/env python

import ast
import StringIO
import sys
import pyc_vis

from pyc_astvisitor import ASTVisitor

class PrintASTVisitor(ASTVisitor):
	
	def __init__(self, io):
		ASTVisitor.__init__(self)
		self.io = io
		self.pass_fields = True

	def format(self, depth, field, val):
		fmt = "%s%s"
		fmt += (":" if field != '' else '')
		fmt += "%s"
		return fmt % (" "*depth, field, val)

	def default_ast(self, node, *args, **kwargs):
		val = "%s()" % node.__class__.__name__

		print >>self.io, self.format(self.depth, kwargs.get("field", ""), val)

	def default_non_ast(self, obj, *args, **kwargs):		
		print >>self.io, self.format(self.depth, kwargs.get("field", ""), repr(obj) )


def parse(src):
	return ast.parse(src)

def tree_to_str(astree):
	s = StringIO.StringIO()
	v = PrintASTVisitor(s)	
	pyc_vis.walk(v, astree)
	return v.io.getvalue()

def print_astree(astree):
	v = PrintASTVisitor(sys.stdout)
	pyc_vis.walk(v, astree)

def dump(astree):
	return ast.dump(astree)

