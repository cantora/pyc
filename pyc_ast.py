from pyc_log import *
import pyc_gen_name
import pyc_vis
import pyc_ir
import ast

import copy

"""
def to_str_fmt_func(node, user, depth):
	val = node.__class__.__name__
	if len(node.getChildNodes()) == 0:
		val = repr(node)

	user.append( "%s%s" % (' '*depth, val) )


def str(as_tree):
	lines = []

	traverse(as_tree, to_str_fmt_func, lines)
	return "\n".join(lines)

def traverse(node, func, user):
	_traverse(node, func, user)

def _traverse(node, func, user, depth=0):
	func(node, user, depth)
	for n in node.getChildNodes():
		_traverse(n, func, user, depth+1)

"""

class IRTreeSimplifier(pyc_vis.Visitor):
	
	def __init__(self):
		pyc_vis.Visitor.__init__(self)

	def var_ref(self, name):
		return ast.Name( id = name, ctx = ast.Load() )

	def visit_Module(self, node):
		sir_body = []
		for n in node.body:
			(name, sir_list) = pyc_vis.visit(self, n)
			sir_body += sir_list

		return ast.Module(body = sir_body)

	def visit_Assign(self, node):	
		(name, sir_list) = pyc_vis.visit(self, node.value)

		sir_list.append(ast.Assign(
			targets = [copy.deepcopy(node.targets[0])],
			value = name
		))
		return (None, sir_list)

	def visit_BinOp(self, node):
		(l_name, l_sir_list) = pyc_vis.visit(self, node.left)
		(r_name, r_sir_list) = pyc_vis.visit(self, node.right)
		
		result_name = pyc_gen_name.new()
		l_sir_list += r_sir_list
		l_sir_list.append(ast.Assign(
			targets = [self.var_ref(result_name)],
			value = ast.BinOp( 
				left = l_name, 
				op = node.op.__class__(),
				right = r_name
			)
		))

		return (self.var_ref(result_name), l_sir_list)

	def visit_UnaryOp(self, node):
		(name, sir_list) = pyc_vis.visit(self, node.operand)
		result_name = pyc_gen_name.new()
		sir_list.append(ast.Assign(
			targets = [self.var_ref(result_name)],
			value = ast.UnaryOp(
				op = node.op.__class__(),
				operand = name
			)
		))

		return (self.var_ref(result_name), sir_list)

	def visit_Call(self, node):
		if not node.kwargs is None \
				or not node.starargs is None \
				or hasattr(node, 'keywords'):
			raise Exception("havent implemented kwargs or starargs")

		fn_args = []
		sir_list = []

		if hasattr(node, 'args'):
			for n in node.args:
				(name, arg_sir_list) = pyc_vis.visit(self, n)
				fn_args.append( name )
				sir_list += arg_sir_list
		
		result_name = pyc_gen_name.new()
		sir_list.append(ast.Assign(
			targets = [self.var_ref(result_name)],
			value = ast.Call(
				func = copy.deepcopy(node.func), 
				args = fn_args
			)
		))

		return (self.var_ref(result_name), sir_list)

	def visit_Name(self, node):
		return (self.var_ref(node.id), [] )

	def make_print(self, args):
		return ast.Print(dest=None, values=args, nl=True)

	def visit_Print(self, node):
		nlen = len(node.values)
		if nlen == 0 :
			return (None, [self.make_print([])])
		elif nlen == 1 :
			(name, sir_list) = pyc_vis.visit(self, node.values[0])
			sir_list.append(self.make_print([name]))
			return (None, sir_list)

		raise Exception("print statements may only print one item (%d)" % nlen)

	def visit_Num(self, node):
		return (ast.Num(n=node.n), [])
		
	def visit_Expr(self, node):
		(dummy, sir_list) = pyc_vis.visit(self, node.value)
		return (None, sir_list)
	
#convert an abstract syntax tree into a list of
#simple IR statements
def simple_ir(ir_tree):
	return pyc_vis.walk(IRTreeSimplifier(), ir_tree)




