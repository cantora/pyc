# Copyright 2013 anthony cantor
# This file is part of pyc.
# 
# pyc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#  
# pyc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#  
# You should have received a copy of the GNU General Public License
# along with pyc.  If not, see <http://www.gnu.org/licenses/>.

from pyc_asm_nodes import *
from pyc_ir_nodes import *
from pyc_log import *
import pyc_vis

import ast

def from_sir_mod(sir_mod):
	asm_list = []
	log("convert simple statements to list of asm nodes")

	return [
		sir_to_asm(sir) for sir in sir_mod.body
	]

class SIRtoASM(pyc_vis.Visitor):
	
	def __init__(self):
		pyc_vis.Visitor.__init__(self)

	def set_origin(self, insns, node):
		for i in insns:
			i.origin = node

	def visit_Assign(self, assign, var_tbl):
		
		nodelen = len(assign.targets)
		if nodelen != 1:
			raise Exception("expected Assign with a single assignment")

		if isinstance(assign.targets[0], ast.Subscript):
			result = self.set_subscript(assign, var_tbl)
		elif isinstance(assign.targets[0], ast.Attribute):
			result = self.set_attribute(assign, var_tbl)
		else:
			var = Var(assign.targets[0].id)
				
			result = self.set_var(var, assign.value, var_tbl)
			var_tbl[var] = True
		
		self.set_origin(result, assign)
		return result

	def set_subscript(self, node, var_tbl):
		return self.fn_call(
			"set_subscript",
			[
				node.targets[0].value,
				node.targets[0].slice,
				node.value
			],
			var_tbl
		)
		
	def set_attribute(self, node, var_tbl):
		return self.fn_call(
			"set_attr",
			[
				node.targets[0].value,
				ast.Str(node.targets[0].attr),
				node.value
			],
			var_tbl
		)

	def set_var(self, var, expr, var_tbl):
		return pyc_vis.dispatch_to_prefix(
			self, 
			'set_var_to_', 
			'set_var_default', 
			expr, 
			var,
			var_tbl
		)
		
	def set_var_default(self, node, var, var_tbl):
		if node.__class__ in set(SIRtoASM.ir_to_fn.keys()):
			return self.set_var_to_ir_fn(node, var, var_tbl)
				
		raise Exception("set_var_default: unexpected expr: %s" % ast.dump(node))

	ir_to_fn = {
		ClassRef:		('create_class', 'bases'),
		ClosureFVS:		('get_free_vars', 'var'),
		DictRef:		('create_dict',),
		ListRef:		('create_list', 'size'),
		IsTrue:			('is_true', 'arg'),
		IsClass:		('is_class', 'arg'),
		IsBoundMethod:	('is_bound_method', 'arg'),
		IsUnboundMethod:('is_unbound_method', 'arg'),
		GetFunction:	('get_function', 'arg'),
		GetReceiver:	('get_receiver', 'arg'),
		CreateObject:	('create_object', 'arg')
	}

	def set_var_to_ir_fn(self, node, var, var_tbl):
		fn = SIRtoASM.ir_to_fn[node.__class__][0]
		args = SIRtoASM.ir_to_fn[node.__class__][1:]

		return self.set_var_to_fn_call(
			fn,
			[getattr(node, x) for x in args],
			var,
			var_tbl
		)

	def set_var_to_Tag(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		
		return [
			Mov(op, var),
			And(Immed(HexInt(0x03)), var)
		]

	def set_var_to_ProjectToInt(self, node, var, var_tbl):
		return self.set_var_to_project(node, var, var_tbl)

	def set_var_to_ProjectToBool(self, node, var, var_tbl):
		return self.set_var_to_project(node, var, var_tbl)

	def set_var_to_ProjectToBig(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		return [
			Mov(op, var),
			And(Immed(HexInt(0xfffffffc)), var)
		]

	def set_var_to_project(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		return [
			Mov(op, var),
			Sarl(Immed(HexInt(2)), var)
		]

	def set_var_to_InjectFromBig(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		return [
			Mov(op, var),
			Or(Immed(HexInt(Tag.big.n)), var)
		]

	def set_var_to_InjectFromBool(self, node, var, var_tbl):
		return self.set_var_to_inject(node, var, var_tbl, Tag.bool.n)

	def set_var_to_InjectFromInt(self, node, var, var_tbl):
		return self.set_var_to_inject(node, var, var_tbl, Tag.int.n)

	def set_var_to_inject(self, node, var, var_tbl, tag):
		op = self.se_to_operand(node.arg, var_tbl)

		if isinstance(op, Immed):
			n = op.node.val
			n = n << 2
			n = n | tag
			return [Mov(Immed(HexInt(n)), var)]
			
		insns = [
			Mov(op, var),
			Sall(Immed(HexInt(0x02)), var)
		]
		
		if tag != 0:
			insns.append(Or(Immed(HexInt(tag)), var))

		return insns

	def set_var_to_HasAttr(self, node, var, var_tbl):
		return self.set_var_to_fn_call(
			'has_attr',
			[node.obj, node.attr],
			var,
			var_tbl
		)

	def set_var_to_CreateClosure(self, node, var, var_tbl):
		return self.set_var_to_fn_call(
			'create_closure', 
			[Immed(node.name), node.free_vars],
			var,
			var_tbl
		)

	def set_var_to_ClosureCall(self, node, var, var_tbl):
		insns = self.fn_call(
			'get_fun_ptr', 
			[node.var],
			var_tbl
		)
		insns.extend(self.fn_call_push_args(node.args, var_tbl))
		insns.append(IndirectCall(Register("eax")))
		insns.append(Mov(Register("eax"), var))
		
		return insns

	def set_var_to_Subscript(self, node, var, var_tbl):
		return self.set_var_to_fn_call(
			"get_subscript",
			[node.value, node.slice],
			var,
			var_tbl
		)

	def set_var_to_Attribute(self, node, var, var_tbl):
		return self.set_var_to_fn_call(
			"get_attr",
			[node.value, ast.Str(node.attr)],
			var,
			var_tbl
		)
		
	def set_var_to_Num(self, node, var, var_tbl):
		return [Mov(Immed(DecInt(node.n)), var)]
	
	def set_var_to_Name(self, node, var, var_tbl):
		op = self.se_to_operand(node, var_tbl)
		return self.mov(op, var)
	
	def set_var_to_BinOp(self, node, var, var_tbl):
		if isinstance(node.op, ast.Add):
			return self.add_to_var(var, node.left, node.right, var_tbl)

		raise Exception("unexpected binop: %r", node)

	def set_var_to_fn_call(self, name, fn_args, var, var_tbl):
		return self.fn_call(name, fn_args, var_tbl) + [
			Mov(Register("eax"), var)
		]
				
	def set_var_to_Call(self, node, var, var_tbl):
		return self.set_var_to_fn_call(node.func.id, node.args, var, var_tbl)
	
	def set_var_to_UnaryOp(self, node, var, var_tbl):
		def unknown_unaryop(op, node, var, var_tbl):
			raise Exception("unknown unary op: %s" % ast.dump(op))

		return pyc_vis.dispatch_to_prefix(
			self, 
			'set_var_to_UnaryOp_', 
			unknown_unaryop,
			node.op, 
			node,
			var,
			var_tbl
		)

	def set_var_to_Compare(self, node, var, var_tbl):
		lop = self.se_to_operand(node.left, var_tbl)
		rop = self.se_to_operand(node.comparators[0], var_tbl)
		
		return self.cmp(lop, rop, var, isinstance(node.ops[0], ast.NotEq) )
			
	def set_var_to_CastBoolToInt(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		
		return self.cmp(Immed(DecInt(0)), op, var, True)

	def set_var_to_CastIntToBool(self, node, var, var_tbl):
		op = self.se_to_operand(node.arg, var_tbl)
		
		return self.cmp(Immed(DecInt(0)), op, var, True)

	def set_var_to_Error(self, node, var, var_tbl):
		return self.fn_call("puts", [node.msg], var_tbl) + [
			Mov(Immed(DecInt(1)), Register("eax") ),
			Interrupt(Immed(HexInt(0x80))),
			Mov(Immed(DecInt(0)), var)
		]

	def cmp(self, a, b, dest, log_not=False):
		return [
			Cmp(a, b),
			Sete(CuteReg("al")) if log_not == False else Setne(CuteReg("al")),
			Movzbl(CuteReg("al"), dest)
		]

	def mov(self, src, dst):
		result = []
		
		#possible optimization, but reg 
		#allocation probably takes care of this
		#if dst == src: 
		#	pass # noop
		#else:
		result.append(Mov(src, dst) )
	
		return result	
	
	def add_to_var(self, var, left, right, var_tbl):
		lop = self.se_to_operand(left, var_tbl)
		rop = self.se_to_operand(right, var_tbl)
	
		result = []
		result.extend(self.mov(rop, var))
		result.append(Add(lop, var))
	
		return result
		
	def se_to_operand(self, expr, var_tbl):
		if isinstance(expr, ast.Num):
			return Immed(DecInt(expr.n) )
		elif isinstance(expr, ast.Name):
			var = Var(expr.id)
			if not var_tbl[var]:
				raise Exception("unknown Var %s" % expr.name)
			return var
		elif isinstance(expr, ast.Str):
			return Immed(GlobalString(expr.s))
		elif isinstance(expr, ast.Index):
			return self.se_to_operand(expr.value, var_tbl)
		elif isinstance(expr, Immed):
			return expr
	
		raise Exception("expected name or constant, got %s" % expr.__class__.__name__)
	
	def set_var_to_UnaryOp_USub(self, dummy, node, var, var_tbl):
		insns = []
		op = self.se_to_operand(node.operand, var_tbl)
	
		insns.extend( self.mov(op, var) )
		insns.append( Neg(var) )		
	
		return insns

	def set_var_to_UnaryOp_Not(self, dummy, node, var, var_tbl):
		insns = []
		op = self.se_to_operand(node.operand, var_tbl)
	
		return self.cmp(Immed(DecInt(0)), op, var)


	def fn_call_push_args(self, args, var_tbl):
		insns = []
		for i in args:
			insns.insert(0, Push(self.se_to_operand(i, var_tbl) ) )
	
		return insns
		
	def fn_call(self, name, args, var_tbl):
		insns = self.fn_call_push_args(args, var_tbl)
		
		insns.append( Call(name) )
		
		#arglen = len(args)
		#if arglen > 0:
		#	insns.append( Pop(arglen) )
		
		return insns
		
	def visit_Print(self, pr_node, var_tbl):
		if len(pr_node.values) != 1:
			raise Exception("expected pr_node with 1 node")
		
		result = self.fn_call("print_any", [pr_node.values[0]], var_tbl)
		self.set_origin(result, pr_node)
		return result

	def visit_If(self, ifnode, var_tbl):
		testop = self.se_to_operand(ifnode.test, var_tbl)
		body_insns = []
		for node in ifnode.body:
			body_insns.extend(pyc_vis.visit(self, node, var_tbl) )

		els_insns = []
		for node in ifnode.orelse:
			els_insns.extend(pyc_vis.visit(self, node, var_tbl) )

		result = [AsmIf(
			test = testop,
			body = body_insns,
			orelse = els_insns
		)]
		self.set_origin(result, ifnode)
		return result

	def visit_DoWhile(self, node, var_tbl):
		tbody_insns = []
		for n in node.tbody:
			tbody_insns.extend(pyc_vis.visit(self, n, var_tbl) )

		testop = self.se_to_operand(node.test, var_tbl)

		wbody_insns = []
		for n in node.wbody:
			wbody_insns.extend(pyc_vis.visit(self, n, var_tbl) )

		result = [AsmDoWhile(
			test = testop,
			tbody = tbody_insns,
			wbody = wbody_insns
		)]
		self.set_origin(result, node)
		return result

	def visit_Return(self, node, var_tbl):
		result = [
			Mov(self.se_to_operand(node.value, var_tbl), Register("eax")),
			Return() #instruction node; gets replaced later with a jmp
		]
		self.set_origin(result, node)
		return result

	def visit_BlocDef(self, node):
		vt = {
			Var("False"): True,
			Var("True"): True
		}

		insns = []
		for i in range(0, len(node.params)):
			n = node.params[i]
			vt[Var(n.id)] = True
			mv = Mov(Param(i), Var(n.id))
			mv.origin = node
			insns.append(mv)

		for sir in node.body:
			insns.extend(pyc_vis.visit(self, sir, vt))

		return CodeBloc(
			node.name,
			insns,
			node
		)

def sir_to_asm(sir_node):
	v = SIRtoASM()
	v.log = lambda s: log("SIRtoASM  : %s" % s)	
	result = pyc_vis.walk(v, sir_node)

	return result


