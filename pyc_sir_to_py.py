from pyc_ir_nodes import *
from pyc_astvisitor import ASTVisitor
import pyc_vis
from pyc_log import log

class SirToPyVisitor(ASTVisitor):

	arg_irnodes = [
		InjectFromBool,
		InjectFromInt,
		InjectFromBig,
		ProjectToInt,
		ProjectToBool,
		ProjectToBig,
		CastBoolToInt,
		CastIntToBool,
		IsTrue
	]

	simple_nodes = {
		ListRef: ["size"],
		DictRef: [],
		ClosureFVS: ["var"],
		Error: ["msg"],
		ast.Return: ["value"],
		Tag: ["arg"]
	}

	def __init__(self, io):
		ASTVisitor.__init__(self)
		self.io = io

	def tab_str(self, **kwargs):
		return "  "*(1 + kwargs["if_depth"])

	def default_accumulator(self):
		return ""

	def default_accumulate(self, current, output):
		if output is None:
			return current

		return current + output

	def default_ast(self, node, *args, **kwargs):
		if node.__class__ not in set([ast.Module]):
			raise Exception("not handled: %r" % ast.dump(node))
		return ""

	def default(self, node, *args, **kwargs):
		if node.__class__ in SirToPyVisitor.arg_irnodes:
			return self.visit_arg_irnode(node, **kwargs)
		elif node.__class__ in SirToPyVisitor.simple_nodes:
			return self.visit_irnode(node, **kwargs)
		else:
			return ASTVisitor.default(self, node, *args, **kwargs)			


	def visit_arg_irnode(self, node, **kwargs):
		return "%s(%s)" % (node.__class__.__name__, pyc_vis.visit(self, node.arg) )

	def visit_Call(self, node, **kwargs):
		return "%s(%s)" % (
			pyc_vis.visit(self, node.func),
			self.format_args(
				[pyc_vis.visit(self, arg) for arg in node.args]
			)
		)

	def visit_Return(self, node, **kwargs):
		print >>self.io, "%sreturn %s" % (
			self.tab_str(**kwargs),
			pyc_vis.visit(self, node.value)
		)

	def visit_irnode(self, node):
		return self.visit_func_like(
			node, 
			[pyc_vis.visit(self, getattr(node, arg)) for arg in SirToPyVisitor.simple_nodes[node.__class__]]
		)

	def visit_func_like(self, node, args):
		klass = node.__class__
		return "%s(%s)" % (klass.__name__, self.format_args(args))

	def format_args(self, args):
		arg_amt = len(args)
		fmt = ", ".join(["%s"]*arg_amt)
		return fmt % tuple(args)
 
	def visit_If(self, node, **kwargs):
		print >>self.io, "%sif (%s):" % (self.tab_str(**kwargs), pyc_vis.visit(self, node.test))

		kwargs["if_depth"] += 1
		for n in node.body:
			pyc_vis.visit(self, n, **kwargs)
		kwargs["if_depth"] -= 1

		print >>self.io, "%selse:" % self.tab_str(**kwargs)
		kwargs["if_depth"] += 1
		for n in node.orelse:
			pyc_vis.visit(self, n, **kwargs)
		kwargs["if_depth"] -= 1

		return ""

	def visit_DoWhile(self, node, **kwargs):
		for n in node.tbody:
			pyc_vis.visit(self, n, **kwargs)

		print >>self.io, "%swhile (%s):" % (self.tab_str(**kwargs), pyc_vis.visit(self, node.test))
	
		kwargs["if_depth"] += 1
		for n in node.wbody:
			pyc_vis.visit(self, n, **kwargs)
		for n in node.tbody:
			pyc_vis.visit(self, n, **kwargs)
		kwargs["if_depth"] -= 1

		return ""

	def visit_Eq(self, node, **kwargs):
		return "=="

	def visit_Compare(self, node):
		return "(%s %s %s)" % (
			pyc_vis.visit(self, node.left),
			pyc_vis.visit(self, node.ops[0]),
			pyc_vis.visit(self, node.comparators[0])
		)

	def visit_BinOp(self, node):
		return "(%s %s %s)" % (
			pyc_vis.visit(self, node.left),
			pyc_vis.visit(self, node.op),
			pyc_vis.visit(self, node.right)
		)

	def visit_UnaryOp(self, node):
		return "%s(%s)" % (
			pyc_vis.visit(self, node.op),
			pyc_vis.visit(self, node.operand)
		)

	def visit_Not(self, node):
		return "not"

	def visit_Add(self, node):
		return "+"

	def visit_Str(self, node, **kwargs):
		return repr(node.s)

	def visit_Print(self, node, **kwargs):
		print >>self.io, "%s%s" % (
			self.tab_str(**kwargs),
			self.visit_func_like(
				node, 
				[pyc_vis.visit(self, n) for n in node.values]
			)
		)

	def visit_CreateClosure(self, node, **kwargs):
		return self.visit_func_like(
			node,
			[
				pyc_vis.visit(self, node.name),
				pyc_vis.visit(self, node.free_vars)
			]
		)
	
	def visit_ClosureCall(self, node, **kwargs):
		return self.visit_func_like(
			node, 
			[pyc_vis.visit(self, node.var)] + \
			[pyc_vis.visit(self, n) for n in node.args]
		)

	def visit_Subscript(self, node):
		return "%s[%s]" % (pyc_vis.visit(self, node.value), pyc_vis.visit(self, node.slice))

	def visit_Index(self, node):
		return pyc_vis.visit(self, node.value)

	def visit_Num(self, node):
		return str(node.n)

	def visit_Module(self, node):
		return self.default(node, **{"if_depth": 0})

	def visit_BlocDef(self, node, **kwargs):
		print >>self.io, "\ndef %s(%s):" % (
			node.name, 
			self.format_args([n.id for n in node.params])
		)
		for n in node.body:
			pyc_vis.visit(self, n, **kwargs)

		return ""

	def visit_Assign(self, node, **kwargs):
		print >>self.io, "%s%s = %s" % (
			self.tab_str(**kwargs),
			pyc_vis.visit(self, node.targets[0]),
			pyc_vis.visit(self, node.value)
		)
		return ""

	def visit_Name(self, node, **kwargs):
		return node.id
		
	def visit_USub(self, node, **kwargs):
		return "-"

	def default_non_ast(self, obj, *args, **kwargs):		
		return str(obj)
		

def generate(sir_mod, io):
	v = SirToPyVisitor(io)
	#v.log = lambda s: log("SirToPy : %s" % s)
	pyc_vis.walk(v, sir_mod)