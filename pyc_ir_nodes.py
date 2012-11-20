import ast
import copy

tag_types = ('int', 'bool', 'big')


def assert_type_exists(typ):
	global tag_types
	if typ not in tag_types:
		raise Exception("invalid type %s" % typ) 

class IRNode(ast.AST):

	def __init__(self, fields, **kwargs):
		ast.AST.__init__(self)
		self._fields = fields + tuple(['lineno'])
		self.init_kwargs(**kwargs)
	
	def init_kwargs(self, **kwargs):
		for f in self._fields:
			if f in kwargs:
				setattr(self, f, kwargs[f])

class Tag(IRNode):
	int = ast.Num(n=0)
	bool = ast.Num(n=1)
	big = ast.Num(n=3)

	@staticmethod
	def type_to_tag(type):
		if type == 'int':
			return 0
		elif type == 'bool':
			return 1
		elif type == 'big':
			return 3
		else:
			raise Exception("unknown type: %s" % type)

	def __init__(self, **kwargs):
		IRNode.__init__(
			self,
			tuple(['arg']),
			**kwargs
		)

simple_ir_nodes = {
	'UserCall':				tuple(['func', 'args', 'starargs', 'kwargs']),
	'NameWrap': 			tuple(['value']),
	'CreateClosure':		tuple(['name', 'free_vars']),
	'ClosureCall':			tuple(['var', 'args']),
	'ClosureFVS':			tuple(['var']),
	'Bloc':					tuple(['args', 'body', 'klass']),
	'BlocDef':				tuple(['name', 'params', 'body']),
	'DoWhile':				tuple(['test', 'tbody', 'wbody', 'dummy_lineno']),
	'Cast':					tuple(['from_typ', 'to_typ', 'arg']),
	'IsTrue':				tuple(['arg']),
	'IsClass':				tuple(['arg']),
	'IsBoundMethod':		tuple(['arg']),
	'IsUnboundMethod':		tuple(['arg']),
	'CreateObject':			tuple(['arg']),
	'HasAttr':				tuple(['obj', 'attr']),
	'GetFunction':			tuple(['arg']),
	'GetReceiver':			tuple(['arg']),
	'Let':					tuple(['name', 'rhs', 'body']),
	'Seq':					tuple(['body']),
	'Error':				tuple(['msg'])
}

for (name, fields) in simple_ir_nodes.items():
	globals()[name] = type(name, (IRNode,), {})

	setattr(globals()[name], 'dyn_fields', copy.copy(fields))
	setattr(
		globals()[name], 
		'__init__', 
		lambda self, **kwa:	IRNode.__init__(
			self,
			self.dyn_fields,
			**kwa
		)
	)


class BigRef(IRNode):
	
	def __init__(self, fields, **kwargs):
		IRNode.__init__(
			self,
			fields,
			**kwargs
		)

class ClassRef(BigRef):
	def __init__(self, **kwargs):
		BigRef.__init__(
			self,
			tuple(['bases']),
			**kwargs
		)

class ListRef(BigRef):
	def __init__(self, **kwargs):
		BigRef.__init__(
			self,
			tuple(['size']),
			**kwargs
		)

class DictRef(BigRef):
	def __init__(self, **kwargs):
		BigRef.__init__(
			self,
			tuple([]),
			**kwargs
		)

class InjectFrom(IRNode):
	
	def __init__(self, **kwargs):
		IRNode.__init__(
			self,
			('typ', 'arg'),
			**kwargs
		)
		
	@staticmethod
	def inject(node, typ):
		inj_klass = eval("InjectFrom%s" % typ.capitalize())
		return inj_klass(arg=node)

class InjectFromInt(InjectFrom):
	def __init__(self, **kwargs):
		kwargs["typ"] = 'int'
		InjectFrom.__init__(self, **kwargs)

class InjectFromBool(InjectFrom):
	def __init__(self, **kwargs):
		kwargs["typ"] = 'bool'
		InjectFrom.__init__(self, **kwargs)

class InjectFromBig(InjectFrom):
	def __init__(self, **kwargs):
		kwargs["typ"] = 'big'
		InjectFrom.__init__(self, **kwargs)

class ProjectTo(IRNode):
	def __init__(self, **kwargs):
		IRNode.__init__(
			self,
			('typ', 'arg'),
			**kwargs
		)

	@staticmethod
	def project(node, typ):
		proj_klass = eval("ProjectTo%s" % typ.capitalize())
		return proj_klass(arg=node)

class ProjectToInt(ProjectTo):
	def __init__(self, **kwargs):
		kwargs['typ'] = 'int'
		ProjectTo.__init__(self, **kwargs)

class ProjectToBool(ProjectTo):
	def __init__(self, **kwargs):
		kwargs['typ'] = 'bool'
		ProjectTo.__init__(self, **kwargs)

class ProjectToBig(ProjectTo):
	def __init__(self, **kwargs):
		kwargs['typ'] = 'big'
		ProjectTo.__init__(self, **kwargs)

class CastBoolToInt(Cast):
	def __init__(self, **kwargs):
		kwargs['from_typ'] = 'bool'		
		kwargs['to_typ'] = 'int'
		Cast.__init__(self, **kwargs)

class CastIntToBool(Cast):
	def __init__(self, **kwargs):
		kwargs['from_typ'] = 'int'		
		kwargs['to_typ'] = 'bool'
		Cast.__init__(self, **kwargs)



def var_set(name_id):
	return ast.Name(
		id = name_id,
		ctx = ast.Store()
	)

def copy_name(node):
	return ast.Name(
		id = node.id,
		ctx = node.ctx.__class__()
	)

def make_subn(name_id, node_ctx, index):
	return ast.Subscript(
		value = ast.Name(
			id = name_id,
			ctx = ast.Load()
		),
		slice = ast.Index(value=ast.Num(n=index)),
		ctx = node_ctx()
	)

def var_ref(name_id):
	return ast.Name(
		id = name_id,
		ctx = ast.Load()
	)

def make_call(func_id, args):
	return ast.Call(
		func = var_ref(func_id),
		args = args,
		kwargs = None,
		starargs = None
	)


def make_assign(target, value, **kwargs):
	return ast.Assign(
		targets = [target],
		value = value,
		**kwargs
	)

def simple_compare(lhs, rhs):
	return ast.Compare(
		left = lhs,
		ops = [ast.Eq()],
		comparators = [rhs]
	)

def false_node():
	return var_ref("False")
	
def let_env(body, *name_node_pairs):
	if len(name_node_pairs) < 1:
		return body

	if not (isinstance(name_node_pairs[0], tuple) \
			and len(name_node_pairs[0]) == 2 ):
		raise Exception("not a name-node pair: %r" % name_node_pairs[0])

	return Let(
		name = name_node_pairs[0][0],
		rhs = name_node_pairs[0][1],
		body = let_env(body, *name_node_pairs[1:])
	)


def tag_switch(name, int_node, bool_node, big_node):
	return ast.IfExp(
		test = simple_compare(
			lhs = Tag.int,
			rhs = Tag(arg=name)
		),
		body = int_node,
		orelse = ast.IfExp(
			test = simple_compare(
				lhs = Tag.bool,
				rhs = Tag(arg=name)
			),
			body = bool_node,
			orelse = ast.IfExp(
				test = simple_compare(
					lhs = Tag.big,
					rhs = Tag(arg=name)
				),
				body = big_node,
				orelse = make_error("unknown tag type")
			)
		)			
	)

def make_error(err_msg):
	return Error(msg = ast.Str(s = err_msg) )

#arguments to make_* must be Let names or code duplication will result


class PolySwitch:
	tag_to_type = {
		Tag.int: 'int',
		Tag.bool: 'bool',
		Tag.big: 'big'
	}

	def no_match(self, name_typ_list):
 		raise Exception('no method for form %s in %s' % (
			repr([(ast.dump(name), typ) for (name, typ) in name_typ_list]), 
			self.__class__
		))

	def match_types(self, typs):
		meth_name = "_".join(typs)
		meth = getattr(self, meth_name, None)
		return meth
	
	def cast_int_to_bool(self, int_node):
		return CastIntToBool(arg=int_node)

	def cast_bool_to_int(self, bool_node):
		return CastBoolToInt(arg=bool_node)
		

def polyswitch(instance, *names):
	return _polyswitch(instance, (), names)

def _polyswitch(instance, preceding, names):
	if len(names) < 1:
		return _polyswitch_base(instance, preceding)

	this_name = names[0]
	next_names = names[1:]

	return tag_switch(
		name = this_name,
		int_node = _polyswitch(
			instance, 
			preceding + ((this_name, Tag.int),), 
			next_names
		),
		bool_node = _polyswitch(
			instance,
			preceding + ((this_name, Tag.bool),),
			next_names
		),
		big_node = _polyswitch(
			instance,
			preceding + ((this_name, Tag.big),),
			next_names
		)		
	)

def _polyswitch_base(instance, preceding):
	#preceding contains a tuple of (name, tag)
	(names, tags) = zip(*preceding) 		
	typs = map(lambda tag: PolySwitch.tag_to_type[tag], tags)

	meth = instance.match_types(typs)
	if meth is None:
		return instance.no_match(zip(names, typs))
	
	return meth(*names)

"""
#taking this out for now, as it is doing too much
#ill try to find a way to bring it back if i find a 
#situation where i need it
def _polyswitch_base(instance, preceding):
	#preceding contains a tuple of (name, tag)
	(names, tags) = zip(*preceding) 		
	typs = map(lambda tag: PolySwitch.tag_to_type[tag], tags)

	meth = instance.match_types(typs)
	if meth is None:
		return polyswitch_match_types_with_casting(instance, preceding)
	
	projected_names = []
	for (name, typ) in zip(names, typs):
		projected_names.append(ProjectTo.project(name, typ) )
		
	return InjectFrom.inject(meth(*projected_names), typs[0])

def polyswitch_match_types_with_casting(instance, preceding):
	(names, tags) = zip(*preceding)
	typs = map(lambda tag: PolySwitch.tag_to_type[tag], tags)

	cast_fail = lambda : instance.no_match(zip(names, typs))

	#can only type cast to match for 2 vars right now cause
	#its really confusing
	if len(preceding) != 2: 
		return cast_fail()
	
	primary = typs[0]
	
	cast_meth = getattr(instance, "cast_%s_to_%s" % (typs[1], primary), None)
	if cast_meth is None:
		return cast_fail()

	meth = instance.match_types([primary, primary])
	if meth is None:
		return cast_fail()

	return InjectFrom.inject(
		meth(*[
			ProjectTo.project(names[0], primary),
			cast_meth(names[1])
		]),
		primary
	)
		

#more complete version of match types with casting: not finished. also... needed?
#too complicated to do generically right now
def polyswitch_match_types_with_casting(instance, preceding):
	(names, tags) = zip(*preceding)
	typs = map(lambda tag: PolySwitch.tag_to_type[tag], tags)

	primary = typs[0]
	convertable = {}

	for i in range(1, len(typs)):
		cast_meth = getattr(instance, "cast_%s_to_%s" % (typs[i], primary), None)
		if not cast_meth is None:
			convertable[i] = cast_meth

	for i in range(0, len(names)):
		

		native_vars = [ProjectTo.project(names[0], primary)]

		
		
	if meth is None:
		return instance.no_match(zip(names, types))
"""