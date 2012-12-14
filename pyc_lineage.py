from pyc_vis import VisTracer
from pyc_log import *
import pyc_vis
import pyc_gen_name
import pyc_sir_to_py
import pyc_ir_nodes
import pyc_parser
from pyc_astvisitor import ASTVisitor

import ast
import StringIO
import string

class Bequeather(ASTVisitor):
	
	def __init__(self, root, parent, cpass):
		ASTVisitor.__init__(self)
		self.root = root
		self.parent = parent
		self.cpass = cpass

	def default_ast(self, node, *args, **kwargs):
		if hasattr(node, 'parent'):
			raise Exception("attempted to bequeath to a node with a parent")

		#self.log("bequeath!")
		node.parent = self.parent
		node.cpass = self.cpass

	def default_non_ast(self, node, *args, **kwargs):
		return self.default_accumulator()

	def default(self, node, *args, **kwargs):
		if hasattr(node, 'parent'):
			#self.log("node already has parent: (%s)%s" % (
			#	str(node.parent.lineno) if hasattr(node.parent, 'lineno') else '?',
			#	ast.dump(node.parent)
			#))
			return self.default_accumulator()

		return ASTVisitor.default(self, node, *args, **kwargs)

def bequeath_lineage(old_node, new_node, cpass):
	v = Bequeather(new_node, old_node, cpass)
	v.log = lambda s: log("Bequeather : %s" % s)
	#log("bequeath parent: (%s)%s" % (
	#	src_lineno(old_node),
	#	ast.dump(old_node)
	#))
	pyc_vis.walk(v, new_node)
	#log("bequeath result: (%s)%s" % (
	#	src_lineno(new_node),
	#	ast.dump(new_node)
	#))

class Tracer(VisTracer):

	def __init__(self):
		VisTracer.__init__(self)

	def trace(self, result, instance, prefix, default, value, *args, **kwargs):
		node = args[0]
		if not isinstance(node, ast.AST):
			raise Exception("expected instance of AST")

		vis_klass = instance.__class__.__name__ 
		if vis_klass == 'IRTreeSimplifier':
			self.track_sir_vis(node, result, vis_klass)
		elif vis_klass == 'Converter':
			self.track_closure_vis(node, result, vis_klass)
		else:
			self.track(node, result, vis_klass)
	
	def track(self, node, result, cpass):
		bequeath_lineage(node, result, cpass)

	def track_closure_vis(self, node, result, cpass):
		child = result[0]
		if not isinstance(child, ast.AST):
			raise Exception("expecting AST as 1st part of closure tuple result")

		self.track(node, child, cpass)

	def track_sir_vis(self, node, result, cpass):
		(name, l) = result
		if not isinstance(l, list):
			raise Exception("expecting list as second part of ir vis result: %r" % (l) )

		if not name is None:
			self.track(node, name, cpass)
		
		for n in l:
			self.track(node, n, cpass)
			#log("post track result:")
			#log(pyc_parser.tree_to_str(n))


def src_lineno(node):
	n = node
	lineage = [n]
	while(hasattr(n, 'parent')):
		n = n.parent
		lineage.append(n)

	if not hasattr(n, 'lineno') or n.lineno is None:
		raise Exception("could not find origin for node: %s" % (
			"\n".join(["%s:%s" % (getattr(x, 'cpass', 'None'), pyc_parser.dump(x)) for x in lineage])
		))
		#return 0
	
	return n.lineno

def graph(bloc_list, io):
	for bloc in bloc_list:
		sir_nodes = {}

		prev_sir = None
		offset = "    |"
		for i in bloc.insns:
			if i.origin is None:
				raise Exception("inst %r is None" % i)

			if i.origin not in sir_nodes:
				sir_str = StringIO.StringIO()
				pyc_sir_to_py.generate(i.origin, sir_str)
				sir_str = sir_str.getvalue()
				if i.origin.__class__ in [ast.If, pyc_ir_nodes.DoWhile, pyc_ir_nodes.BlocDef]:
					sir_str = sir_str.split("\n")[0]
				
				sir_str = string.strip(sir_str)
				ln = src_lineno(i.origin)
				sir_nodes[i.origin] = (ln, sir_str)
				print >>io
				print >>io, "%d:%s" % sir_nodes[i.origin]
				print >>io, offset				
			else:
				if prev_sir != i.origin:
					if isinstance(i.origin, ast.If):
						print >>io
						print >>io, "%d:%s" % sir_nodes[i.origin]
						print >>io, offset
					else:
						raise Exception(repr(i.origin))

			print >>io, "%s%s> %s" % (offset, "-"*16, repr(i) )
			prev_sir = i.origin



