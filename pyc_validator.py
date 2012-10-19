from pyc_vis import Visitor
import pyc_vis
import ast

class AssumptionChecker(Visitor):
	def visit_FunctionDef(self, node):
		return (
			node.args.vararg is None and \
			node.args.kwarg is None
		)

	def visit_Lambda(self, node):
		return (
			self.visit_FunctionDef(node) and \
			len(node.args.defaults) == 0
		)

	
#check whether an ast node is constrained as expected
#for the particular level of python we are implementing
def isvalid(node):
	ac = AssumptionChecker()
	return pyc_vis.visit(ac, node)

def assert_valid(node):
	if not isvalid(node):
		raise Exception("node failed assumption: %s" % ast.dump(node))

