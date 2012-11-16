from pyc_vis import VisTracer
from pyc_log import *
import pyc_vis

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
			self.track_ir_vis(node, result, vis_klass)
		elif vis_klass == 'Converter':
			self.track_closure_vis(node, result, vis_klass)
		else:
			self.track(node, result, vis_klass)
	
	def track(self, node, result, cpass):
		result.parent = node
		result.cpass = cpass

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

from pyc_astvisitor import ASTSearcher

class GraphVizVisitor(ASTSearcher):
	
	def __init__(self, io):
		ASTSearcher.__init__(self)
		self.io = io

	def default_ast(self, node, *args, **kwargs):
		if not hasattr(node, 'parent'):
			return #raise Exception("orphaned node: %r" % (node))

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

