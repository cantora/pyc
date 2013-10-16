# Copyright 2013 anthony cantor
# This file is part of pyc.
# 
# pyc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#  
# pyc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#  
# You should have received a copy of the GNU General Public License
# along with pyc.  If not, see <http://www.gnu.org/licenses/>.
import ast
import StringIO
import sys
import pyc_vis
import pyc_lineage

from pyc_astvisitor import ASTVisitor
from pyc_astvisitor import ASTTxformer

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
		
		val = "%s():%d" % (node.__class__.__name__, pyc_lineage.src_lineno(node) )

		print >>self.io, self.format(self.depth, kwargs.get("field", ""), val)

	def default_non_ast(self, obj, *args, **kwargs):		
		print >>self.io, self.format(self.depth, kwargs.get("field", ""), repr(obj) )

class SrcLineFixer(ASTTxformer):
	
	def default(self, node, lineno):
		new_lineno = node.lineno if hasattr(node, 'lineno') else lineno
		result = ASTTxformer.default(self, node, new_lineno)
		result.lineno = new_lineno

		return result

def fix_source_lines(node):
	v = SrcLineFixer()
	return pyc_vis.walk(v, node, 0)

def parse(src):
	result = ast.parse(src)
	return fix_source_lines(result)

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

