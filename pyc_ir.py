from pyc_astvisitor import ASTTxformer
import pyc_vis
import pyc_parser
from pyc_log import *

import ast

class AstToIRTxformer(ASTTxformer):

	class InvalidSyntax(Exception):
		pass

	class InvalidP1(InvalidSyntax):
		pass

	#bad assumption ^_^
	class BadAss(Exception):
		pass
		
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise InvalidP1("assign expected to have only one target: %r" % node)
		elif not isinstance(node.targets[0], ast.Name):
			raise BadAss("assumbed all targets were names: %r" % node)
		elif not isinstance(node.targets[0].ctx, ast.Store):
			raise BadAss("why isnt the target context store?: %r" % node)
		
		return ast.Assign(
			targets = [pyc_vis.visit(self, node.targets[0])],
			value = pyc_vis.visit(self, node.value)
		)

	def visit_Print(self, node):
		if len(node.values) != 1:
			raise InvalidP1("print expected to have only one arg")
		
		return ast.Print(
			dest = None,
			values = [ pyc_vis.visit(self, node.values[0]) ],
			nl = True
		)

	def visit_Name(self, node):
		name_id = "user_"+node.id
		return ast.Name(
			id = name_id,
			ctx = node.ctx.__class__()
		)

	def visit_IfExp(self, node):
		
		return ast.IfExp(
			test = pyc_vis.visit(self, node.test),
			body = pyc_vis.visit(self, node.body),
			orelse = pyc_vis.visit(self, node.orelse)
		)

	def visit_Call(self, node):
		if node.func.id != "input":
			raise InvalidP1("the only function in p1 is input >_<: %r" % node)
		
		return ast.Call(
			func = ast.Name( id = "input", ctx = ast.Load() ),
			kwargs = None,
			starargs = None
		)




def generate(as_tree):
	v = AstToIRTxformer()
	#v.log = log
	return pyc_vis.walk(v, as_tree)

def print_irtree(tree):
	return pyc_parser.print_astree(tree)

def str(tree):
	return pyc_parser.str(tree)

def dump(tree):
	return ast.dump(tree)
