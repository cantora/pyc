from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTVisitor
import pyc_vis
import pyc_parser
from pyc_log import *
from pyc_ir_nodes import *
import pyc_gen_name
from pyc_constants import BadAss
import pyc_lineage

import StringIO
import ast

class InvalidSyntax(Exception):
	pass

class InvalidP1(InvalidSyntax):
	pass

class InvalidP3(InvalidSyntax):
	pass

class AstToIRTxformer(ASTTxformer):
		
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise InvalidP1("assign expected to have only one target: %r" % node)
		elif node.targets[0].__class__ not in set([ast.Name, ast.Subscript, ast.Attribute]):
			raise BadAss("assumed all targets were names, subs or attrs: %r" % ast.dump(node))
		elif not isinstance(node.targets[0].ctx, ast.Store):
			raise BadAss("why isnt the target context store?: %r" % node)
		
		return ast.Assign(
			targets = [pyc_vis.visit(self, node.targets[0])],
			value = pyc_vis.visit(self, node.value)
		)

	def visit_Num(self, node):
		return InjectFromInt(
			arg = ast.Num(n=node.n)
		)

	def visit_HasAttr(self, node):
		return InjectFromBool(
			arg = HasAttr(
				obj = pyc_vis.visit(self, node.obj),
				attr = pyc_vis.visit(self, node.attr)
			)
		)

	def visit_Print(self, node):
		if len(node.values) != 1:
			raise InvalidP1("print expected to have only one arg")
		
		return ast.Print(
			dest = None,
			values = [ pyc_vis.visit(self, node.values[0]) ],
			nl = True
		)

	def gen_name(self):
		return pyc_gen_name.new("ir_")

	def visit_UnaryOp(self, node):
		if isinstance(node.op, ast.Not):
			return InjectFromBool(arg = ast.UnaryOp(
				op = ast.Not(),
				operand = IsTrue(arg = pyc_vis.visit(self, node.operand) )
			))
		elif isinstance(node.op, ast.USub):
			return self.visit_UnaryOp_USub(node)
		else:			
			return self.default(node)

	def visit_UnaryOp_USub(self, node):

		class USubPolySwitch(PolySwitch):
			def no_match(self, name_typ_list):
				return make_error(
					"cant negate %s " % (name_typ_list[0][1])
				)

			def make_usub(self, op):
				return ast.UnaryOp(
					op = ast.USub(),
					operand = op
				)

			def int(self, op):
				return InjectFromInt(
					arg = self.make_usub(ProjectToInt(arg=op) ) 
				)

			def bool(self, op):
				return InjectFromInt(
					arg = self.make_usub(ProjectToBool(arg=op) ) 
				)

		#end USubPolySwitch

		return let(
			name_gen = self.gen_name,
			rhs = pyc_vis.visit(self, node.operand),
			body = lambda name: polyswitch(USubPolySwitch(), var_ref(name))
		)		


	def visit_IfExp(self, node):
		return ast.IfExp(
			test = IsTrue(arg=pyc_vis.visit(self, node.test)),
			body = pyc_vis.visit(self, node.body),
			orelse = pyc_vis.visit(self, node.orelse)
		)

	def visit_If(self, node):
		return ast.If(
			test = IsTrue(arg=pyc_vis.visit(self, node.test)),
			body = [pyc_vis.visit(self, x) for x in node.body],
			orelse = [pyc_vis.visit(self, x) for x in node.orelse]
		)

	def visit_While(self, node):
		if len(node.orelse) > 0:
			raise InvalidP3("while orelse not supported: %s" % dump(node) )

		return ast.While(
			test = IsTrue(arg=pyc_vis.visit(self, node.test)),
			body = [pyc_vis.visit(self, x) for x in node.body]			
		)

	def visit_Compare(self, node):
		if len(node.ops) != 1:
			raise BadAss("expected 1 compare op: %s" % dump(node) )
		elif not isinstance(node.ops[0], ast.Eq) \
				and not isinstance(node.ops[0], ast.NotEq) \
				and not isinstance(node.ops[0], ast.Is):
			raise BadAss("unexpected compare context: %s" % dump(node) )
		elif len(node.comparators) != 1:
			raise BadAss("expected 1 comparator: %s" % dump(node) )

		class IsPolySwitch(PolySwitch):

			def no_match(self, name_typ_list):
				return ast.Num(0)

			def int_int(self, l, r):
				return simple_compare(ProjectToInt(arg=l), ProjectToInt(arg=r))

			def bool_bool(self, l, r):
				return simple_compare(ProjectToBool(arg=l), ProjectToBool(arg=r))

			def big_big(self, l, r):
				return simple_compare(ProjectToBig(arg=l), ProjectToBig(arg=r))
		#end IsPolySwitch

		class CmpPolySwitch(IsPolySwitch):
			
 			def int_bool(self, l, r):
				return simple_compare(ProjectToInt(arg=l), ProjectToBool(arg=r))

			def bool_int(self, l, r):
				return simple_compare(ProjectToBool(arg=l), ProjectToInt(arg=r))

			def big_big(self, l, r):
				return make_call(
					'equal',
					[ ProjectToBig(arg=l), ProjectToBig(arg=r) ]
				)

		l_name = self.gen_name()
		comp_name = self.gen_name() 

		ps = IsPolySwitch() if isinstance(node.ops[0], ast.Is) else CmpPolySwitch()

		result = let_env(
			self.gen_name,
			lambda names: InjectFromBool(arg=polyswitch(ps, var_ref(names[0]), var_ref(names[1]))),
			pyc_vis.visit(self, node.left),
			pyc_vis.visit(self, node.comparators[0])
		)
			
		if isinstance(node.ops[0], ast.NotEq):
			return InjectFromBool(arg=ast.UnaryOp(
				op = ast.Not(),
				operand = IsTrue(arg=result)
			))

		return result
		
	def visit_Call(self, node):
		
		args = [pyc_vis.visit(self, n) for n in node.args]

		if isinstance(node.func, ast.Name) \
				and node.func.id in set(['input']):
			return InjectFromInt(arg=make_call('input', args) )
		else:
			return self.make_user_call(node)

	#yes, this is ugly T_T
	#this could be made much cleaner if runtime.c were rewritten in a 
	#smarter way
	def make_user_call(self, node):
		obj_name = self.gen_name()
		arg_nodes = []

		for n in node.args:
			arg_nodes.append(pyc_vis.visit(self, n))
		
		return let_env(
			self.gen_name,
			lambda names: ast.IfExp(
				test = simple_compare(
					ast.Num(0),
					IsClass(arg=var_ref(names[0]))
				),
				body = ast.IfExp(
					test = simple_compare(
						ast.Num(0),
						IsBoundMethod(arg=var_ref(names[0]))
					),
					body = ast.IfExp(
						test = simple_compare(
							ast.Num(0),
							IsUnboundMethod(arg=var_ref(names[0]))
						),
						body = UserCall( 					#just a normal function call
							func = var_ref(names[0]),
							args = [var_ref(name) for name in names[1:] ],
							kwargs = None,
							starargs = None
						),
						orelse = UserCall(					#unbound method call: get function and call
							func = InjectFromBig(arg=GetFunction(arg=var_ref(names[0]))),
							args = [var_ref(name) for name in names[1:] ],
							kwargs = None,
							starargs = None
						)
					),
					orelse = UserCall(						#bound method call: get function, receiver and call
						func = InjectFromBig(arg=GetFunction(arg=var_ref(names[0]))),
						args = [InjectFromBig(arg=GetReceiver(arg=var_ref(names[0])))] \
									+ [var_ref(name) for name in names[1:] ],
						kwargs = None,
						starargs = None
					)
				),
				orelse = Let(								#object creation: create and call __init__ if exists
					name = var_set(obj_name),
					rhs = InjectFromBig(arg=CreateObject(arg=var_ref(names[0]))),
					body = ast.IfExp(
						test = simple_compare(
							ast.Num(0),
							HasAttr(obj=var_ref(names[0]), attr=ast.Str('__init__'))
						),
						body = var_ref(obj_name),			#no __init__, return object
						orelse = Seq(					#call __init__, return object
							body = [
								UserCall(
									func = InjectFromBig(arg=GetFunction(
										arg = ast.Attribute(
											value = var_ref(names[0]),
											attr = '__init__',
											ctx = ast.Load()
										)
									)),
									args = [				#(object, arg1, ..., argn)
										var_ref(name) for name in ([obj_name] + names[1:])
									],
									kwargs = None,
									starargs = None
								), #call __init__
								var_ref(obj_name)
							] #body
						) #hasattr('__init__') true
					) #if hasattr('__init__')
				) #let o = CreateObject(names[0])
			),
			pyc_vis.visit(self, node.func),
			*arg_nodes
		)

	def visit_Dict(self, node):
		d_name = self.gen_name()

		elements = []
		for (k,v) in zip(node.keys, node.values):

			elements.append(make_assign(
				ast.Subscript(
					value = var_ref(d_name),
					slice = ast.Index(pyc_vis.visit(self, k)),
					ctx = ast.Store()
				),
				pyc_vis.visit(self, v))
			)

		
		return Let( 
			name = var_set(d_name),
			rhs = InjectFromBig(
				arg = DictRef()
			),
			body = Seq(body = elements + [var_ref(d_name)])
		)


	def visit_List(self, node):
		if not isinstance(node.ctx, ast.Load):
			raise BadAss("unexpected context for list: %s" % (ast.dump(node)) )
		
		list_name = self.gen_name()

		elements = []
		for i in range(0, len(node.elts)):
			e = node.elts[i]
			elements.append(make_assign(
				ast.Subscript(
					value = var_ref(list_name),
					slice = ast.Index(
						InjectFromInt(arg=ast.Num(n=i))
					),
					ctx = ast.Store()
				),
				pyc_vis.visit(self, e))
			)

		
		return Let( 
			name = var_set(list_name),
			rhs = InjectFromBig(
				arg = ListRef(
					size = InjectFromInt(arg = ast.Num(n=len(node.elts) ) )
				)
			),
			body = Seq(body = elements + [var_ref(list_name)]) 
		)

	def visit_ClassRef(self, node):
		return InjectFromBig(
			arg = ClassRef(
				bases = pyc_vis.visit(self, node.bases)
			)
		)

	def visit_BinOp(self, node):
		def unknown_op(node, *args):
			raise Exception("unsupported BinOp: %s" % ast.dump(node))

		return pyc_vis.dispatch_to_prefix(
			self,
			'visit_BinOp_',
			unknown_op,			
			node.op,
			node
		)
		
	def visit_BinOp_Add(self, dummy, node):

		class AddPolySwitch(PolySwitch):

			def no_match(self, name_typ_list):
				return make_error(
					"cant add %s to %s" % (
						name_typ_list[1][1],
						name_typ_list[0][1]
					)
				)

			def add_bools_or_ints(self, l, r):
				return ast.BinOp(left = l, op = ast.Add(), right = r)

			#int, bool => int, cast(bool, int) 
			def int_int(self, l, r):
				return InjectFromInt(
					arg = self.add_bools_or_ints(ProjectToInt(arg=l), ProjectToInt(arg=r))
				)

			def int_bool(self, l, r):
				return InjectFromInt(
					arg = self.add_bools_or_ints(ProjectToInt(arg=l), CastBoolToInt(arg=ProjectToBool(arg=r)))
				)

			def bool_bool(self, l, r):
				return InjectFromInt(
					arg = self.add_bools_or_ints(
						CastBoolToInt(arg=ProjectToBool(arg=l)), 
						CastBoolToInt(arg=ProjectToBool(arg=r))
					)
				)

			def bool_int(self, l, r):
				return InjectFromInt(
					arg = self.add_bools_or_ints(
						CastBoolToInt(arg=ProjectToBool(arg=l)), 
						ProjectToInt(arg=r)
					)
				)

			def big_big(self, l, r):
				return InjectFromBig(
					arg = make_call(
						"add", 
						[ProjectToBig(arg=l), ProjectToBig(arg=r)]
					)
				)
		#AddPolyswitch

		return let_env(
			self.gen_name,
			lambda names: polyswitch(AddPolySwitch(), var_ref(names[0]), var_ref(names[1])),
			pyc_vis.visit(self, node.left), 
			pyc_vis.visit(self, node.right)
		)

	def visit_BoolOp(self, node):
		def unknown_op(node, *args):
			raise Exception("unsupported BoolOp: %s" % ast.dump(node))

		return pyc_vis.dispatch_to_prefix(
			self,
			'visit_BoolOp_',
			unknown_op,			
			node.op,
			node
		)

	def visit_BoolOp_And(self, dummy, node):
		if len(node.values) != 2:
			raise BadAss("expected 2 operands to bool op: %s" % ast.dump(node))

		return let(
			name_gen = self.gen_name,
			rhs = pyc_vis.visit(self, node.values[0]),
			body = lambda name: ast.IfExp(
				test = simple_compare(
					lhs = ast.Num(1),
					rhs = IsTrue(arg=var_ref(name))
				),
				body = pyc_vis.visit(self, node.values[1]),
				orelse = var_ref(name)
			)
		)
					
				
	def visit_BoolOp_Or(self, dummy, node):
		if len(node.values) != 2:
			raise BadAss("expected 2 operands to bool op: %s" % ast.dump(node))

		return let(
			name_gen = self.gen_name,
			rhs = pyc_vis.visit(self, node.values[0]),
			body = lambda name: ast.IfExp(
				test = simple_compare(
					lhs = ast.Num(1),
					rhs = IsTrue(arg=var_ref(name))
				),
				body = var_ref(name),
				orelse = pyc_vis.visit(self, node.values[1])
			)
		)		

	def visit_FunctionDef(self, node):
		return make_assign(
			var_set(node.name),
			Bloc(
				args = pyc_vis.visit(self, node.args),
				body = [pyc_vis.visit(self, n) for n in node.body],
				klass = ast.FunctionDef
			)
		)

	def visit_Lambda(self, node):
		return Bloc(
			args = pyc_vis.visit(self, node.args),
			body = [ast.Return(
				value = pyc_vis.visit(self, node.body)
			)],
			klass = ast.Lambda
		)

def txform(astree, **kwargs):
	v = AstToIRTxformer()
	#v.log = log
	if 'tracer' in kwargs:
		v.tracer = kwargs['tracer']

	return pyc_vis.walk(v, astree)
	



