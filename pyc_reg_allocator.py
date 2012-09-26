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
		return EBPIndirect( (index - len(registers))*4 )
		

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

	def stack(self):
		return (max(self.mem_map.values()) - 6)*4 + 4

	#throws key error if the arg isnt mapped
	def __getitem__(self, arg):
		return self.mem_map[arg]

	def is_swap(self, node):
		if not node in self.mem_map:
			raise Exception("unknown symbol %s" % repr(node) )

		return node in self.swaps
	
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

class Swapper:
	def __init__(self):
		self.map = {}
		
	def is_swapping(self):
		return len(self.map) > 0

	def swapon_insns(self, node, symtbl):
		if not node in self.map:
			raise Exception("%s is not currently swapped")

		stack_loc = index_to_loc(symtbl[node])
		#symtbl[node] returns the pre-swap location (not the register)
		reg = index_to_loc(self.map[node])

		return [
			Push(reg),	 			#the register is in use, so store it on the stack
			Mov(stack_loc, reg ), 	#swap our stack var into reg
			Pop(stack_loc)			#now put the stack val into our stack var's location
		]

	def swapon(self, node, symtbl):
		if node in self.map:
			raise Exception("shouldnt get here")

		reg_idxs = set([reg_to_index(x) for x in registers])
		free_idxs = reg_idxs - set(self.map.values())
		
		if len(free_idxs) < 1:
			raise Exception("out of swap space!")
			
		index = free_idxs.pop()
		self.map[node] = index

		return (index, self.swapon_insns(node, symtbl) )

	def evacuate(self, node, symtbl):
		if not node in self.map:
			raise Exception("%s is not swapped" % node)
			
		loc = index_to_loc(self.map[node])
		stack_loc = symtbl[node]
		del map[node]
		return [Mov(loc, stack_loc)]

	def swapoff(self, node, symtbl):
		if not node in self.map:
			raise Exception("%s is not swapped" % node)

		#log("swappoff: %s" % repr(node) )
			
		loc = index_to_loc(self.map[node])
		stack_loc = index_to_loc(symtbl[node])
		del self.map[node]
		return [
			Push(stack_loc),
			Mov(loc, stack_loc),
			Pop(loc)
		]
		
	def swap_from_reg(self, reg):
		reg_idx = reg_to_index(reg.name)
		for (node, index) in self.map.items():
			#log("%s == %s" % (index, reg_idx) )
			if index == reg_idx:
		 		return node

		return None

	def __getitem__(self, arg):
		return self.map[arg]

	def index(self, node, symtbl):
		if symtbl.is_swap(node):
			if node in self.map:
				return (self.map[node], True, [])
			else:
				(index, insns) = self.swapon(node, symtbl)
				return (index, True, insns)

		return (symtbl[node], False, [])

		
"""
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
"""

def dodge_swap_collisions(ins, swpr, swapped_ops, symtbl):
	insns = []

	for target in ins.reads():
		if not isinstance(target, Register): #we only swap into registers
			continue

		#if we are referring to a register in the context of the swapped in var
		#and not the original owner of the register, dont swapoff
		if target in set([index_to_loc(swpr[node]) for node in swapped_ops]):
			continue

		log("    check %s for swap collision" % repr(target) )
		colliding_node = swpr.swap_from_reg(target)
		if colliding_node is None:
			continue

		log("    %s collides with %s" % (repr(target), repr(colliding_node) ) )
		insns.extend(swpr.swapoff(colliding_node, symtbl))
		
	#we have to evacuate if we are writing to a swapped register
	for write in (set(ins.writes()) - set(ins.reads()) ):
		if not isinstance(write, Register): #we only swap into registers
			continue

		#if we are referring to a register in the context of the swapped in var
		#and not the original owner of the register, dont swapoff
		if write in set([index_to_loc(swpr[node]) for node in swapped_ops]):
			continue

		log("    check %s for swap collision" % repr(write) )
		colliding_node = swpr.swap_from_reg(write)
		if colliding_node is None:
			continue

		insns.extend(swpr.evacuate(colliding_node, symtbl))

	return insns
	
def patch(asm_list, symtbl):
	result = []
	has_alts = False
	swpr = Swapper()
	
	for ins in asm_list:
		log(lambda : "set locs in %s" % repr(ins))
		swapped_ops = set([])
		prefix_insns = []

		def node_to_loc(node):
			(index, swapped, insns) = swpr.index(node, symtbl)
			if swapped:
				swapped_ops.add(node)
				log("  current swap: %s => %s" % (repr(node), repr(index_to_loc(index)) ) )
				if len(insns) > 0:
					prefix_insns.extend(insns)
				

			return index_to_loc(index)

		new_ins = ins.patch_vars(node_to_loc)

		log( lambda : "  patched: %s" % repr(new_ins) if new_ins != ins else "  unchanged" )

		if new_ins.is_noop():
			if len(prefix_insns) > 0:
				raise Exception("just swapped for a noop?")
			log("    noop. continue")
			continue

		if swpr.is_swapping():
			prefix_insns.extend(dodge_swap_collisions(new_ins, swpr, swapped_ops, symtbl) )		

		alt_insns = new_ins.fix_operand_violations()
		if len(alt_insns) > 0:
			log(lambda : "  replace ins with: \n\t%s" % "\n\t".join([repr(x) for x in alt_insns]) )
			result.extend(alt_insns)
			has_alts = True
		else:
			if len(prefix_insns) > 0:
				log(lambda : "    prefix insns: \n      %s" % "\n      ".join([repr(x) for x in prefix_insns]))
				result.extend(prefix_insns)

			result.append(new_ins)
			
	
	return (has_alts, result)