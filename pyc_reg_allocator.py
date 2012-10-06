from pyc_var_analyzer import IntfGraph
from pyc_log import *
from pyc_asm_nodes import *

import pyc_var_analyzer 
import random
import copy
import time

reg_index_map = {}
for i in range(0, len(Register.registers) ):
	reg_index_map[Register.registers[i]] = i

def reg_to_index(reg):
	global reg_index_map
	return reg_index_map[reg]
	
def index_to_loc(index):

	if index < 0:
		raise Exception("invalid index %d" % index)
	elif index < len(Register.registers):
		return Register(Register.registers[index])
	else:
		return EBPIndirect( (index - len(Register.registers))*4 )
		

class SymTable:
	def __init__(self):
		self.mem_map = {}
		self.swaps = set([])

		#registers are like variables for which we must allocate
		#themselves
		for i in range(0, len(Register.registers)):
			self.map(Register(Register.registers[i]), i)

	def boot_reg_dwellers(self):
		for var in self.mem_map.keys():
			if not isinstance(var, Register) and self.mem_map[var] < len(Register.registers):
				del self.mem_map[var]

	def map(self, node, loc):
		if node in self.mem_map:
			raise Exception("%s is already mapped to %d" % (repr(node), self.mem_map[node]) )

		self.mem_map[node] = loc

	def swap_map(self, node, loc):
		raise Exception("swaps not currently implemented :(")
		self.map(node, loc)
		self.swaps.add(node)

	def get(self, node):
		return self.mem_map.get(node, None)

	def high_index(self):
		return max(self.mem_map.values())

	def stack(self):
		return (self.high_index() - 6)*4 + 4

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


class Allocator:
	def __init__(self):
		self.symtbl = SymTable()
		self.stack_constraints = {}

	def propagate_reg_constraints(self, reg_constraints, graph, todo, node, index):
		for n in todo:
			if n not in graph[node]:
				continue

			if n not in reg_constraints:
				reg_constraints[n] = set([])

			reg_constraints[n].add(index)


	def propagate_stack_constraints(self, graph, node, index):
		for intf_node in graph[node]:
			if intf_node not in self.stack_constraints:
				self.stack_constraints[intf_node] = set([])

			self.stack_constraints[intf_node].add(index)


	def allocate_stack(self, node, graph):
		if node.needs_reg:
			raise Exception("%s needs a reg!" % repr(node))

		i = len(Register.registers)
		while node in self.stack_constraints and i in self.stack_constraints[node]:
			i = i+1
		
		self.symtbl.map(node, i)
		self.propagate_stack_constraints(graph, node, i)

		return i
		

	def allocate_reg(self, node, reg_constraints, graph, todo):
		regamt = len(Register.registers)

		i = 0
		if node in reg_constraints:
			for i in range(0, regamt):
				if i not in reg_constraints[node]:
					break

		if i >= regamt:
			raise Exception("no reg available!")

		self.symtbl.map(node, i)
		self.propagate_reg_constraints(reg_constraints, graph, todo, node, i)
		
		return i


	def next(self, todo, reg_constraints):
		if len(reg_constraints) < 1:
			for node in todo:
				if node.needs_reg == True:
					return (node, False)
	
			return (node, False)
		
		regamt = len(Register.registers)
		to_sort = []
		for (node, v) in reg_constraints.items():
			saturation = len(v)

			#if its already out of the running on a reg
			#there is no need to break ties
			if saturation >= regamt:
				return (node, True)

			to_sort.append( (node, saturation) )


		sorted_items = sorted(to_sort, key = lambda (node, v): v, reverse=True )
		high_score = sorted_items[0][1]

		for (node, score) in sorted_items:
			if node.needs_reg == True:
				return (node, False)

			if score != high_score:
				break

		return (sorted_items[0][0], False)


	def allocate(self, graph):
		reg_constraints = {}
		self.symtbl.boot_reg_dwellers()
		
		reg_nodes = [Register(x) for x in Register.registers]
		todo = set(graph.keys()) - set(self.symtbl.mem_map.keys()) - set(reg_nodes)

		#registers are implicitly allocated to themselves 
		for rnode in reg_nodes:			
			self.propagate_reg_constraints(reg_constraints, graph, todo, rnode, self.symtbl[rnode])
		
		t0 = time.time()

		while len(todo) > 0:
			#log("todo: %s" % repr(self.todo))
			#log("constraints: %s" % repr(self.reg_constraints) )
			
			(node, saturated) = self.next(todo, reg_constraints)
			log("allocate reg for %s" % repr(node) )
			index = \
				self.allocate_stack(node, graph) if saturated \
				else self.allocate_reg(node, reg_constraints, graph, todo)

			log("  allocated %d" % index)
			todo.remove(node)
	
			try:
				del reg_constraints[node]
			except KeyError:
				pass

		if len(reg_constraints) > 0:
			raise Exception("why are constraints non empty?")

		return self.symtbl


def adjust(asm_list, symtbl):
	has_alts = False
	result = []

	for ins in asm_list:
		log(lambda : "set locs in %s" % repr(ins))

		new_ins = patch_insn(ins, symtbl)

		if new_ins == ins:
			result.append(ins)
			continue
		
		log( lambda : "  patched: %s" % repr(new_ins))

		#cant eliminate noops just yet because locations arent set in stone
		#however we also dont want to fix operand violations of the form:
		#  mov -4(%ebp), -4(%ebp)
		#so just continue...
		if new_ins.is_noop(): 
			result.append(ins)
			continue

		alt_insns = new_ins.fix_operand_violations()
		if len(alt_insns) > 0:
			log(lambda : "  replace ins with: \n\t%s" % "\n\t".join([repr(x) for x in alt_insns]) )
			result.extend(alt_insns)
			has_alts = True
		else:
			result.append(ins)
			
	
	return (has_alts, result)


def patch_insn(ins, symtbl):
	result = ins.patch_vars(lambda node: index_to_loc(symtbl[node]) )
	return result

def allocate(asm_list):
	more_alloc_needed = 1
	adjusted_asm_list = asm_list
	allocator = Allocator()

	while more_alloc_needed:
		log("analyze asm nodes and assign memory locations")
		t0 = time.time()
		live_list, graph = pyc_var_analyzer.interference_graph(adjusted_asm_list)
		t_graph = time.time()
		#print "graph time: %d" % (t_graph - t0) 

		t0 = time.time()
		allocator.allocate(graph)
		t_alloc = time.time()
		#print "alloc time: %d" % (t_alloc - t0) 

		log( lambda : "mem allocation offsets:\n\t%s" % str(allocator.symtbl) )
	
		(more_alloc_needed, adjusted_asm_list) = adjust(adjusted_asm_list, allocator.symtbl) 
		
		log( lambda : "adjusted asm list (more_alloc? = %d):\n\t%s" % (more_alloc_needed, "\n\t".join([("%s" % repr(x) ) for x in adjusted_asm_list])) )

	return (adjusted_asm_list, allocator.symtbl)