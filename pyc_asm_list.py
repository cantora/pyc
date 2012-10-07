
from pyc_asm_nodes import *
from pyc_log import *
import pyc_vis

import ast

def from_sir_mod(sir_mod):
	asm_list = []
	vt = dict()

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
		insns = []
	
		if isinstance(expr, ast.Num):
			insns.append( Mov(Immed(Int(expr.n)), var) )
	
		elif isinstance(expr, ast.Name):
			op = self.se_to_operand(expr, var_tbl)
			insns.extend(self.mov(op, var))
	
		elif isinstance(expr, ast.BinOp):
			if isinstance(expr.op, ast.Add):
				insns.extend( self.add_to_var(var, expr.left, expr.right, var_tbl) )
			else:
				raise Exception("unexpected binop: %r", expr)
	
		elif isinstance(expr, ast.Call):
			insns.extend( self.fn_call(expr.func.id, expr.args, var_tbl) )
			insns.append( Mov(Register("eax"), var) )
	
		elif isinstance(expr, ast.UnaryOp):
			if isinstance(expr.op, ast.USub):
				insns.extend(self.neg_to_var(var, expr.operand, var_tbl) )
			else:
				raise Exception("unexpected unaryop: %s", ast.dump(expr))
	
		else:
			raise Exception("unexpected expr: %r" % expr)
	
		return insns

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
			return Immed(Int(expr.n) )
		elif isinstance(expr, ast.Name):
			var = Var(expr.id)
			if not var_tbl[var]:
				raise Exception("unknown Var %s" % expr.name)
			return var
	
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
		nodelen = len(pr_node.values)
		insns = []
	
		if nodelen != 1:
			raise Exception("expected pr_node with 1 node")
		
		return self.fn_call("print_int_nl", [pr_node.values[0]], var_tbl)
		
def sir_to_asm(sir_node, var_tbl):
	result = pyc_vis.walk(SIRtoASM(), sir_node, var_tbl)
	if len(result) < 1:
		raise Exception("expected non empty result")

	for ins in result:
		if not isinstance(ins, Inst):
			raise Exception("expected instruction node")

		ins.origin = sir_node

	return result

	




