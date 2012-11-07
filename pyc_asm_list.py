
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


	def visit_Assign(self, assign, var_tbl):
		
		nodelen = len(assign.targets)
		if nodelen != 1:
			raise Exception("expected Assign with a single assignment")
	
		if isinstance(assign.targets[0], ast.Subscript):
			return self.set_subscript(assign, var_tbl)
		elif isinstance(assign.targets[0], ast.Attribute):
			return self.set_attribute(assign, var_tbl)
		else:
			var = Var(assign.targets[0].id)
				
			result = self.set_var(var, assign.value, var_tbl)
			var_tbl[var] = True
		
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
		InjectFromInt:	('inject_int', 'arg'),
		InjectFromBool:	('inject_bool', 'arg'),
		InjectFromBig:	('inject_big', 'arg'),
		ProjectToInt:	('project_int', 'arg'),
		ProjectToBool:	('project_bool', 'arg'),
		ProjectToBig:	('project_big', 'arg'),
		Tag:			('tag', 'arg'),
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

	def set_var_to_HasAttr(self, node, var, var_tbl):
		return self.set_var_to_fn_call(
			'has_attr',
			[node.obj, ast.Str(node.attr)],
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
		
		return self.cmp(lop, rop, var)
			
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

	#def set_var_to_BoolOp(self, node, var, var_tbl):
	#	def unknown_boolop(op, node, var, var_tbl):
	#		raise Exception("unknown bool op: %s" % ast.dump(op))
	#
	#	return pyc_vis.dispatch_to_prefix(
	#		self, 
	#		'set_var_to_BoolOp_', 
	#		unknown_boolop,
	#		node.op, 
	#		node,
	#		var,
	#		var_tbl
	#	)
	#
	#def set_var_to_BoolOp_And(self, dummy, node, var, var_tbl):
	#	return self.fn_call(	
	#		"is_true", 
	#		[node.values[0]],
	#		var_tbl
	#	) + [Mov(Register("eax"), 

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
		
		return self.fn_call("print_any", [pr_node.values[0]], var_tbl)

	def visit_If(self, ifnode, var_tbl):
		testop = self.se_to_operand(ifnode.test, var_tbl)
		body_insns = []
		for node in ifnode.body:
			body_insns.extend(pyc_vis.visit(self, node, var_tbl) )

		els_insns = []
		for node in ifnode.orelse:
			els_insns.extend(pyc_vis.visit(self, node, var_tbl) )

		return [AsmIf(
			test = testop,
			body = body_insns,
			orelse = els_insns
		)]

	def visit_DoWhile(self, node, var_tbl):
		tbody_insns = []
		for n in node.tbody:
			tbody_insns.extend(pyc_vis.visit(self, n, var_tbl) )

		testop = self.se_to_operand(node.test, var_tbl)

		wbody_insns = []
		for n in node.wbody:
			wbody_insns.extend(pyc_vis.visit(self, n, var_tbl) )

		return [AsmDoWhile(
			test = testop,
			tbody = tbody_insns,
			wbody = wbody_insns
		)]

	def visit_Return(self, node, var_tbl):
		return [
			Mov(self.se_to_operand(node.value, var_tbl), Register("eax")),
			Return() #instruction node; gets replaced later with a jmp
		]

	def visit_BlocDef(self, node):
		vt = {
			Var("False"): True,
			Var("True"): True
		}

		insns = []
		for i in range(0, len(node.params)):
			n = node.params[i]
			vt[Var(n.id)] = True
			insns.append(Mov(Param(i), Var(n.id)))

		for sir in node.body:
			insns.extend(pyc_vis.visit(self, sir, vt) )

		return CodeBloc(
			node.name,
			insns
		)

def sir_to_asm(sir_node):
	v = SIRtoASM()
	v.log = lambda s: log("SIRtoASM  : %s" % s)	
	result = pyc_vis.walk(v, sir_node)

	return result

"""
#origin stuff, come back to this later
	if len(result.insns) < 1:
		raise Exception("expected non empty result")

	for ins in result.insns:
		if not isinstance(ins, Inst):
			raise Exception("expected instruction node: %s" % repr(ins))

		ins.origin = sir_node
"""
	




