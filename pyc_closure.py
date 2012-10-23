from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTSearcher
import pyc_astvisitor
import pyc_vis
from pyc_log import *
import pyc_gen_name
from pyc_validator import assert_valid
import pyc_localize
from pyc_ir_nodes import *
import pyc_constants
import pyc_heapify
import pyc_ir
import ast
import copy

class Converter(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)

	def default_accumulator(self):
		return {
			"defs": [], 
			"free_vars": set([]), 
			"bloc_vars": set([])
		}

	def default_accumulate(self, current, output):
		(node, d) = output
		new_d = {
			"defs": current["defs"] + d["defs"],
			"free_vars": current["free_vars"] | d["free_vars"],
			"bloc_vars": current["bloc_vars"] | d["bloc_vars"]
		}

		return (node, new_d)

	def visit_Name(self, node):
		d = self.default_accumulator()
		if not node.id in pyc_constants.internal_names \
				and not node.id[0:2] == "ir":
			d["bloc_vars"] = set([node.id])

		return (
			copy_name(node),
			d
		)

	def visit_Module(self, node):
		main_body = []

		d = self.default_accumulator()
		for n in node.body:
			output = pyc_vis.visit(self, n) 
			(out_n, d) = self.default_accumulate(d, output)
			main_body.append(out_n)

		return (
			BlocDef(
				name = "main",
				params = ast.arguments(
					args = [],
					kwarg = None,
					vararg = None
				),
				body = main_body
			),
			d
		)

	def visit_Bloc(self, node):
		bname = pyc_gen_name.new("bloc")
		
		(def_node, d) = pyc_vis.visit(
			self,
			BlocDef(
				name = bname,
				body = node.body,
				params = node.args
			)
		)

		self.log(self.depth_fmt("bloc vars: %r" % d["bloc_vars"]))
		locals = pyc_localize.locals(node)
		self.log(self.depth_fmt("locals: %r" % locals))

		#!!dont think we need any of this because converted params should
		#!!show up as locals because they are initialized
		#just generate the names that would be used IF the param were on heap
		#cause we only are subtracting out of the free vars set
		#params = set([pyc_heapify.heap_name(x) for x in pyc_astvisitor.names(node.args)])
		#self.log(self.depth_fmt("params as heap vars: %r" % params))
		d["free_vars"] = (d["free_vars"] | d["bloc_vars"]) - locals
		self.log(self.depth_fmt("free vars: %r" % d["free_vars"]))

		def_node.fvs = list(d["free_vars"])
		fvs_inits = []
		for i in range(0, len(def_node.fvs)):
			fvs_inits.append(pyc_ir.astree_to_ir(
				make_assign(
					var_set(def_node.fvs[i]),
					make_subn("fvs", ast.Load, i)	
				)
			))
		def_node.body = fvs_inits + def_node.body
		d["defs"].append(def_node)
		d["bloc_vars"] = set([])

		return (
			InjectFromBig(arg=CreateClosure(
				name = bname,
				free_vars = [var_ref(x) for x in def_node.fvs]
			)),
			d
		)

	def visit_Call(self, node):
		
		(func_node, d) = pyc_vis.visit(self, node.func)
		arg_nodes = []
		for a in node.args:
			output = pyc_vis.visit(self, a)
			(a_node, d) = self.default_accumulate(d, output)
			arg_nodes.append(a_node)

		lname = pyc_gen_name.new("closurecall")
		return (
			Let(
				name = var_ref(lname),
				rhs = func_node,
				body = ClosureCall(
					var = var_ref(lname),
					args = [ClosureFVS(var = var_ref(lname))] + arg_nodes
				)
			),
			d
		)

def convert(as_tree):
	v = Converter()
	v.log = lambda s: log("Converter : %s" % s)
	(conv_tree, d) = pyc_vis.walk(v, as_tree)
	
	return ast.Module(
		body = [conv_tree] + d["defs"]
	)
