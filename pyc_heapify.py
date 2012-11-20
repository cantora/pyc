from pyc_astvisitor import ASTTxformer
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

class Lamb(IRNode):
	def __init__(self, **kwargs):
		IRNode.__init__(
			self,
			tuple(['lamb']),
			**kwargs
		)		

	
class Heapifier(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)
		self.lamb_nodes = []

	def visit_Module(self, node):
		heap_vars = {}
		locs = pyc_localize.locals(node)
		env = set(["True", "False"])
		locs = locs | env

		self.log("locals: %r" % locs)

		bool_inits = [
			make_assign(var_set('False'), InjectFromBool(arg=ast.Num(n=0)) ),
			make_assign(var_set('True'), InjectFromBool(arg=ast.Num(n=1)) )
		]

		result = [pyc_vis.visit(self, n, heap_vars, locs) for n in node.body]
		inits = self.init_local_heap_vars(locs, env, heap_vars)

		self.log("heapify result: %r" % heap_vars)
		self.patch_lamb_nodes()		
		return ast.Module(
			body = bool_inits + inits + result
		)
	
	def heapify_name(self, node, new_name):
		return pyc_ir.txform(make_subn(new_name, node.ctx.__class__, 0), tracer = self.tracer)

	def heapify_switch(self, node, heap_vars):
		if node.id in heap_vars:
			return self.heapify_name(node, heap_vars[node.id])
		else:
			return copy_name(node)	

	def visit_Name(self, node, heap_vars, locals):
		if node.id in pyc_constants.internal_names \
				or node.id[0:2] == "ir":
			return copy_name(node)
		elif node.id in heap_vars or node.id not in locals:
			heap_vars[node.id] = heap_name(node.id)
			self.log(self.depth_fmt("heap: %s" % node.id))
			return self.heapify_name(node, heap_vars[node.id])
		else:
			self.log(self.depth_fmt("defer: %s" % node.id))
			exp = NameWrap(value=Lamb(
				lamb = lambda : self.heapify_switch(node, heap_vars)
			))
			self.lamb_nodes.append(exp)
			#we will edit this node later by invoking the lambda
			return exp


	def init_heap_var(self, hv, value):
		return make_assign(
			var_set(hv),
			pyc_ir.txform(
				ast.List(
					elts = [value],
					ctx = ast.Load()
				),
				tracer = self.tracer
			)
		)

	def init_local_heap_vars(self, locals, params, heap_vars):
		inits = []
		for name in locals:
			if name not in heap_vars:
				continue
	
			val = var_ref(name) if name in params else false_node()
			inits.append(self.init_heap_var(heap_vars[name], val))

		return inits

	def visit_Bloc(self, node, heap_vars, dummy):
		locals = pyc_localize.locals(node)
		self.log(self.depth_fmt("locals: %r" % locals) )
		prms = pyc_astvisitor.names(node.args)		
		self.log(self.depth_fmt("params: %r" % prms) )

		result_body = [
			pyc_vis.visit(self, n, heap_vars, locals) for n in node.body
		]

		#pass all params for locals and empty heap_vars 
		#because none of the fn arg references should be "heapified"
		#because we copy those into new heapified vars before the function body.
		#due to above pyc_vis call, all references to these parameters will
		#have been converted to the new heapified version we will initialize
		#after we patch the lambda nodes
		result_args = pyc_vis.visit(self, node.args, {}, prms )

		inits = self.init_local_heap_vars(locals, prms, heap_vars)
	
		return Bloc(
			args = result_args,
			body = inits + result_body
		)

	def patch_lamb_nodes(self):
		log("patch lamb nodes:")
		for expr in self.lamb_nodes:
			expr.value = expr.value.lamb()
			log("  ->%s" % ast.dump(expr.value))


def heap_name(name):
	return ("heap_%s" % name)

def txform(as_tree, **kwargs):
	v = Heapifier()
	v.log = lambda s: log("Heapifier  : %s" % s)
	if 'tracer' in kwargs:
		v.tracer = kwargs['tracer']

	return pyc_vis.walk(v, as_tree)
