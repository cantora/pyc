from pyc_log import *
from pyc_asm_nodes import *

"""
		if write is None:
			continue
		
		try:
			graph[write]
		except KeyError:
			graph[write] = set([])

		if isinstance(ins, Mov):
			graph[write] 
		else:
"""

def interference_graph(asm_list):
	live_list = to_live_list(asm_list)
	log(lambda: "live_list:\n\t%s" % "\n\t".join([repr(x) for x in reversed(live_list)]))

	exit()
	graph = to_intf_graph(live_list)
	
	return None

def to_intf_graph(live_list):
	graph = {}
	
#	for (ins, live) in live_list:
#		log("(%s)

def get_vars(op_descs):
	result = []
	
	for op_desc in op_descs:
		if isinstance(op_desc, VarOperandDesc):
			result.append(op_desc.operand)
		
	return result


def to_live_list(asm_list):
	result = []
	live = set([])

	log("process asm_list into live_list")
	for ins in reversed(asm_list):
		log("ins: %s" % ins)

		live = (live - set( get_vars(ins.writes()) ) ) \
				| set( get_vars(ins.reads()) )
		
		result.append((ins, set(live)) )
		log("live: %s" % repr(live))


	return result

