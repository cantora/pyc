import pyc_vis
import ast

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

