
#designed to swap variables between registers. not sure if its really useful

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