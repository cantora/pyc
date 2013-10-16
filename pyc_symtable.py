# Copyright 2013 anthony cantor
# This file is part of pyc.
# 
# pyc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#  
# pyc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#  
# You should have received a copy of the GNU General Public License
# along with pyc.  If not, see <http://www.gnu.org/licenses/>.
from pyc_asm_nodes import *
from pyc_log import *

class SymTable:
	
	def __init__(self):
		self.mem_map = {}
		self.swaps = set([])

		#registers are like variables for which we must allocate
		#themselves
		for i in range(0, len(Register.registers)):
			self.map(Register(Register.registers[i]), i)
	
	@staticmethod
	def from_map(map):
		symtbl = SymTable()
		symtbl.mem_map = map

		return symtbl		

	def location(self, x):
		index = self[x]
		if index < 0:
			raise Exception("invalid index %d" % index)
		elif index < len(Register.registers):
			return Register(Register.registers[index])
		else:
			return EBPIndirect( (index - len(Register.registers))*4 )

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
