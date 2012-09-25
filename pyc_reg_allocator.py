from pyc_var_analyzer import IntfGraph
from pyc_log import *
from pyc_asm_nodes import *
import random
import copy

caller_save = [
	"ecx",
	"edx",
	"eax"
]

callee_save = [
	"ebx",
	"esi",
	"edi"
]

registers = callee_save + caller_save

def index_to_loc(index):
	global registers

	if index < 0:
		raise Exception("invalid index %d" % index)
	elif index < len(registers):
		return Register(registers[index])
	else:
		return EBPIndirect(index - len(registers) )
		
	
def alloc(live_list, graph):
	global registers
	mem_map = {}
	todo = set(graph.keys())

	#registers are like variables for which me must allocate
	#themselves
	for i in range(0, len(registers)):
		mem_map[Register(registers[i])] = i

	while len(todo) > 0:
		constraints = {}

		log("todo: %s" % repr(todo))

		for node in todo:
			constraints[node] = set([])
			log("  find constraints on %s" % repr(node) )
			for neighbor in graph[node]:
				n_loc = mem_map.get(neighbor, None)
				log("    reg for neighbor %s: %s" % (repr(neighbor), repr(n_loc) ) )
				if not n_loc is None:
					constraints[node].add(n_loc)

		sorted_nodes = sorted(constraints.keys(), key = lambda k: len(graph[k]), reverse = True)
		log("allocate memory for %s" % repr(sorted_nodes[0]) )
		i = 0
		while i in constraints[sorted_nodes[0]]:
			i = i+1

		mem_map[sorted_nodes[0]] = i
		log("  allocated %d" % i)

		todo.remove(sorted_nodes[0])


	return mem_map


def patch(asm_list, mem_map):
	result = []
	has_alts = False

	for ins in asm_list:
		#log("set locs in %s" % repr(ins))
		new_ins = ins.patch_vars(lambda node: index_to_loc(mem_map[node]) )
		#log("  patched: %s" % repr(new_ins) )

		alt_insns = new_ins.fix_operand_violations()
		if len(alt_insns) > 0:
			result.extend(alt_insns)
			has_alts = True
		else:
			result.append(new_ins)
	
	return (has_alts, result)