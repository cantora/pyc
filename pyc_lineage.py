from pyc_vis import VisTracer
from pyc_log import *
import pyc_vis

import ast
from pyc_astvisitor import ASTVisitor

class Bequeather(ASTVisitor):
	
	def __init__(self, root, parent, cpass):
		ASTVisitor.__init__(self)
		self.root = root
		self.parent = parent
		self.cpass = cpass

	def default_ast(self, node, *args, **kwargs):
		node.parent = self.parent
		node.cpass = self.cpass

	def default_non_ast(self, node, *args, **kwargs):
		return self.default_accumulator()

	def default(self, node, *args, **kwargs):
		if node != self.root and hasattr(node, 'parent'):
			return self.default_accumulator()

		return ASTVisitor.default(self, node, *args, **kwargs)
		
class Tracer(VisTracer):

	def __init__(self):
		VisTracer.__init__(self)

	def trace(self, result, instance, prefix, default, value, *args, **kwargs):
		node = args[0]
		if not isinstance(node, ast.AST):
			raise Exception("expected instance of AST")

		vis_klass = instance.__class__.__name__ 
		if vis_klass == 'IRTreeSimplifier':
			self.track_ir_vis(node, result, vis_klass)
		elif vis_klass == 'Converter':
			self.track_closure_vis(node, result, vis_klass)
		else:
			self.track(node, result, vis_klass)
	
	def track(self, node, result, cpass):
		v = Bequeather(result, node, cpass)
		v.log = lambda s: log("Bequeather : %s" % s)
		pyc_vis.walk(v, result)

	def track_closure_vis(self, node, result, cpass):
		child = result[0]
		if not isinstance(child, ast.AST):
			raise Exception("expecting AST as 1st part of closure tuple result")

		self.track(node, child, cpass)

	def track_ir_vis(self, node, result, cpass):
		(name, l) = result
		if not isinstance(l, list):
			raise Exception("expecting list as second part of ir vis result: %r" % (l) )

		if not name is None:
			self.track(node, name, cpass)
		
		for n in l:
			self.track(node, n, cpass)

class GraphVizVisitor(ASTVisitor):
	
	def __init__(self, io):
		ASTVisitor.__init__(self)
		self.io = io

	def default_non_ast(self, node, *args, **kwargs):
		return set([])

	def default_ast(self, node, *args, **kwargs):
		if not hasattr(node, 'parent'):
			raise Exception("orphaned node: %r" % (node))

		self.lineage_edges(node, node.parent)

	def namespace(self, node):
		return node.cpass if hasattr(node, 'cpass') else 'parse'

	def lineage_edges(self, node, parent):
		print >>self.io, "\t%s-%s -> %s-%s" % (
			self.namespace(parent),
			parent.__class__.__name__,
			self.namespace(node),
			node.__class__.__name__
		)
		
		if hasattr(parent, 'parent'):
			self.lineage_edges(parent, parent.parent)

def graph(as_tree, io):
	v = GraphVizVisitor(io)
	v.log = lambda s: log("GraphVizVisitor : %s" % s)
	
	return pyc_vis.walk(v, as_tree)

