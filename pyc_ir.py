from pyc_astvisitor import ASTTxformer
from pyc_astvisitor import ASTVisitor
import pyc_vis
import pyc_parser
from pyc_log import *
from pyc_ir_nodes import *
import pyc_gen_name

import StringIO
import ast

class AstToIRTxformer(ASTTxformer):

	class InvalidSyntax(Exception):
		pass

	class InvalidP1(InvalidSyntax):
		pass

	#bad assumption ^_^
	class BadAss(Exception):
		pass
		
	def __init__(self):
		ASTTxformer.__init__(self)

	def visit_Assign(self, node):
		if len(node.targets) != 1:
			raise InvalidP1("assign expected to have only one target: %r" % node)
		elif not isinstance(node.targets[0], ast.Name):
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


	def visit_Compare(self, node):
		if len(node.ops) != 1:
			raise BadAss("expected 1 compare op: %s" % dump(node) )
		elif not isinstance(node.ops[0], ast.Eq):
			raise BadAss("expected compare to use equality context: %s" % dump(node) )
		elif len(node.comparators) != 1:
			raise BadAss("expected 1 comparator: %s" % dump(node) )

		l_name = var_ref(self.gen_name())
		comp_name = var_ref(self.gen_name() )

		return let_env(
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
			
		
	def visit_Call(self, node):
		if node.func.id != "input":
			raise InvalidP1("the only function in p1 is input >_<: %r" % node)
		
		return InjectFromInt(ast.Call(
			func = ast.Name( id = "input", ctx = ast.Load() ),
			kwargs = None,
			starargs = None
		))

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
		
			def int_int(self, l, r):
				return self.add_bools_or_ints(l, r)

			def bool_bool(self, l, r):
				return self.add_bools_or_ints(l, r)

			def big_big(self, l, r):
				return ast.Call(func = var_ref("add"), args = [l, r])
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


def generate(as_tree):
	v = AstToIRTxformer()
	#v.log = log
	return pyc_vis.walk(v, as_tree)

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
	