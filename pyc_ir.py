from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTVisitor
import pyc_vis
import pyc_parser
from pyc_log import *
from pyc_ir_nodes import *
import pyc_gen_name

import StringIO
import ast

class InvalidSyntax(Exception):
	pass

class InvalidP1(InvalidSyntax):
	pass

#bad assumption ^_^
class BadAss(Exception):
	pass

class AstToIRTxformer(ASTTxformer):
		
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise InvalidP1("assign expected to have only one target: %r" % node)
		elif not isinstance(node.targets[0], ast.Name) and not isinstance(node.targets[0], ast.Subscript):
			raise BadAss("assumbed all targets were names: %r" % node)
		elif not isinstance(node.targets[0].ctx, ast.Store):
			raise BadAss("why isnt the target context store?: %r" % node)
		
		return ast.Assign(
			targets = [pyc_vis.visit(self, node.targets[0])],
			value = pyc_vis.visit(self, node.value)
		)

	def visit_Num(self, node):
		return InjectFromInt(ast.Num(n=node.n))

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

	def visit_Name(self, node):
		name_id = pyc_gen_name.user_name(node.id)
		return ast.Name(
			id = name_id,
			ctx = node.ctx.__class__()
		)

	def visit_UnaryOp(self, node):
		if isinstance(node.op, ast.Not):
			return InjectFromBool(ast.UnaryOp(
				op = ast.Not(),
				operand = IsTrue(pyc_vis.visit(self, node.operand) )
			))
		else:
			return self.default(node)

	def visit_IfExp(self, node):
		return ast.IfExp(
			test = IsTrue(pyc_vis.visit(self, node.test)),
			body = pyc_vis.visit(self, node.body),
			orelse = pyc_vis.visit(self, node.orelse)
		)
	
	def visit_Compare_Is(self, node, l_name, comp_name):
		
		class IsPolySwitch(PolySwitch):

			def no_match(self, name_typ_list):
				return false_node()

			def int_int(self, l, r):
				return simple_compare(ProjectToInt(l), ProjectToInt(r))

			def bool_bool(self, l, r):
				return simple_compare(ProjectToBool(l), ProjectToBool(r))

			def big_big(self, l, r):
				return simple_compare(ProjectToBig(l), ProjectToBig(r))
		#end IsPolySwitch

		return let_env(
			InjectFromBool(polyswitch(IsPolySwitch(), l_name, comp_name)) ,
			(
				l_name,
				pyc_vis.visit(self, node.left)
			),
			(
				comp_name,
				pyc_vis.visit(self, node.comparators[0])
			)
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

		l_name = var_ref(self.gen_name())
		comp_name = var_ref(self.gen_name() )

		if isinstance(node.ops[0], ast.Is):
			return self.visit_Compare_Is(node, l_name, comp_name)

		result = let_env(
			InjectFromBool(make_cmp(l_name, comp_name)),
			(
				l_name,
				pyc_vis.visit(self, node.left)
			),
			(
				comp_name, 
				pyc_vis.visit(self, node.comparators[0])
			)
		)
			
		if isinstance(node.ops[0], ast.NotEq):
			return InjectFromBool(ast.UnaryOp(
				op = ast.Not(),
				operand = IsTrue(result)
			))

		return result
		
	def visit_Call(self, node):
		if node.func.id != "input":
			raise InvalidP1("the only function in p1 is input >_<: %r" % node)
		
		return InjectFromInt(ast.Call(
			func = ast.Name( id = "input", ctx = ast.Load() ),
			kwargs = None,
			starargs = None
		))

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
			name = var_ref(d_name),
			rhs = InjectFromBig(
				DictRef()
			),
			body = BigInit(var_ref(d_name), elements)
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
					slice = ast.Index(pyc_vis.visit(self, ast.Num(n=i))),
					ctx = ast.Store()
				),
				pyc_vis.visit(self, e))
			)

		
		return Let( 
			name = var_ref(list_name),
			rhs = InjectFromBig(
				ListRef(
					InjectFromInt(ast.Num(n=len(node.elts) ) )
				)
			),
			body = BigInit(var_ref(list_name), elements)
		)

	def visit_BinOp(self, node):
		l_name = var_ref(self.gen_name())
		r_name = var_ref(self.gen_name())
		
		def unknown_op(node, *args):
			raise Exception("unsupported BinOp: %s" % ast.dump(node))

		return pyc_vis.dispatch_to_prefix(
			self,
			'visit_BinOp_',
			unknown_op,			
			node.op,
			node,
			l_name,
			r_name
		)
		
	def visit_BinOp_Add(self, dummy, node, l_name, r_name):

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
				return InjectFromInt(self.add_bools_or_ints(ProjectToInt(l), ProjectToInt(r)))

			def int_bool(self, l, r):
				return InjectFromInt(self.add_bools_or_ints(ProjectToInt(l), CastBoolToInt(ProjectToBool(r))))

			def bool_bool(self, l, r):
				return InjectFromInt(self.add_bools_or_ints(CastBoolToInt(ProjectToBool(l)), CastBoolToInt(ProjectToBool(r))))

			def bool_int(self, l, r):
				return InjectFromInt(self.add_bools_or_ints(CastBoolToInt(ProjectToBool(l)), ProjectToInt(r)))

			def big_big(self, l, r):
				return InjectFromBig(ast.Call(func = var_ref("add"), args = [ProjectToBig(l), ProjectToBig(r)]))
		#AddPolyswitch

		return let_env(
			polyswitch(AddPolySwitch(), l_name, r_name),
			(
				l_name,
				pyc_vis.visit(self, node.left)
			),
			(
				r_name,
				pyc_vis.visit(self, node.right)
			)
		)

	def visit_BoolOp(self, node):
		def unknown_op(node, *args):
			raise Exception("unsupported BoolOp: %s" % ast.dump(node))
		l_name = var_ref(self.gen_name())

		return pyc_vis.dispatch_to_prefix(
			self,
			'visit_BoolOp_',
			unknown_op,			
			node.op,
			node,
			l_name
		)

	def visit_BoolOp_And(self, dummy, node, l_name):
		if len(node.values) != 2:
			raise BadAss("expected 2 operands to bool op: %s" % ast.dump(node))

		return Let(
			name = l_name,
			rhs = pyc_vis.visit(self, node.values[0]),
			body = ast.IfExp(
				test = simple_compare(
					lhs = IsTrue(l_name),
					rhs = ast.Num(1)
				),
				body = pyc_vis.visit(self, node.values[1]),
				orelse = l_name
			)
		)
					
				
	def visit_BoolOp_Or(self, dummy, node, l_name):
		if len(node.values) != 2:
			raise BadAss("expected 2 operands to bool op: %s" % ast.dump(node))

		return Let(
			name = l_name,
			rhs = pyc_vis.visit(self, node.values[0]),
			body = ast.IfExp(
				test = simple_compare(
					lhs = IsTrue(l_name),
					rhs = ast.Num(1)
				),
				body = l_name,
				orelse = pyc_vis.visit(self, node.values[1])
			)
		)		


def generate(as_tree):
	v = AstToIRTxformer()
	#v.log = log
	ir = pyc_vis.walk(v, as_tree)
	#set False and True for the program environment
	ir.body.insert(
		0, 
		make_assign(var_set('user_False'), InjectFromBool(ast.Num(n=0)) )
	)
	ir.body.insert(
		0, 
		make_assign(var_set('user_True'), InjectFromBool(ast.Num(n=1)) )
	)

	return ir
	

def print_irtree(tree):
	return pyc_parser.print_astree(tree)

def tree_to_str(tree):
	return pyc_parser.tree_to_str(tree)

def dump(tree):
	return ast.dump(tree)


class PrintPyVisitor(ASTVisitor):
	
	def __init__(self, io):
		ASTVisitor.__init__(self)
		self.io = io

	def default_ast(self, node, field=""):
		pass

	def default_non_ast(self, obj, field=""):
		pass


def to_py(ir_node):
	s = StringIO.StringIO()
	v = PrintPyVisitor(s)	
	v.log = log
	pyc_vis.walk(v, ir_node)
	return v.io.getvalue()
	