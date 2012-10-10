import ast

tag_types = ('int', 'bool', 'big')


def assert_type_exists(typ):
	global tag_types
	if typ not in tag_types:
		raise Exception("invalid type %s" % typ) 

class IRNode(ast.AST):

	def __init__(self):
		ast.AST.__init__(self)

class InjectFrom(IRNode):
	
	def __init__(self, typ, arg):
		IRNode.__init__(self)
		self.typ = typ
		self.arg = arg
		self._fields = ('typ', 'arg')

		assert_type_exists(self.typ)

	@staticmethod
	def inject(node, typ):
		inj_klass = eval("InjectFrom%s" % typ.capitalize())
		return inj_klass(node)

class InjectFromInt(InjectFrom):
	def __init__(self, arg):
		InjectFrom.__init__(self, 'int', arg)

class InjectFromBool(InjectFrom):
	def __init__(self, arg):
		InjectFrom.__init__(self, 'bool', arg)

class InjectFromBig(InjectFrom):
	def __init__(self, arg):
		InjectFrom.__init__(self, 'big', arg)

class ProjectTo(IRNode):
	def __init__(self, typ, arg):
		IRNode.__init__(self)
		self.typ = typ
		self.arg = arg
		self._fields = ('typ', 'arg')

		assert_type_exists(self.typ)

	@staticmethod
	def project(node, typ):
		proj_klass = eval("ProjectTo%s" % typ.capitalize())
		return proj_klass(node)

class ProjectToInt(ProjectTo):
	def __init__(self, arg):
		ProjectTo.__init__(self, 'int', arg)
		
class ProjectToBool(ProjectTo):
	def __init__(self, arg):
		ProjectTo.__init__(self, 'bool', arg)

class ProjectToBig(ProjectTo):
	def __init__(self, arg):
		ProjectTo.__init__(self, 'big', arg)

class Cast(IRNode):
	def __init__(self, from_typ, to_typ, arg):
		IRNode.__init__(self)
		self.from_typ = from_typ
		self.to_typ = to_typ
		self.arg = arg
		self._fields = ('from_typ', 'to_typ', 'arg')

		assert_type_exists(self.from_typ)
		assert_type_exists(self.to_typ)		

class CastBoolToInt(Cast):
	def __init__(self, arg):
		Cast.__init__(self, 'bool', 'int', arg)

class CastIntToBool(Cast):
	def __init__(self, arg):
		Cast.__init__(self, 'int', 'bool', arg)

class IsTrue(IRNode):
	def __init__(self, arg):
		self.arg = arg
		self._fields = tuple(['arg'])

class Tag(IRNode):
	int = ast.Num(n=0)
	bool = ast.Num(n=1)
	big = ast.Num(n=3)

	def __init__(self, arg):
		IRNode.__init__(self)
		self.arg = arg
		self._fields = tuple(['arg'])


class Type(IRNode):
	def __init__(self, arg):
		IRNode.__init__(self)
		self.arg = arg
		self._fields = tuple(['arg'])
	
class Let(IRNode):
	def __init__(self, name, rhs, body):
		IRNode.__init__(self)
		self.name = name
		self.rhs = rhs
		self.body = body
		self._fields = ('name', 'rhs', 'body')

class BigRef(IRNode):
	pass

class ListRef(BigRef):
	def __init__(self, size):
		BigRef.__init__(self)
		self.size = size
		self._fields = tuple(['size'])

class DictRef(BigRef):
	pass

class BigInit(IRNode):
	def __init__(self, pyobj_name, body):
		self.pyobj_name = pyobj_name
		self.body = body
		self._fields = tuple(['pyobj_name', 'body'])


class Error(IRNode):
	def __init__(self, msg):
		IRNode.__init__(self)
		self.msg = msg
		self._fields = tuple(['msg'])

def var_set(name_id):
	return ast.Name(
		id = name_id,
		ctx = ast.Store()
	)

def var_ref(name_id):
	return ast.Name(
		id = name_id,
		ctx = ast.Load()
	)

def make_assign(target, value):
	return ast.Assign(
		targets = [target],
		value = value
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
		name_node_pairs[0][0],
		name_node_pairs[0][1],
		let_env(body, *name_node_pairs[1:])
	)


def tag_switch(name, int_node, bool_node, big_node):
	return ast.IfExp(
		test = simple_compare(
			lhs = Tag(name),
			rhs = Tag.int
		),
		body = int_node,
		orelse = ast.IfExp(
			test = simple_compare(
				lhs = Tag(name),
				rhs = Tag.bool
			),
			body = bool_node,
			orelse = ast.IfExp(
				test = simple_compare(
					lhs = Tag(name),
					rhs = Tag.big
				),
				body = big_node,
				orelse = make_error("unknown tag type")
			)
		)			
	)

def make_error(msg):
	return Error(ast.Str(s = msg) )

#arguments to make_* must be Let names or code duplication will result

def make_cmp(lname, rname):
	return tag_switch(
		name = lname,
		int_node = make_int_cmp(lname, rname),
		bool_node = make_bool_cmp(lname, rname),
		big_node = make_big_cmp(lname, rname)
	)

def make_int_cmp(lname, rname):
	return tag_switch(
		name = rname,
		int_node = simple_compare(
			lhs = ProjectToInt(lname),
			rhs = ProjectToInt(rname)
		),
		bool_node = simple_compare(
			lhs = ProjectToInt(lname),
			rhs = CastBoolToInt(rname)
		),
		big_node = false_node()
	)

def make_bool_cmp(lname, rname):
	return tag_switch(
		name = rname,
		int_node = simple_compare(
			lhs = ProjectToBool(lname),
			rhs = CastIntToBool(rname)
		),
		bool_node = simple_compare(
			lhs = ProjectToBool(lname),
			rhs = ProjectToBool(rname)
		),
		big_node = false_node()
	)

def make_big_cmp(lname, rname):
	return tag_switch(
		name = rname,
		int_node = false_node(),
		bool_node = false_node(),
		big_node = ast.Call(
			func = var_ref('equal'),
			args = [ ProjectToBig(lname), ProjectToBig(rname) ]
		)
	)

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
		return CastIntToBool(int_node)

	def cast_bool_to_int(self, bool_node):
		return CastBoolToInt(bool_node)
		

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