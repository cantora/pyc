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

reg_index_map = {}
for i in range(0, len(registers) ):
	reg_index_map[registers[i]] = i

def reg_to_index(reg):
	global reg_index_map
	return reg_index_map[reg]
	
def index_to_loc(index):
	global registers

	if index < 0:
		raise Exception("invalid index %d" % index)
	elif index < len(registers):
		return Register(registers[index])
	else:
		return EBPIndirect(index - len(registers) )
		

class SymTable:
	def __init__(self):
		global registers
		self.mem_map = {}
		self.swaps = set([])

		#registers are like variables for which we must allocate
		#themselves
		for i in range(0, len(registers)):
			self.map(Register(registers[i]), i)

	def map(self, node, loc):
		if node in self.mem_map:
			raise Exception("%s is already mapped to %d" % (repr(node), self.mem_map[node]) )

		self.mem_map[node] = loc

	def swap_map(self, node, loc):
		self.map(node, loc)
		self.swaps.add(node)

	def get(self, node):
		return self.mem_map.get(node, None)

	#throws key error if the arg isnt mapped
	def __getitem__(self, arg):
		return self.mem_map[arg]

	#modifies current_swaps param
	def actual_index(self, node, current_swaps):
		if node in self.swaps:
			index = 5 - len(current_swaps)
			if index < 0:
				raise Exception("out of swap space!")
			
			current_swaps.add(node)
			return index

		return self[node]

	
	def __str__(self):
		return "\n\t".join(["%s: %s%s" % (repr(k), "*" if k in self.swaps else "", repr(v)) for (k,v) in self.mem_map.items()] )

	def __repr__(self):
		return "SymTable(mem_map=%s, swaps=%s)" % (repr(self.mem_map), repr(self.swaps))

	#log( lambda : "mem allocations:\n\t%s" % "\n\t".join(["%s: %s" % (repr(k), repr(pyc_reg_allocator.index_to_loc(v))) for (k,v) in mem_map.items()]) )

def alloc(live_list, graph, symtbl):
	global registers
	todo = set(graph.keys()) - set([Register(x) for x in registers])

	while len(todo) > 0:
		constraints = {}
		no_intf = set([])

		log("todo: %s" % repr(todo))

		for node in todo:
			log("  find constraints on %s" % repr(node) )
			if len(graph[node]) < 1:
				log("    no interference, assign to %s" % repr(index_to_loc(0)) )
				symtbl.map(node, 0)
				no_intf.add(node)
			else:
				constraints[node] = set([])
				for neighbor in graph[node]:
					n_loc = symtbl.get(neighbor)
					log("    reg for neighbor %s: %s" % (repr(neighbor), repr(n_loc) ) )
					if not n_loc is None:
						constraints[node].add(n_loc)

		todo = todo - no_intf
		sorted_nodes = sorted(constraints.keys(), key = lambda k: len(graph[k]), reverse = True)
		log("allocate memory for %s" % repr(sorted_nodes[0]) )
		i = 0
		while i in constraints[sorted_nodes[0]]:
			i = i+1

		if sorted_nodes[0].needs_reg and i > (len(registers)-1):
			symtbl.swap_map(sorted_nodes[0], i)
		else:
			symtbl.map(sorted_nodes[0], i)

		log("  allocated %d" % i)

		todo.remove(sorted_nodes[0])


def patch(asm_list, symtbl):
	result = []
	has_alts = False

	for ins in asm_list:
		log(lambda : "set locs in %s" % repr(ins))
		swaps = set([])
		loc_map = {}

		def node_to_loc(node):
			loc = index_to_loc(symtbl.actual_index(node, swaps))
			loc_map[node] = loc
			return loc

		new_ins = ins.patch_vars(node_to_loc)

		if new_ins == ins:
			result.append(new_ins)
			continue

		log( lambda : "  patched: %s" % repr(new_ins) )

		if new_ins.is_noop():
			continue

		alt_insns = new_ins.fix_operand_violations()
		if len(alt_insns) > 0:
			log(lambda : "  replace ins with: \n\t%s" % "\n\t".join([repr(x) for x in alt_insns]) )
			result.extend(alt_insns)
			has_alts = True
		else:
			#note: so far operand violations are always resolved by making
			#		the read operands registers, so a swap is always taking
			#		a memory location and putting it into a used register

			#we have to prefix/suffix in swap instructions if there were any swaps
			swap_list = list(swaps)
			
			for node in swap_list:
				stack_loc = index_to_loc(symtbl[node])
				#symtbl[node] returns the pre-swap location (not the register)
				prefix = [
					Push(loc_map[node]), 				#the register is in use, so store it on the stack
					Mov(stack_loc, loc_map[node] ), 	#swap our stack var into reg
					Pop(stack_loc)					#now put the stack val into our stack var's location
				]
				log(lambda : "    prefix: \n      %s" % "\n      ".join([repr(x) for x in prefix]))
				result.extend(prefix)

			result.append(new_ins)

			for node in reversed(swap_list):
				stack_loc = index_to_loc(symtbl[node])				
				#now restore things
				suffix = [
					Push(loc_map[node]),				#push our stack var onto stack
					Mov(stack_loc, loc_map[node] ),	#restore original variable from stack var's location
					Pop(stack_loc)					#restore our stack var to its rightful place
				]
				log(lambda : "    suffix: \n      %s" % "\n      ".join([repr(x) for x in suffix]))
				result.extend(suffix)

	
	return (has_alts, result)