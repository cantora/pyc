from pyc_vis import VisTracer
from pyc_log import *

import ast

class Tracer(VisTracer):

	def __init__(self):
		VisTracer.__init__(self)
		
	def trace(self, result, instance, prefix, default, value, *args, **kwargs):
		node = args[0]
		if not isinstance(node, ast.AST):
			raise Exception("expected instance of AST")

		vis_klass = instance.__class__.__name__ 
		if vis_klass == 'IRTreeSimplifier':
			self.track_ir_vis(node, result)
		elif vis_klass == 'Converter':
			self.track_closure_vis(node, result)
		else:
			self.track(node, result)
	
	def track(self, node, result):
		result.parent = node

	def track_closure_vis(self, node, result):
		child = result[0]
		if not isinstance(child, ast.AST):
			raise Exception("expecting AST as 1st part of closure tuple result")

		self.track(node, child)

	def track_ir_vis(self, node, result):
		(name, l) = result
		if not isinstance(l, list):
			raise Exception("expecting list as second part of ir vis result: %r" % (l) )

		if not name is None:
			self.track(node, name)
		
		for n in l:
			self.track(node, n)

