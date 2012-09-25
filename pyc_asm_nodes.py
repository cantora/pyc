
import compiler

class AsmNode(compiler.ast.Node):
	def __init__(self, *args):
		self.con_args = args
		self.asm_tab = "\t"

	def __repr__(self):
		tup = tuple([self.__class__.__name__] + [repr(x) for x in self.con_args])
		arg_fmt = ", ".join(["%s" for x in range(0, len(self.con_args) )])
		fmt = "%%s(%s)" % arg_fmt
		return fmt % tup

	def __eq__(self, other):
		if type(other) is type(self):
			return self.__dict__ == other.__dict__
		else:
			return False
		
	def __ne__(self, other):
		return not __eq__(self, other)


class Operand:
	def __init__(self, asm_node):
		self.asm_node = asm_node

	def isstatic(self):
		if isinstance(self.asm_node, Immed):
			return True

		return False

class ReadOperand(Operand):
	pass

class WriteOperand(Operand):
	pass

class RWOperand(ReadOperand, WriteOperand):
	pass

class Inst(AsmNode):

	op_modes = {
		'r': ReadOperand, 
		'w': WriteOperand, 
		'rw': RWOperand
	}

	def __init__(self, *args):
		AsmNode.__init__(self, *args)
		
		self.operand_props = {}

	def new_operand(self, name, operand, mode):
		if mode not in self.op_modes.keys():
			raise Exception("invalid operand mode: %s" % repr(mode))

		self.operand_props[name] = mode
		setattr(self, name, operand)
		
	def get_operand(self, name):
		return self.op_modes[self.operand_props[name]](self.get_operand_node(name))

	def get_operand_node(self, name):
		return self.__dict__[name]

	def operand_names(self):
		return reversed(self.operand_props.keys())

	def read_operand(self, name, asm_node):
		self.new_operand(name, asm_node, 'r')
	
	def write_operand(self, name, asm_node):
		self.new_operand(name, asm_node, 'w')

	def read_write_operand(self, name, asm_node):
		self.new_operand(name, asm_node, 'rw')

	def operands(self):
		return [self.get_operand(name) for name in self.operand_names()]

	def operand_nodes(self):
		return [self.get_operand_node(name) for name in self.operand_names()]

	def inst_join(self, list):
		return self.asm_tab.join(list)

	def read_operands(self):
		return self.get_operands('r')

	def write_operands(self):
		return self.get_operands('w')

	def read_write_operands(self):
		return self.get_operands('rw')

	def get_operands(self, filter_mode):
		return [self.get_operand(name) for (name, mode) in self.operand_props.items() if mode == filter_mode]

	def writes(self):
		return [op.asm_node for op in (self.write_operands() + self.read_write_operands()) ]

	def reads(self):
		return [op.asm_node for op in self.read_operands() + self.read_write_operands()]

	def patch_vars(self, fn_to_mem_loc):
		args = []

		for name in self.operand_names():
			#print name
			asm_node = self.get_operand_node(name)
			if not isinstance(asm_node, Var):
				args.append(asm_node)
				continue
			
			#print("patch op %s" % repr(name))
			args.append(fn_to_mem_loc(asm_node) )

		return self.__class__(*args)


"""
	def sub_loc_for_var(self, mem_map):
		if isinstance(self.src, Var):
			self.src = mem_map(self.src)

		if isinstance(self.dest, Var):
			self.dest = mem_map(self.dest)
		
		return True
"""

class Mov(Inst):
	def __init__(self, src, dest):
		Inst.__init__(self, src, dest)
		self.read_operand('src', src)
		self.write_operand('dest', dest)

	def __str__(self):
		return self.inst_join(["movl", "%s, %s" % (str(self.src), str(self.dest) )])

		
class Add(Inst):
	def __init__(self, left, right):
		Inst.__init__(self, left, right)
		self.read_operand('left', left)
		self.read_write_operand('right', right)

	def __str__(self):
		return self.inst_join(["addl", "%s, %s" % (str(self.left), str(self.right) )])


class Push(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.read_operand('operand', operand)

	def __str__(self):
		return self.inst_join(["push", str(self.operand)])


class Pop(Inst):
	def __init__(self, amt=1):
		Inst.__init__(self, amt)
		if amt < 1:
			raise Exception("invalid pop amt: %d" % amt)
		self.amt = amt
		
	def __str__(self):
		return self.inst_join(["subl", "%s, %s" % ("%esp", str(4*self.amt) ) ] )


class Neg(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.read_write_operand('operand', operand)

	def __str__(self):
		return self.inst_join(["negl", str(self.operand)])

class Call(Inst):
	def __init__(self, name):
		Inst.__init__(self, name)
		self.name = name

	def __str__(self):
		return self.inst_join(["call", self.name])

	def writes(self):
		return [Register(x) for x in ["eax", "ecx", "edx"] ]


class Immed(AsmNode):
	def __init__(self, node):
		AsmNode.__init__(self, node)
		self.node = node

	def __str__(self):
		return "$%s" % str(self.node)

def get_vars(asm_nodes):
	return [x for x in asm_nodes if isinstance(x, Var)]

class Var(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name

	def __str__(self):
		return self.name

	def __eq__(self, other):
		return str(self).__eq__(str(other))

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return str(self).__hash__()


class Register(Var):
	def __init__(self, name):
		Var.__init__(self, name)

	def __str__(self):
		return "%%%s" % self.name

class Indirect(AsmNode):
	def __init__(self, reg, offset):
		AsmNode.__init__(self, reg, offset)
		if isinstance(reg, Register) != True:
			raise Exception("invalid register: %s" % reg.__class__.__name__)
			
		self.reg = reg
		self.offset = offset

	def __str__(self):
		return self._to_s(self.offset)

	def _to_s(self, offset):
		off_str = ""
		if offset != 0:
			off_str = str(offset)

		s = "%s(%s)" % (off_str, str(self.reg))

		return s
		

"""
an offset of 0 => -4(%ebp)
an offset of 4 => -8(%ebp)
...
an offset of N => -(4+N)(%ebp)
"""
class EBPIndirect(Indirect):
	def __init__(self, offset):
		Indirect.__init__(self, Register("ebp"), offset)
		AsmNode.__init__(self, offset)

	def __str__(self):
		return self._to_s(-(self.offset+4) )
		
		
class Int(AsmNode):
	def __init__(self, val):
		AsmNode.__init__(self, val)
		self.val = val

	def __str__(self):
		return str(self.val)

class Global(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name





