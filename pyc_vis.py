
class VisTracer:
	def __init__(self):
		self.visitors = set([])

	def trace(self, result, instance, prefix, default, value, *args, **kwargs):
		pass

class Visitor:

	def __init__(self):
		self.depth = 0
		self.log = lambda s: None
		self.tracer = None

	def default(self, node, *args, **kwargs):
		raise Exception('no visit method for type %s in %s at depth %d' \
			% (node.__class__, self.__class__, self.depth) )

	def depth_fmt(self, s):
		return "%s%s" % (" "*self.depth, s)
			

def dispatch_to_prefix(instance, prefix, default, node, *args, **kwargs):

	return dispatch_to_prefix_value(
		instance, 
		prefix, 
		default, 
		node.__class__.__name__,
		*((node,) + args),
		**kwargs
	)

def dispatch_to_prefix_value(instance, prefix, default, value, *args, **kwargs):
	if isinstance(default, str):
		default_lam = lambda *a, **kwa : getattr(instance, default)(*a, **kwa)
	elif hasattr(default, '__call__'):
		default_lam = lambda *a, **kwa : default(*a, **kwa)
	else:
		raise Exception("unexpected default argument type: %r" % default)
	
	meth = getattr(
		instance, 
		prefix + value,
		default_lam		
	)

	if hasattr(instance.log, '__call__'):
		instance.log(instance.depth_fmt("%s => %s" % (value, meth.__name__) ) )

	result = meth(*args, **kwargs)
	if hasattr(instance, 'tracer') and instance.tracer is not None:
		instance.tracer.trace(result, instance, prefix, default, value, *args, **kwargs)

	return result

def dispatch(instance, node, *args, **kwargs):
	return dispatch_to_prefix(instance, 'visit_', 'default', node, *args, **kwargs)

def visit(instance, node, *args, **kwargs):
	instance.depth += 1
	result = dispatch(instance, node, *args, **kwargs)
	instance.depth -= 1
	return result

def walk(instance, tree, *args, **kwargs):
	instance.depth = 0

	if isinstance(tree, list):
		raise Exception("expected a tree root of some sort, not a list: %r" % tree)

	return dispatch(instance, tree, *args, **kwargs)
