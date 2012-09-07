
from pyc_asm_nodes import *
from pyc_log import *

class sym_table(dict):

	def __init__(self):
		self.stack = 0

	def type_size(self, type):
		if type == "long":
			return 4
		else:
			raise Exception("unknown type %s" % type)

	def push(self, type):
		size = self.type_size(type)
		self.stack += size

	def pop(self, type):
		size = type_size(type)
		self.stack -= size

		
		
def from_ss_list(ss_list):
	asm_list = []
	st = sym_table()

	log("convert simple statements to list of asm nodes")

	for ss in ss_list:
		asm_list.append(py_ss_to_asm(ss, st))

	return asm_list


def py_ss_to_asm(ss, sym_tbl):
	if isinstance(ss, compiler.ast.Assign):
		return assign_to_asm(ss, sym_tbl)
	elif isinstance(ss, compiler.ast.Printnl):
		return printnl_to_asm(ss, sym_tbl)
	
	raise Exception("didnt expect ast node of type %s" % ss.__class__.__name__)

	
def assign_to_asm(assign, sym_tbl):
	log(repr(assign))
	
	nodelen = len(assign.nodes)
	if nodelen != 1:
		raise Exception("expected Assign with a single assignment")

	sym = assign.nodes[0].name
	addr = None

	try:
		addr = sym_tbl[sym]
	except KeyError:
		pass
	
	if addr == None:
		addr = sym_tbl.stack	
		sym_tbl.push("long")
		
	result = set_mem(addr, assign.expr, sym_tbl)
	sym_tbl[sym] = addr

	return result

"""
generate asm nodes to put an addition in eax
imm1, imm2 => [movl($imm1, %eax), addl($imm2, %eax)]
imm, addr or addr, imm1 => [movl(addr, %eax), addl($imm, %eax)]
addr1, addr2 => [movl(addr1, %eax), addl(addr2, %eax)]
"""
def add(left, right):
	return [
		Mov(left, Register("eax")),
		Add(right, Register("eax"))
	]
	
	
def se_to_operand(expr, sym_tbl):
	if isinstance(expr, compiler.ast.Const):
		return Immed(Int(expr.value) )
	elif isinstance(expr, compiler.ast.Name):
		src_addr = sym_tbl[expr.name]
		return EBPIndirect(src_addr)

	raise Exception("expected name or constant, got %s" % expr.__class__.__name__)

def fn_call(name, args, sym_tbl):
	insns = []
	
	for i in args:
		insns.insert(0, Push(se_to_operand(i, sym_tbl) ) )

	insns.append( Call(name) )
	
	arglen = len(args)
	#if arglen > 0:
	#	insns.append( Pop(arglen) )
	
	return insns
	

def set_mem(addr, expr, sym_tbl):
	dest_op = EBPIndirect(addr)
	insns = []

	if isinstance(expr, compiler.ast.Const):
		#movl $N, -(4+ADDR)(%ebp)
		insns.append( Mov(Immed(Int(expr.value)), dest_op) )

	elif isinstance(expr, compiler.ast.Name):
		src_addr = sym_tbl[expr.name]
		if src_addr == addr:
			raise Exception("src and dest are equal: %d" % addr)

		insns.extend( [
			Mov(EBPIndirect(src_addr), Register("eax") ),
			Mov(Register("eax"), dest_op )
		] )

	elif isinstance(expr, compiler.ast.Add):
		l_op = se_to_operand(expr.left, sym_tbl)
		r_op = se_to_operand(expr.right, sym_tbl)
		insns.extend( add(l_op, r_op) )
		insns.append( Mov(Register("eax"), dest_op ) )

	elif isinstance(expr, compiler.ast.CallFunc):
		insns.extend( fn_call(expr.node.name, expr.args, sym_tbl) )		
		insns.append( Mov(Register("eax"), dest_op) )

	elif isinstance(expr, compiler.ast.UnarySub):
		op = se_to_operand(expr.expr, sym_tbl)
		if isinstance(op, Immed):
			insns.append( Mov(op, dest_op) )

		elif isinstance(op, Indirect):
			if op.to_s() != dest_op.to_s():
				insns.append( Mov(op, Register("eax")) )
				insns.append( Mov(Register("eax"), dest_op) )

		else:
			raise Exception("expected Indirect or Immed operand, got %s" % op.__class__.__name__)  

		insns.append( Neg(dest_op) )		

	else:
		raise Exception("unexpected expr: %s" % expr.__class__.__name__)

	return insns

def printnl_to_asm(printnl, sym_tbl):
	nodelen = len(printnl.nodes)
	insns = []

	log(repr(printnl))
	
	if nodelen != 1:
		raise Exception("expected printnl with 1 node")
	
	return fn_call("print_int_nl", [printnl.nodes[0]], sym_tbl)
