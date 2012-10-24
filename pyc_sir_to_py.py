from pyc_ir_nodes import *
from pyc_astvisitor import ASTVisitor
import pyc_vis
from pyc_log import log

class SirToPyVisitor(ASTVisitor):

	arg_irnodes = [
		InjectFromBool,
		InjectFromInt,
		InjectFromBig
	]

	irnodes = {
		ListRef: ["size"],
		CreateClosure: ["name", "free_vars"]
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
		self.log(self.depth_fmt("not handled: %r" % node.__class__))
		return ""

	def default(self, node, *args, **kwargs):
		if node.__class__ in SirToPyVisitor.arg_irnodes:
			return self.visit_arg_irnode(node, **kwargs)
		elif node.__class__ in SirToPyVisitor.irnodes:
			return self.visit_irnode(node, **kwargs)
		else:
			return ASTVisitor.default(self, node, *args, **kwargs)			


	def visit_arg_irnode(self, node, **kwargs):
		return "%s(%s)" % (node.__class__.__name__, pyc_vis.visit(self, node.arg) )

	def visit_irnode(self, node):
		return self.visit_func_like(
			node, 
			[pyc_vis.visit(self, getattr(node, arg)) for arg in SirToPyVisitor.irnodes[node.__class__]]
		)

	def visit_func_like(self, node, args):
		klass = node.__class__
		fmt = "%s("
		arg_amt = len(args)
		fmt += ",".join(["%s"]*arg_amt)
		fmt += ")"
		arr = [klass.__name__] + args
		return fmt % tuple(arr)

	def visit_Print(self, node, **kwargs):
		print >>self.io, self.visit_func_like(
			node, 
			[pyc_vis.visit(self, n) for n in node.values]
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
		print >>self.io, "def %s():\n" % node.name
		for n in node.body:
			pyc_vis.visit(self, n, **kwargs)

		return ""

	def visit_Assign(self, node, **kwargs):
		print >>self.io, "%s%s = %s\n" % (
			self.tab_str(**kwargs),
			pyc_vis.visit(self, node.targets[0]),
			pyc_vis.visit(self, node.value)
		)
		return ""

	def visit_Name(self, node, **kwargs):
		return node.id
		
	def default_non_ast(self, obj, *args, **kwargs):		
		return str(obj)
		

def generate(sir_mod, io):
	v = SirToPyVisitor(io)
	v.log = lambda s: log("SirToPy : %s" % s)
	pyc_vis.walk(v, sir_mod)