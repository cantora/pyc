
from pyc_asm_nodes import *
from pyc_ir_nodes import *
from pyc_log import *
import pyc_vis

import ast

def from_sir_mod(sir_mod):
	asm_list = []
	vt = {
		Var("False"): True,
		Var("True"): True
	}

	log("convert simple statements to list of asm nodes")

	return [
		sir_to_asm(sir, vt) for sir in sir_mod.body
	]

class SIRtoASM(pyc_vis.Visitor):
	
	def __init__(self):
		pyc_vis.Visitor.__init__(self)


	def visit_Assign(self, assign, var_tbl):
		
		nodelen = len(assign.targets)
		if nodelen != 1:
			raise Exception("expected Assign with a single assignment")
	
		var = Var(assign.targets[0].id)
			
		result = self.set_var(var, assign.value, var_tbl)
		var_tbl[var] = True
	
		return result

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
		raise Exception("set_var_default: unexpected expr: %s" % ast.dump(node))
		
	def set_var_to_Num(self, node, var, var_tbl):
		return [Mov(Immed(DecInt(node.n)), var)]
	
	def set_var_to_Name(self, node, var, var_tbl):
		op = self.se_to_operand(node, var_tbl)
		return self.mov(op, var)
	
	def set_var_to_BinOp(self, node, var, var_tbl):
		if isinstance(node.op, ast.Add):
			return self.add_to_var(var, node.left, node.right, var_tbl)

		raise Exception("unexpected binop: %r", node)

	def set_var_to_Call(self, node, var, var_tbl):
		return self.fn_call(node.func.id, node.args, var_tbl) + [
			Mov(Register("eax"), var)
		]
	
	def set_var_to_UnaryOp(self, node, var, var_tbl):
		if isinstance(expr.op, ast.USub):
			return self.neg_to_var(var, expr.operand, var_tbl)

		raise Exception("unexpected unaryop: %s", ast.dump(expr))


	def set_var_to_InjectFromInt(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'inject_int', var, var_tbl)

	def set_var_to_InjectFromBool(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'inject_bool', var, var_tbl)

	def set_var_to_InjectFromBig(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'inject_big', var, var_tbl)

	def set_var_to_ProjectToInt(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'project_int', var, var_tbl)

	def set_var_to_ProjectToBool(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'project_bool', var, var_tbl)

	def set_var_to_ProjectToBig(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'project_big', var, var_tbl)

	def set_var_to_Tag(self, node, var, var_tbl):
		return self.set_var_to_single_arg_ir_fn(node, 'tag', var, var_tbl)

	def set_var_to_single_arg_ir_fn(self, node, fn, var, var_tbl):
		return self.set_var_to_Call(
			ast.Call(
				func = var_ref(fn),
				args = [var_ref(node.arg.id)]
			),
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
		return self.fn_call("error_pyobj", [node.msg], var_tbl) + [
			Mov(Immed(DecInt(1)), Register("eax") ),
			Interrupt(Immed(HexInt(0x80)))
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
			
	
		raise Exception("expected name or constant, got %s" % expr.__class__.__name__)
	
	def neg_to_var(self, var, expr, var_tbl):
		insns = []
		op = self.se_to_operand(expr, var_tbl)
	
		insns.extend( self.mov(op, var) )
		insns.append( Neg(var) )		
	
		return insns
	
	
	def fn_call(self, name, args, var_tbl):
		insns = []
		
		for i in args:
			insns.insert(0, Push(self.se_to_operand(i, var_tbl) ) )
	
		insns.append( Call(name) )
		
		#arglen = len(args)
		#if arglen > 0:
		#	insns.append( Pop(arglen) )
		
		return insns
		
	def visit_Print(self, pr_node, var_tbl):
		if len(pr_node.values) != 1:
			raise Exception("expected pr_node with 1 node")
		
		return self.fn_call("print_int_nl", [pr_node.values[0]], var_tbl)

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

			
def sir_to_asm(sir_node, var_tbl):
	result = pyc_vis.walk(SIRtoASM(), sir_node, var_tbl)
	if len(result) < 1:
		raise Exception("expected non empty result")

	for ins in result:
		if not isinstance(ins, Inst):
			raise Exception("expected instruction node: %s" % repr(ins))

		ins.origin = sir_node

	return result

	




