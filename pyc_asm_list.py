
from pyc_asm_nodes import *
from pyc_log import *
from pyc_ast import DiscardSSList


def from_ss_list(ss_list):
	asm_list = []
	vt = dict()

	log("convert simple statements to list of asm nodes")

	for ss in ss_list:
		if isinstance(ss, DiscardSSList):
			for dss in ss.nodes:
				asm_list.append(py_ss_to_asm(dss, vt))
		else:
			asm_list.append(py_ss_to_asm(ss, vt))

	return asm_list


def py_ss_to_asm(ss, var_tbl):
	result = []
	if isinstance(ss, compiler.ast.Assign):
		result = assign_to_asm(ss, var_tbl)
	elif isinstance(ss, compiler.ast.Printnl):
		result =  printnl_to_asm(ss, var_tbl)
	else:
		raise Exception("didnt expect ast node of type %s" % ss.__class__.__name__)

	if len(result) < 1:
		raise Exception("expected non empty result")

	for ins in result:
		if not isinstance(ins, Inst):
			raise Exception("expected instruction node")

		ins.origin = ss

	return result


def assign_to_asm(assign, var_tbl):
	log(repr(assign))
	
	nodelen = len(assign.nodes)
	if nodelen != 1:
		raise Exception("expected Assign with a single assignment")

	var = Var(assign.nodes[0].name)
		
	result = set_var(var, assign.expr, var_tbl)
	var_tbl[var] = True

	return result

def mov(src, dst):
	result = []
	
	#possible optimization, but reg 
	#allocation probably takes care of this
	#if dst == src: 
	#	pass # noop
	#else:
	result.append(Mov(src, dst) )

	return result	


def add_to_var(var, left, right, var_tbl):
	lop = se_to_operand(left, var_tbl)
	rop = se_to_operand(right, var_tbl)

	result = []
	result.extend(mov(rop, var))
	result.append(Add(lop, var))

	return result
	
def se_to_operand(expr, var_tbl):
	if isinstance(expr, compiler.ast.Const):
		return Immed(Int(expr.value) )
	elif isinstance(expr, compiler.ast.Name):
		var = Var(expr.name)
		if not var_tbl[var]:
			raise Exception("unknown Var %s" % expr.name)
		return var

	raise Exception("expected name or constant, got %s" % expr.__class__.__name__)

def neg_to_var(var, expr, var_tbl):
	insns = []
	op = se_to_operand(expr, var_tbl)

	insns.extend( mov(op, var) )
	insns.append( Neg(var) )		

	return insns


def fn_call(name, args, var_tbl):
	insns = []
	
	for i in args:
		insns.insert(0, Push(se_to_operand(i, var_tbl) ) )

	insns.append( Call(name) )
	
	arglen = len(args)
	#if arglen > 0:
	#	insns.append( Pop(arglen) )
	
	return insns
	

def set_var(var, expr, var_tbl):
	insns = []

	if isinstance(expr, compiler.ast.Const):
		#movl $N, -(4+ADDR)(%ebp)
		insns.append( Mov(Immed(Int(expr.value)), var) )

	elif isinstance(expr, compiler.ast.Name):
		op = se_to_operand(expr, var_tbl)
		insns.extend(mov(op, var))

	elif isinstance(expr, compiler.ast.Add):
		insns.extend( add_to_var(var, expr.left, expr.right, var_tbl) )

	elif isinstance(expr, compiler.ast.CallFunc):
		insns.extend( fn_call(expr.node.name, expr.args, var_tbl) )
		insns.append( Mov(Register("eax"), var) )

	elif isinstance(expr, compiler.ast.UnarySub):
		insns.extend(neg_to_var(var, expr.expr, var_tbl) )

	else:
		raise Exception("unexpected expr: %s" % expr.__class__.__name__)

	return insns

def printnl_to_asm(printnl, var_tbl):
	nodelen = len(printnl.nodes)
	insns = []

	log(repr(printnl))
	
	if nodelen != 1:
		raise Exception("expected printnl with 1 node")
	
	return fn_call("print_int_nl", [printnl.nodes[0]], var_tbl)
