from pyc_var_analyzer import IntfGraph
from pyc_log import *
from pyc_asm_nodes import *

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

"""
class ConstraintDict(dict):

	def __getitem__(self, arg):
		if not arg in self:
			self[arg] = set([])
		
		return dict.__getitem__(self, arg)
"""

class Allocator:
	def __init__(self, live_list, graph, symtbl, timeout=0):
		self.live_list = live_list
		self.graph = graph
		self.symtbl = symtbl
		self.symtbl.boot_reg_dwellers()
		self.constraints = {}
		self.timeout = timeout

		reg_nodes = [Register(x) for x in Register.registers]
		self.todo = set(self.graph.keys()) - set(self.symtbl.mem_map.keys()) - set(reg_nodes)
		
		for node in reg_nodes:
			self.propagate_constraints(node, self.symtbl[node])
		

	def propagate_constraints(self, node, index):
		for intf_node in self.graph[node]:
			if intf_node not in self.todo:
				continue

			if intf_node not in self.constraints:
				self.constraints[intf_node] = set([])

			self.constraints[intf_node].add(index)
		
		
	def allocate_mem(self, node):
		log("allocate memory for %s" % repr(node) )
		i = 0
		while node in self.constraints and i in self.constraints[node]:
			i = i+1

		if node.needs_reg and i > (len(Register.registers) - 1):
			raise Exception("%s needs a reg!" % repr(node))

		self.symtbl.map(node, i)
		self.propagate_constraints(node, i)
		
		log("  allocated %d" % i)
		self.todo.remove(node)
	
		try:
			del self.constraints[node]
		except KeyError:
			pass

		return i

	def next(self):
		if len(self.constraints) < 1:
			for node in self.todo:
				if node.needs_reg == True:
					return node
	
			return node
		
		to_sort = [(node, len(self.graph[node]) - len(v)) for (node, v) in self.constraints.items() ]
		sorted_items = sorted(to_sort, key = lambda (node, v): v )
		low_score = sorted_items[0][1]

		for (node, score) in sorted_items:
			if node.needs_reg == True:
				return node

			if score != low_score:
				break

		return sorted_items[0][0]

	def throw_the_rest_on_the_stack(self):
		i = self.symtbl.high_index() + 1
		for node in self.todo:
			if node.needs_reg and i > (len(Register.registers) - 1):
				raise Exception("%s needs a reg!" % repr(node))
	
			self.symtbl.map(node, i)
			i = i+1

		self.constraints.clear()
		self.todo.clear()
				

	def run(self):
		t0 = time.time()

		while len(self.todo) > 0:
			log("todo: %s" % repr(self.todo))
			log("constraints: %s" % repr(self.constraints) )
			
			self.allocate_mem(self.next())
			if self.timeout > 0 and (time.time() - t0) > self.timeout:
				self.throw_the_rest_on_the_stack()
				break


		return self.symtbl


def alloc(live_list, graph, symtbl, timeout=0):
	al = Allocator(live_list, graph, symtbl, timeout)

	return al.run()


def adjust(asm_list, symtbl):
	has_alts = False
	result = []

	for ins in asm_list:
		log(lambda : "set locs in %s" % repr(ins))

		new_ins = patch_insn(ins, symtbl)

		if new_ins == ins:
			result.append(new_ins)
			continue
		
		log( lambda : "  patched: %s" % repr(new_ins))

		if new_ins.is_noop():
			continue

		alt_insns = new_ins.fix_operand_violations()
		if len(alt_insns) > 0:
			log(lambda : "  replace ins with: \n\t%s" % "\n\t".join([repr(x) for x in alt_insns]) )
			result.extend(alt_insns)
			has_alts = True
		else:
			result.append(new_ins)
			
	
	return (has_alts, result)


def patch_insn(ins, symtbl):
	return ins.patch_vars(lambda node: index_to_loc(symtbl[node]) )