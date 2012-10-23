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
import pyc_ir
import ast
import copy

class FreeVarFinder(ASTSearcher):
	
	def __init__(self, root):
		ASTSearcher.__init__(self)
		self.root = root

	def visit_Name(self, node):
		if node.id[0:4] == "heap":
			self.log(self.depth_fmt("  free var => %s" % node.id))
			return set([node.id])
		
		return set([])

	def visit_Bloc(self, node):
		if self.root != node:
			return set([])
		else:
			return (
				pyc_vis.visit(self, node.args)
					| pyc_vis.visit(self, node.body)
			)




class Converter(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)

	def default_accumulator(self):
		return {"defs": [], "free_vars": set([])}

	def default_accumulate(self, current, output):
		(node, d) = output
		new_d = {
			"defs": current["defs"] + output["defs"],
			"free_vars": current["free_vars"] | output["free_vars"]
		}

		return (node, new_d)

	def visit_Bloc(self, node):
		bname = pyc_gen_name.new("bloc")
		
		(def_node, d) = pyc_vis.visit(
			self,
			BlocDef(
				name = bname,
				body = node.body,
				params = pyc_vis.visit(node.args)
			)
		)
	
		locals = pyc_localize.locals(node)
		#just generate the names that would be used IF the param were on heap
		#cause we only are subtracting out of the free vars set
		params = [pyc_heapify.heap_name(x) for x in pyc_astvisitor.names(node.args)]
		d["free_vars"] = d["free_vars"] - locals - params

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

		return (
			InjectToBig(arg=CreateClosure(
				name = bname,
				free_vars = [var_ref(x) for x in def_node.fvs]
			)),
			d
		)

	def visit_Call(self, node):
		
		(func_node, d) = pyc_vis.visit(self, node.func)
		arg_nodes = []
		for a in node.args:
			(a_node, a_d) = pyc_vis.visit(self, a)
			arg_nodes.append(a_node)
			d = self.default_accumulate(d, a_d)

		lname = pyc_gen_name.new("closurecall")
		return (
			Let(
				name = var_ref(lname),
				rhs = func_node,
				ClosureCall(
					var = var_ref(lname),
					args = [ClosureFVS(var = var_ref(lname))] + arg_nodes
				)
			),
			d
		)

def txform(as_tree):
	v = Converter()
	v.log = lambda s: log("Converter : %s" % s)
	return pyc_vis.walk(v, as_tree)
