import pyc_vis
import pyc_parser

import ast
import copy

class AstToIRTxformer(pyc_vis.Visitor):

	class InvalidSyntax(Exception):
		pass

	class InvalidP1(InvalidSyntax):
		pass

	#bad assumption ^_^
	class BadAss(Exception):
		pass
		
	def __init__(self):
		pyc_vis.Visitor.__init__(self)

	def default(self, node):
		node = copy.deepcopy(node)
		for field, old_value in ast.iter_fields(node):
			old_value = getattr(node, field, None)
			if isinstance(old_value, list):
				new_values = []
				for value in old_value:
					if isinstance(value, ast.AST):
						value = pyc_vis.visit(self, value)
						if value is None:
							continue
						elif not isinstance(value, ast.AST):
							new_values.extend(value)
							continue
					new_values.append(value)
				old_value[:] = new_values
			elif isinstance(old_value, ast.AST):
				new_node = pyc_vis.visit(self, old_value)
				if new_node is None:
					delattr(node, field)
				else:
					setattr(node, field, new_node)
		return node


	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise InvalidP1("assign expected to have only one target: %r" % node)
		elif not isinstance(node.targets[0], ast.Name):
			raise BadAss("assumbed all targets were names: %r" % node)
		elif not isinstance(node.targets[0].ctx, ast.Store):
			raise BadAss("why isnt the target context store?: %r" % node)
		
		return ast.Assign(
			targets = [pyc_vis.visit(self, node.targets[0])],
			value = pyc_vis.visit(self, node.value)
		)

	def visit_Print(self, node):
		if len(node.values) != 1:
			raise InvalidP1("print expected to have only one arg")
		
		return ast.Print(
			dest = None,
			values = [ pyc_vis.visit(self, node.values[0]) ],
			nl = True
		)

	def visit_Name(self, node):
		name_id = "user_"+node.id
		return ast.Name(
			id = name_id,
			ctx = node.ctx.__class__()
		)

	def visit_IfExp(self, node):
		
		return ast.IfExp(
			test = pyc_vis.visit(self, node.test),
			body = pyc_vis.visit(self, node.body),
			orelse = pyc_vis.visit(self, node.orelse)
		)

	def visit_Call(self, node):
		if node.func.id != "input":
			raise InvalidP1("the only function in p1 is input >_<: %r" % node)
		
		return ast.Call(
			func = ast.Name( id = "input", ctx = ast.Load() ),
			kwargs = None,
			starargs = None
		)


def generate(as_tree):
	return pyc_vis.walk(AstToIRTxformer(), as_tree)

def print_irtree(tree):
	return pyc_parser.print_astree(tree)