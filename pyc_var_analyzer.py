from pyc_log import *
from pyc_asm_nodes import VarOperandDesc

def interference_graph(asm_list):
	live_list = to_live_list(asm_list)
	log(lambda: "live_list:\n\t%s" % "\n\t".join([repr(x) for x in reversed(live_list)]))
	
	return None

def is_read_op(op):
	return isinstance(op, VarOperandDesc) \
		and VarOperandDesc.READ in op.modes


def is_write_op(op):
	return isinstance(op, VarOperandDesc) \
		and set([VarOperandDesc.WRITE]) == op.modes


def to_live_list(asm_list):
	result = []
	live = set([])

	log("process asm_list into live_list")
	for ins in reversed(asm_list):
		log("ins: %s" % ins)
		#log("operands: %s" % repr(ins.operands()))
		writes = []
		reads = []
		for op_desc in ins.operands():
			if is_write_op(op_desc):
				writes.append(op_desc.operand)
			elif is_read_op(op_desc):
				reads.append(op_desc.operand)

		live = (live - set(writes) ) | set(reads)

		result.append(set(live))
		log("live: %s" % repr(live))

	return result

	

