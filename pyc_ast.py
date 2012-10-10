from pyc_log import *
import pyc_gen_name
import pyc_vis
import pyc_ir
from pyc_ir_nodes import *
import ast

import copy

"""
def to_str_fmt_func(node, user, depth):
	val = node.__class__.__name__
	if len(node.getChildNodes()) == 0:
		val = repr(node)

	user.append( "%s%s" % (' '*depth, val) )


def str(as_tree):
	lines = []

	traverse(as_tree, to_str_fmt_func, lines)
	return "\n".join(lines)

def traverse(node, func, user):
	_traverse(node, func, user)

def _traverse(node, func, user, depth=0):
	func(node, user, depth)
	for n in node.getChildNodes():
		_traverse(n, func, user, depth+1)

"""

def sir_list_to_str(sir_list):
	return "\n".join(_sir_list_to_str(sir_list))

def _sir_list_to_str(sir_list, depth=0):
	lines = []
	for sir in sir_list:
		if isinstance(sir, ast.If):
			lines.append("%sIf(%s)" % (" "*depth, ast.dump(sir.test)) )
			lines.extend(_sir_list_to_str(sir.body, depth+1) )
			lines.append("%selse(%s)" % (" "*depth, ast.dump(sir.test)) )
			lines.extend(_sir_list_to_str(sir.orelse, depth+1) )
			lines.append("%send(%s)" % (" "*depth, ast.dump(sir.test)) )
		else:
			lines.append("%s%s" % (" "*depth, pyc_ir.dump(sir) ) )
			

	return lines

class IRTreeSimplifier(pyc_vis.Visitor):
	
	def __init__(self):
		pyc_vis.Visitor.__init__(self)

	def gen_name(self):
		return pyc_gen_name.new("gen_")
	
	def visit_Module(self, node):
		sir_body = []
		for n in node.body:
			(name, sir_list) = pyc_vis.visit(self, n)
			sir_body += sir_list

		return ast.Module(body = sir_body)

	def visit_ListRef(self, node):
		(size_name, size_sir_list) = pyc_vis.visit(self, node.size)
		result_name = self.gen_name()
		
		return (
			var_ref(result_name), 
			size_sir_list + [make_assign(
				var_ref(result_name),
				ListRef(size_name)
			)]
		)

	def visit_DictRef(self, node):
		result_name = self.gen_name()
		
		return (
			var_ref(result_name),
			[make_assign(
				var_ref(result_name),
				DictRef()
			)]
		)

	def visit_BigInit(self, node):
		init_sir_list = []

		for n in node.body:
			(name, sir_list) = pyc_vis.visit(self, n)
			init_sir_list.extend( sir_list )

		return (node.pyobj_name, init_sir_list)

	def visit_Assign(self, node):	
		(target, target_sir_list) = pyc_vis.visit(self, node.targets[0])
		(name, name_sir_list) = pyc_vis.visit(self, node.value)
		
		sir_list = name_sir_list + target_sir_list # + name_sir_list
		sir_list.append(make_assign(
			target,			
			name
		))
		
		return (None, sir_list)

	def visit_Subscript(self, node):
		(slice_name, slice_sir_list) = pyc_vis.visit(self, node.slice)
		(var_name, var_sir_list) = pyc_vis.visit(self, node.value)

		sir_list = var_sir_list + slice_sir_list #+ 
		new_sub = ast.Subscript(
			value = var_name,
			slice = slice_name,
			ctx = node.ctx.__class__()
		)

		if isinstance(node.ctx, ast.Load):
			result_name = self.gen_name()
			sir_list.append(make_assign(
				var_ref(result_name),
				new_sub		
			))
			return (var_ref(result_name), sir_list)
		
		#we are storing, so we need Subscript as left hand value
		return (new_sub, sir_list)
		
		
	def visit_IsTrue(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_BinOp(self, node):
		(l_name, l_sir_list) = pyc_vis.visit(self, node.left)
		(r_name, r_sir_list) = pyc_vis.visit(self, node.right)
		
		result_name = self.gen_name()
		l_sir_list += r_sir_list
		l_sir_list.append(make_assign(
			var_ref(result_name),
			ast.BinOp( 
				left = l_name, 
				op = node.op.__class__(),
				right = r_name
			)
		))

		return (var_ref(result_name), l_sir_list)

	def visit_UnaryOp(self, node):
		(name, sir_list) = pyc_vis.visit(self, node.operand)
		result_name = self.gen_name()
		sir_list.append(make_assign(
			var_ref(result_name),
			ast.UnaryOp(
				op = node.op.__class__(),
				operand = name
			)
		))

		return (var_ref(result_name), sir_list)

	def visit_Call(self, node):
		if not getattr(node, 'kwargs', None) is None \
				or not getattr(node, 'starargs', None) is None \
				or not getattr(node, 'keywords', None) is None:
			raise Exception("havent implemented kwargs or starargs")

		fn_args = []
		sir_list = []

		if hasattr(node, 'args'):
			for n in node.args:
				(name, arg_sir_list) = pyc_vis.visit(self, n)
				fn_args.append( name )
				sir_list += arg_sir_list
		
		result_name = self.gen_name()
		sir_list.append(make_assign(
			var_ref(result_name),
			ast.Call(
				func = var_ref(node.func.id), 
				args = fn_args
			)
		))

		return (var_ref(result_name), sir_list)

	def visit_Name(self, node):
		return (var_ref(node.id), [] )

	def visit_Index(self, node):
		(value_name, value_sir_list) = pyc_vis.visit(self, node.value)
		
		return (ast.Index(value_name), value_sir_list)

	def make_print(self, args):
		return ast.Print(dest=None, values=args, nl=True)

	def visit_Print(self, node):
		nlen = len(node.values)
		if nlen == 0 :
			return (None, [self.make_print([])])
		elif nlen == 1 :
			(name, sir_list) = pyc_vis.visit(self, node.values[0])
			sir_list.append(self.make_print([name]))
			return (None, sir_list)

		raise Exception("print statements may only print one item (%d)" % nlen)

	def visit_Num(self, node):
		return (ast.Num(n=node.n), [])
		
	def visit_Expr(self, node):
		(dummy, sir_list) = pyc_vis.visit(self, node.value)
		return (None, sir_list)


	def flatten_single_arg_ir_fn(self, node):
		(name, sir_list) = pyc_vis.visit(self, node.arg)
		result_name = self.gen_name()
		return (
			var_ref(result_name), 
			sir_list + [
				make_assign(
					var_ref(result_name),
					node.__class__(arg = name)
				)
			] 
		)

	def visit_InjectFromInt(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_InjectFromBool(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_InjectFromBig(self, node):
		return self.flatten_single_arg_ir_fn(node)


	def visit_ProjectToInt(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_ProjectToBool(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_ProjectToBig(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_CastBoolToInt(self, node):
		return self.flatten_single_arg_ir_fn(node)
	
	def visit_CastIntToBool(self, node):
		return self.flatten_single_arg_ir_fn(node)

	def visit_Error(self, node):
		return (Error(node.msg), [])

	def visit_Let(self, node):
		(rhs_name, rhs_sir_list) = pyc_vis.visit(self, node.rhs)
		(body_name, body_sir_list) = pyc_vis.visit(self, node.body)
		return (
			body_name,
			rhs_sir_list + [
				make_assign(
					var_ref(node.name.id),
					rhs_name
				)					
			] + body_sir_list
		)

	def visit_IfExp(self, node):
		(test_name, test_sir_list) = pyc_vis.visit(self, node.test)
		(body_name, body_sir_list) = pyc_vis.visit(self, node.body)
		(els_name, els_sir_list) = pyc_vis.visit(self, node.orelse)

		result_name = self.gen_name()
		return (
			var_ref(result_name),
			test_sir_list + [
				ast.If(
					test = test_name,
					body = body_sir_list + [
						make_assign(
							var_ref(result_name),
							body_name
						)
					],
					orelse = els_sir_list + [
						make_assign(
							var_ref(result_name),
							els_name
						)
					]
				)
			]
		)

	def visit_Compare(self, node):
		if len(node.comparators) != 1:
			raise Exception("assumed compare would only have 1 comparator")
		elif len(node.ops) != 1:
			raise Exception("assumed compare would only have 1 op")

		(l_name, l_sir_list) = pyc_vis.visit(self, node.left)
		(r_name, r_sir_list) = pyc_vis.visit(self, node.comparators[0])
		result_name = self.gen_name()

		return (
			var_ref(result_name),
			l_sir_list + r_sir_list + [
				make_assign(
					var_ref(result_name),
					simple_compare(l_name, r_name)
				)
			]
		)

	def visit_Tag(self, node):
		if not isinstance(node.arg, ast.Name):
			raise Exception("error: Tag should only have Name nodes as argument")
		
		result_name = self.gen_name()
		return (
			var_ref(result_name), 
			[make_assign(var_ref(result_name), Tag(var_ref(node.arg.id))) ]
		)

#convert an abstract syntax tree into a list of
#simple IR statements
def simple_ir(ir_tree):
	return pyc_vis.walk(IRTreeSimplifier(), ir_tree)




