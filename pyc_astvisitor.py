import pyc_vis
import ast
import copy

class ASTVisitor(pyc_vis.Visitor):

	def __init__(self):
		pyc_vis.Visitor.__init__(self)
	
	def default(self, node, *args):
		"""Called if no explicit visitor function exists for a node."""

		if isinstance(node, ast.AST):
			self.default_ast(node, *args)
			for (field, value) in ast.iter_fields(node):
				#print "%s => %s" % (field, value.__class__.__name__)
				if isinstance(value, list):
					for i in range(0, len(value) ):
						pyc_vis.visit(self, value[i], field + ("[%d]" % i) )
				else:
					pyc_vis.visit(self, value, field)

		else:
			#print "non ast:"
			self.default_non_ast(node, *args)

class ASTTxformer(pyc_vis.Visitor):
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
