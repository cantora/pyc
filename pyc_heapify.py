from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTVisitor
import pyc_vis
from pyc_log import *
import pyc_gen_name
from pyc_validator import assert_valid
import pyc_localize
from pyc_ir_nodes import *
import ast
import copy

class Heapifier(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Module(self, node):
		heap_vars = {}
		locs = pyc_localize.locals(node)

		self.log(self.depth_fmt("locals: %r" % locs) )

		result = [pyc_vis.visit(self, n, heap_vars, locs) for n in node.body]
		raise Exception("init local heap vars")
		return ast.Module(result)
	
	def visit_Name(self, node, heap_vars, locals):
		if node.id in heap_vars or node.id not in locals:
			heap_vars[node.id] = ("heap_%s" % node.id)
			return astree_to_ir(ast.Subscript(
				value = ast.Name(
					id = heap_vars[node.id],
					ctx = ast.Load()
				),
				slice = ast.Index(value=ast.Num(n=0)),
				ctx = node.ctx.__class__()
			))
		else:
			return ast.Name(
				id = node.id,
				ctx = node.ctx
			)


	def visit_Bloc(self, node, heap_vars, dummy):
		locals = pyc_localizer.locals(node)
		self.log(self.depth_fmt("locals: %r" % locs) )
		prms = pyc_astvisitor.names(node.args)		

		result_body = [pyc_vis.visit(self, n, heap_vars, locals) for n in node.body]

		#pass empty set for locals because none of the fn arg references should be "heapified"
		#because we copy those into new heapified vars before the function body.
		#due to above pyc_vis call, all references to these parameters have been
		#converted to the new heapified version we will initialized
		result_args = pyc_vis.visit(self, node.args, heap_vars, set([]) )

		inits = []
		for name in locals:
			if name not in heap_vars:
				continue

			val = var_ref(name) if name in prms else false_node()
			inits.append(make_assign(
				var_ref(heap_vars[name]),
				astree_to_ir(
					ast.List(
						elts = [val],
						ctx = ast.Load()
					)
				)
			))
	
		return Bloc(
			args = result_args,
			body = inits + result_body
		)

def txform(as_tree):
	v = Heapifier()
	v.log = lambda s: log("Localizer  : %s" % s)
	return pyc_vis.walk(v, as_tree)
