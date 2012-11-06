from pyc_astvisitor import ASTTxformer
import pyc_vis
from pyc_log import *
from pyc_ir_nodes import *
import pyc_gen_name
from pyc_localize import locals
from pyc_constants import BadAss

import ast
import copy

def vis_fn(visitor, node, name, scope):
	locs = locals(node)
	fnscope = locs | scope 

	return ast.FunctionDef(
		name = name,
		args = pyc_vis.visit(visitor, node.args, fnscope),
		body = [
			pyc_vis.visit(visitor, n, fnscope) for n in node.body
		]
	)

def vis_cd(visitor, node, name, scope):
	if not isinstance(name, str):
		raise Exception("name must be a string")

	tmpname = pyc_gen_name.new("0class")
	bt = BodyTxformer(node, visitor, tmpname, scope) 
	bt.log = lambda s: log("BodyTxformer : %s" % s)

	return BigInit(
		pyobj_name = var_set(name),
		body = (
			[make_assign(
				var_set(tmpname), 
				ClassRef(
					bases=ast.List(
						elts = [
							pyc_vis.visit(visitor, b) for b in node.bases
						],
						ctx = ast.Load()
					)
				)
			)] + \
			pyc_vis.visit(bt, node) + \
			[make_assign(
				var_set(name), 
				var_ref(tmpname)
			)]
		)
	)

class Declassifier(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Module(self, node):
		locs = locals(node)
		self.log(self.depth_fmt("locals: %r" % locs) )

		return ast.Module(
			body = [pyc_vis.visit(self, n, locs) for n in node.body]
		)

	def visit_FunctionDef(self, node, scope):
		return vis_fn(self, node, node.name, scope)

	def visit_ClassDef(self, node, scope):
		if not isinstance(node.name, str):
			raise BadAss("assumed ClassDef.name was always a string")

		return vis_cd(self, node, node.name, scope)

class BodyTxformer(ASTTxformer):
	
	def __init__(self, root, parent, refname, scope):
		ASTTxformer.__init__(self)
		self.root = root
		self.parent = parent
		self.scope = scope
		self.attrs = set([])
		self.refname = refname

	def visit_ClassDef(self, cd):
		if cd == self.root:
			return [
				pyc_vis.visit(self, n) for n in cd.body
			]
		else:
			tmpname = pyc_gen_name.new(self.refname + "_classattr")
			return BigInit(
				pyobj_name = tmpname,
				body = [
					vis_cd(self.parent, cd, tmpname, self.scope),
					self.sattr(cd.name, var_ref(tmpname))
				]
			)

	def sattr(self, name, val):
		self.attrs.add(name)

		return make_assign(
			ast.Attribute(
				value = var_ref(self.refname),
				attr = name,
				ctx = ast.Store()	
			),
			val
		)

	def visit_Lambda(self, node):
		return pyc_vis.visit(self.parent, node, self.scope)

	def visit_FunctionDef(self, node):
		tmpname = pyc_gen_name.new(self.refname + "_defattr")
		return BigInit(
			pyobj_name = tmpname,
			body = [
				vis_fn(self.parent, node, tmpname, self.scope),
				self.sattr(node.name, var_ref(tmpname))
			]			
		)

	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise BadAss("expected singleton assign list")

		if isinstance(node.targets[0], ast.Name):
			return self.sattr(
				node.targets[0].id,
				pyc_vis.visit(self, node.value)
			)

		return make_assign(
			pyc_vis.visit(self, node.targets[0]),
			pyc_vis.visit(self, node.value)
		)

	def visit_Name(self, node):
		if node.id in self.attrs:
			return ast.Attribute(
				value = var_ref(self.refname),
				attr = node.id,
				ctx = ast.Load()
			)

		return copy_name(node)

		
def txform(as_tree):
	v = Declassifier()
	v.log = lambda s: log("Declassifier : %s" % s)
	return pyc_vis.walk(v, as_tree)
