
import compiler
import pyc_gen_name
import copy


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
		return str(self).__eq__(str(other))

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return str(self).__hash__()


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
		self.origin = None		
		self.operand_props = {}

	def is_noop(self):
		return False

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

		result = self.__class__(*args)
		result.origin = self.origin
		return result

	@staticmethod
	def is_mem_to_mem(op1, op2):
		return isinstance(op1, MemoryRef) and isinstance(op2, MemoryRef)

	def fix_operand_violations(self):
		return []

class Mov(Inst):
	def __init__(self, src, dest):
		Inst.__init__(self, src, dest)
		self.read_operand('src', src)
		self.write_operand('dest', dest)

	def __str__(self):
		return self.inst_join(["movl", "%s, %s" % (str(self.src), str(self.dest) )])

	def fix_operand_violations(self):
		if not Inst.is_mem_to_mem(self.src, self.dest):
			return []

		temp = Var(pyc_gen_name.new(), True)
		result = [
			Mov(self.src, temp),
			Mov(temp, self.dest)
		]
		result[0].origin = self.origin
		result[1].origin = self.origin
		return result

	def is_noop(self):
		if self.src == self.dest:
			return True

		return False
		
	
class Add(Inst):
	def __init__(self, left, right):
		Inst.__init__(self, left, right)
		self.read_operand('left', left)
		self.read_write_operand('right', right)

	def __str__(self):
		return self.inst_join(["addl", "%s, %s" % (str(self.left), str(self.right) )])

	def fix_operand_violations(self):
		if not Inst.is_mem_to_mem(self.left, self.right):
			return []

		temp = Var(pyc_gen_name.new(), True)
		result = [
			Mov(self.left, temp),
			Add(temp, self.right)
		]
		result[0].origin = self.origin
		result[1].origin = self.origin
		return result


class Push(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.read_operand('operand', operand)

	def __str__(self):
		return self.inst_join(["push", str(self.operand)])

class Pop(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.write_operand('operand', operand)
		
	def __str__(self):
		return self.inst_join(["pop", str(self.operand)])


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
		return [Register(x) for x in Register.caller_save ]

	def patch_vars(self, mem_map):
		return copy.copy(self)

class Immed(AsmNode):
	def __init__(self, node):
		AsmNode.__init__(self, node)
		self.node = node

	def __str__(self):
		return "$%s" % str(self.node)

def get_vars(asm_nodes):
	return [x for x in asm_nodes if isinstance(x, Var)]

class Var(AsmNode):
	def __init__(self, name, needs_reg=False):
		AsmNode.__init__(self, name)
		self.name = name
		self.needs_reg = needs_reg

	def __str__(self):
		return self.name


class Register(Var):
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

	def __init__(self, name):
		Var.__init__(self, name)

	def __str__(self):
		return "%%%s" % self.name

class MemoryRef(AsmNode):
	pass

class Indirect(MemoryRef):
	def __init__(self, reg, offset):
		MemoryRef.__init__(self, reg, offset)
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

#class Global(MemoryRef):
#	def __init__(self, name):
#		MemoryRef.__init__(self, name)
#		self.name = name





