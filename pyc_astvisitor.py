import pyc_vis
import ast
import copy

class ASTVisitor(pyc_vis.Visitor):

	def __init__(self):
		pyc_vis.Visitor.__init__(self)
	
	def default(self, node, *args):

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

	def default(self, node, *args):

		new_node = node.__class__()
		for field, old_value in ast.iter_fields(node):
			#print "%s => %s" % (field, old_value.__class__.__name__)
			old_value = getattr(node, field, None)
			if isinstance(old_value, list):
				new_values = []
				for value in old_value:
					if isinstance(value, ast.AST):
						value = pyc_vis.visit(self, value, *args)
						if value is None:
							continue
						elif not isinstance(value, ast.AST):
							new_values.extend(value)
							continue
					new_values.append(value)
				setattr(new_node, field, new_values)
			elif isinstance(old_value, ast.AST):
				new_child = pyc_vis.visit(self, old_value, *args)
				if not new_child is None:
					setattr(new_node, field, new_child)

			elif isinstance(old_value, int) \
					or isinstance(old_value, str) \
					or old_value is None:
				setattr(new_node, field, old_value)

			else:
				raise Exception(
					"didnt expect to copy field %r with class %r in node %s" % (
						old_value, 
						old_value.__class__, 
						ast.dump(node)
					) 
				)

		return new_node

def names(node):
	names = set([])

	class NameFinder(ASTVisitor):
		def default(self, node, *args):
			pass

		def visit_Name(self, node, *args):
			return names.add(node.id)

	v = NameFinder()
	pyc_vis.walk(v, node)

	return names

