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
import pyc_lineage

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
				params = [],
				body = main_body
			),
			d
		)

	def visit_Bloc(self, node):
		bname = pyc_gen_name.new("bloc")
		
		new_bd = BlocDef(
			name = bname,
			body = node.body,
			params = [var_ref("fvs")] + node.args.args
		)
		pyc_lineage.bequeath_lineage(node, new_bd, self.__class__.__name__)

		(def_node, d) = pyc_vis.visit(
			self,
			new_bd
		)

		self.log(self.depth_fmt("bloc vars: %r" % d["bloc_vars"]))
		locals = pyc_localize.locals(node)
		self.log(self.depth_fmt("locals: %r" % locals))

		#note: the params which were heapified will have their normal
		#name in this params set, and their heapified versions are initialized
		#as a local to the value of the non-heap param
		params = set(pyc_astvisitor.names(node.args)) | set(["fvs"])
		self.log(self.depth_fmt("params: %r" % params))
		d["free_vars"] = (d["free_vars"] | d["bloc_vars"]) - locals - params
		self.log(self.depth_fmt("free vars: %r" % d["free_vars"]))

		def_node.fvs = list(d["free_vars"])
		fvs_inits = []
		for i in range(0, len(def_node.fvs)):
			fvs_inits.append(pyc_ir.txform(
				make_assign(
					var_set(def_node.fvs[i]),
					#is it ok to use a canonical name for fvs?
					make_subn("fvs", ast.Load, i) 
				),
				tracer = self.tracer
			))

		def_node.body = fvs_inits + def_node.body
		d["defs"].append(def_node)
		d["bloc_vars"] = set([])

		return (
			InjectFromBig(arg=CreateClosure(
				name = bname,
				free_vars = pyc_ir.txform(
					ast.List(
						elts = [var_ref(x) for x in def_node.fvs],
						ctx = ast.Load()
					),
					tracer=self.tracer
				)
			)),
			d
		)

	def visit_UserCall(self, node):
		
		(func_node, d) = pyc_vis.visit(self, node.func)
		arg_nodes = []
		for a in node.args:
			output = pyc_vis.visit(self, a)
			(a_node, d) = self.default_accumulate(d, output)
			arg_nodes.append(a_node)

		lname = pyc_gen_name.new("closurecall")
		return (
			Let(
				name = var_set(lname),
				rhs = func_node,
				body = ClosureCall(
					var = var_ref(lname),
					args = [ClosureFVS(var = var_ref(lname))] + arg_nodes
				)
			),
			d
		)

def txform(as_tree, **kwargs):
	v = Converter()
	v.log = lambda s: log("Converter : %s" % s)
	if 'tracer' in kwargs:
		v.tracer = kwargs['tracer']

	(conv_tree, d) = pyc_vis.walk(v, as_tree)
	
	result = ast.Module(
		body = [conv_tree] + d["defs"]
	)

	result.parent = as_tree.parent
	result.cpass = v.__class__.__name__

	return result
