from pyc_var_analyzer import IntfGraph
from pyc_log import *
from pyc_asm_nodes import *
import pyc_var_analyzer 
from pyc_symtable import SymTable

import random
import copy
import time
import Queue

class Allocator:
	def __init__(self):
		self.symtbl = SymTable()
		self.stack_constraints = {}

	def propagate_reg_constraints(self, reg_constraints, graph, node, index):
		for n in graph[node]:
			if n not in reg_constraints:
				continue

			reg_constraints[n].add(index)


	def propagate_stack_constraints(self, graph, node, index):
		for intf_node in graph[node]:
			if intf_node not in self.stack_constraints:
				self.stack_constraints[intf_node] = set([])

			self.stack_constraints[intf_node].add(index)

	def dump_vars_to_stack(self, nodes, graph):
		reg_amt = len(Register.registers)
		i = reg_amt

		for n in nodes:
			if isinstance(n, Register):
				continue

			self.symtbl.map(n, i)
			self.propagate_stack_constraints(graph, n, i)
			i += 1

		return i + 1 - reg_amt
			
	def allocate_stack(self, node, graph):
		if node.needs_reg:
			raise Exception("%s needs a reg!" % repr(node))

		i = len(Register.registers)
		while node in self.stack_constraints and i in self.stack_constraints[node]:
			i = i+1
		
		self.symtbl.map(node, i)
		self.propagate_stack_constraints(graph, node, i)

		return i
		

	def allocate_reg(self, node, reg_constraints, graph):
		regamt = len(Register.registers)

		if node not in reg_constraints:
			raise Exception("node not in reg constraints!")

		i = 0
		for i in range(0, regamt):
			if i not in reg_constraints[node]:
				break

		if i >= regamt:
			raise Exception("no reg available!")

		self.symtbl.map(node, i)
		self.propagate_reg_constraints(reg_constraints, graph, node, i)
		
		return i


	def next(self, reg_constraints):
		if len(reg_constraints) < 1:
			raise Exception("reg_constraints is empty!")
		
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
		for n in todo:
			reg_constraints[n] = set([])		

		#registers are allocated to themselves 
		for rnode in reg_nodes:			
			self.propagate_reg_constraints(reg_constraints, graph, rnode, self.symtbl[rnode])

		t0 = time.time()

		while len(reg_constraints) > 0:
			#log("constraints: %s" % repr(self.reg_constraints) )
			
			(node, saturated) = self.next(reg_constraints)
			log("allocate reg for %s" % repr(node) )
			index = \
				self.allocate_stack(node, graph) if saturated \
				else self.allocate_reg(node, reg_constraints, graph)

			log("  allocated %d" % index)
			del reg_constraints[node]
	
		return self.symtbl

def adjust(asm_list, symtbl, depth=0):
	has_alts = False
	result = []

	for ins in asm_list:

		if isinstance(ins, AsmIf):
			log("%sAsmIf" % (" "*depth) )
			(body_has_alts, adjusted_body) = adjust(ins.body, symtbl, depth+1)
			log("%sAsmIf-else" % (" "*depth) )
			(els_has_alts, adjusted_els) = adjust(ins.orelse, symtbl, depth+1)
			log("%sAsmIf-end" % (" "*depth) )
			if body_has_alts or els_has_alts:
				new_ins = ins.shallow_beget(ins.__class__, ins.test, adjusted_body, adjusted_els)
				result.append(new_ins)			
				has_alts = True
			else:
				result.append(ins)
		elif isinstance(ins, AsmDoWhile):
			log("%sAsmDoWhile-tbody" % (" "*depth) )
			(tbody_has_alts, adjusted_tbody) = adjust(ins.tbody, symtbl, depth+1)
			log("%sAsmDoWhile-wbody" % (" "*depth) )
			(wbody_has_alts, adjusted_wbody) = adjust(ins.wbody, symtbl, depth+1)
			log("%sAsmDoWhile-end" % (" "*depth) )
			if tbody_has_alts or wbody_has_alts:
				new_ins = ins.shallow_beget(ins.__class__, ins.test, adjusted_tbody, adjusted_wbody)
				result.append(new_ins)
				has_alts = True
			else:
				result.append(ins)
		else:	
			log(lambda : "%sset locs in %s" % (" "*depth, repr(ins)) )
			new_ins = patch_insn(ins, symtbl)
	
			if new_ins == ins:
				result.append(ins)
				continue
			
			log( lambda : "%s->patched: %s" % (" "*depth, repr(new_ins) ))
	
			#cant eliminate noops just yet because locations arent set in stone
			#however we also dont want to fix operand violations of the form:
			#  mov -4(%ebp), -4(%ebp)
			#so just continue...
			if new_ins.is_noop(): 
				result.append(ins)
				continue
	
			alt_insns = new_ins.fix_operand_violations()
			if len(alt_insns) > 0:
				log(lambda : "%s->replace ins with: \n\t%s" % (" "*depth, "\n\t".join([repr(x) for x in alt_insns])) )
				result.extend(alt_insns)
				has_alts = True
			else:
				result.append(ins)
			
	
	return (has_alts, result)


def patch_insn(ins, symtbl):
	result = ins.patch_vars(lambda node: symtbl.location(node) )
	return result

#the default allocator algorithm is the 'sudoku' algorithm
#described in the notes. pass no_sudoku as True to use dumb
#allocation that just puts everything on the stack.
#note: sudoku algorithm is still used for spill variables
def allocate(asm_list, no_sudoku=False):
	more_alloc_needed = 1
	adjusted_asm_list = asm_list
	allocator = Allocator()

	while more_alloc_needed:
		log("analyze asm nodes and assign memory locations")
		t0 = time.time()
		graph = pyc_var_analyzer.interference_graph(adjusted_asm_list)
		if no_sudoku:
			allocator.dump_vars_to_stack(graph.keys(), graph)
			no_sudoku = False	

		t_graph = time.time()
		#print "  graph time: %d" % (t_graph - t0) 

		t0 = time.time()
		allocator.allocate(graph)
		t_alloc = time.time()
		#print "  alloc time: %d" % (t_alloc - t0) 

		log( lambda : "mem allocation offsets:\n\t%s" % str(allocator.symtbl) )
		
		t0 = time.time()
		(more_alloc_needed, adjusted_asm_list) = adjust(adjusted_asm_list, allocator.symtbl) 
		#print "  adjust time: %d" % (time.time() - t0)
		log( lambda : "adjusted asm list more_alloc? = %d)" % more_alloc_needed) #:\n\t%s" % (more_alloc_needed, "\n\t".join([("%s" % repr(x) ) for x in adjusted_asm_list])) )

	return (adjusted_asm_list, allocator.symtbl)