class Visitor:

	def __init__(self):
		self.depth = 0
		self.log = None

	def default(self, node, *args):
		raise Exception('no visit method for type %s in %s at depth %d' \
			% (node.__class__, self.__class__, self.depth) )

	def depth_fmt(self, s):
		return "%s%s" % (" "*self.depth, s)
			

def dispatch_to_prefix(instance, prefix, default, node, *args):
	klass = node.__class__

	if isinstance(default, str):
		default_lam = lambda node, *args : getattr(instance, default)(node, *args)
	elif hasattr(default, '__call__'):
		default_lam = lambda node, *args : default(node, *args)
	else:
		raise Exception("unexpected default argument type: %r" % default)

	meth = getattr(
		instance, 
		prefix + klass.__name__, 
		default_lam		
	)

	if hasattr(instance.log, '__call__'):
		instance.log(instance.depth_fmt("%s => %s" % (node.__class__.__name__, meth.__name__) ) )

	return meth(node, *args)

def dispatch(instance, node, *args):
	return dispatch_to_prefix(instance, 'visit_', 'default', node, *args)

def visit(instance, node, *args):
	instance.depth += 1
	result = dispatch(instance, node, *args)
	instance.depth -= 1
	return result

def walk(instance, tree, *args):
	instance.depth = 0
	return dispatch(instance, tree, *args)
