class Visitor:

	def __init__(self):
		self.depth = 0

	def default(self, node, *args):
		raise Exception('no visit method for type %s in %s at depth %d' \
			% (node.__class__, self.__class__), self.depth)
	

def dispatch(instance, node, *args):
	klass = node.__class__
	className = klass.__name__
	meth = getattr(instance, 'visit_' + className, instance.default)

	return meth(node, *args)

def visit(instance, node, *args):
	instance.depth += 1
	result = dispatch(instance, node, *args)
	instance.depth -= 1
	return result

def walk(instance, tree, *args):
	instance.depth = 0
	return dispatch(instance, tree, *args)
