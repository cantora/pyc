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

class Tag(IRNode):
	int_tag = ast.Num(n=0)
	bool_tag = ast.Num(n=1)
	big_tag = ast.Num(n=3)

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

class Error(IRNode):
	def __init__(self, msg):
		IRNode.__init__(self)
		self.msg = msg
		self._fields = tuple(['msg'])


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
	

def tag_switch(name, int_node, bool_node, big_node):
	return ast.IfExp(
		test = simple_compare(
			lhs = Tag(name),
			rhs = Tag.int_tag
		),
		body = int_node,
		orelse = ast.IfExp(
			test = simple_compare(
				lhs = Tag(name),
				rhs = Tag.bool_tag
			),
			body = bool_node,
			orelse = ast.IfExp(
				test = simple_compare(
					lhs = Tag(name),
					rhs = Tag.big_tag
				),
				body = big_node,
				orelse = Error("unknown tag type")
			)
		)			
	)

#left and right must be names or code duplication will result
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
