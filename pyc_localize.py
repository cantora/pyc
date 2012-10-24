from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTVisitor
from pyc_astvisitor import ASTSearcher
import pyc_vis
from pyc_log import *
import pyc_gen_name
from pyc_validator import assert_valid
import pyc_constants

import ast
import copy

class Localizer(ASTTxformer):
	
	def __init__(self):
		ASTTxformer.__init__(self)

	@staticmethod
	def scope_fmt(scope, s):
		return "%s_%s" % (scope, s)

	def visit_Module(self, node):
		locs = locals(node)
		self.log(self.depth_fmt("locals: %r" % locs) )

		mappy = {}
		for loco in locs:
			mappy[loco] = Localizer.scope_fmt("main", loco)

		return ast.Module(
			body = [pyc_vis.visit(self, n, mappy, "main") for n in node.body]
		)

	def visit_Name(self, node, mappy, scope):
		if node.id in pyc_constants.reserved_vars | pyc_constants.internal_names:
			name_id = node.id
		else:
			name_id = mappy[node.id]
		
		return ast.Name(
			id = name_id,
			ctx = node.ctx.__class__()
		)

	def visit_FunctionDef(self, node, mappy, scope):
		fn_name = mappy[node.name]

		(new_args, new_body) = self.localize_lambda(node, mappy, fn_name)
		return ast.FunctionDef(
			name = fn_name,
			args = new_args,
			body = new_body
		)

	def visit_Lambda(self, node, mappy, scope):
		name = pyc_gen_name.new(Localizer.scope_fmt(scope, "l"))
		(new_args, new_body) = self.localize_lambda(node, mappy, name)
		return ast.Lambda(
			args = new_args,
			body = new_body[0]
		)

	def localize_lambda(self, node, mappy, lam_name):
		assert_valid(node)

		locs = locals(node)
		self.log(self.depth_fmt("locals: %r" % locs) )

		lam_mappy = copy.copy(mappy) #dont need deep copy, its a shallow dict
		for loco in locs:
			lam_mappy[loco] = Localizer.scope_fmt(lam_name, loco)

		body = [node.body] if isinstance(node, ast.Lambda) else node.body
		return (
			pyc_vis.visit(self, node.args, lam_mappy, lam_name),
			[pyc_vis.visit(self, n, lam_mappy, lam_name) for n in body]
		)

		
class LocalFinder(pyc_vis.Visitor):
	
	def __init__(self, root):
		pyc_vis.Visitor.__init__(self)
		self.root = root

	def default(self, node):
		return set([])

	def iterate_and_visit(self, ls):
		locals = set([])
		for n in ls:
			locals = locals | pyc_vis.visit(self, n)

		return locals
		
	def visit_Module(self, node):
		if node != self.root:
			raise Exception("shouldnt get here!")

		return self.iterate_and_visit(node.body)

	def visit_Assign(self, node):
		return self.iterate_and_visit(node.targets)

	def visit_Subscript(self, node):
		return pyc_vis.visit(self, node.value)

	def visit_NameWrap(self, node):
		return pyc_vis.visit(self, node.value)

	def visit_Name(self, node):
		self.log(self.depth_fmt("  local => %s" % node.id))
		return set([node.id])

	def visit_FunctionDef(self, node):
		if self.root != node:
			self.log(self.depth_fmt("  local => %s" % node.name))
			return set([node.name])
		else:
			return (
				self.iterate_and_visit(node.args.args)
					| self.iterate_and_visit(node.body)
			)

	def visit_Bloc(self, node):
		if self.root != node:
			return set([])
		else:
			return self.visit_FunctionDef(node)

	def visit_Lambda(self, node):
		if self.root != node:
			return set([])
		else:
			return (
				self.iterate_and_visit(node.args.args)
					| pyc_vis.visit(self, node.body)
			)

def locals(node):
	lf = LocalFinder(node)
	lf.log = lambda s: log("LocalFinder: %s" % s)
	return pyc_vis.walk(lf, node)

def txform(as_tree):
	v = Localizer()
	v.log = lambda s: log("Localizer  : %s" % s)
	return pyc_vis.walk(v, as_tree)
