
import pyc_gen_name
import copy


class AsmNode:
	def __init__(self):
		self.asm_tab = "\t"

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

def common_repr(klass_name, *args):
	tup = (klass_name,) + args
	arg_fmt = ", ".join(["%s"]*len(args) )
	fmt = "%%s(%s)" % arg_fmt
	return fmt % tup

class Inst(AsmNode):

	op_modes = {
		'r': ReadOperand, 
		'w': WriteOperand, 
		'rw': RWOperand
	}

	def __init__(self):
		AsmNode.__init__(self)
		self.origin = None	
		self.operand_props = {}
		self.operand_order = []

	def is_noop(self):
		return False

	@staticmethod
	def gen_name():
		return pyc_gen_name.new("temp_op")

	def new_operand(self, name, operand, mode):
		if mode not in self.op_modes.keys():
			raise Exception("invalid operand mode: %s" % repr(mode))

		self.operand_props[name] = mode
		setattr(self, name, operand)
		self.operand_order.append(name)
		
	def get_operand(self, name):
		return self.op_modes[self.operand_props[name]](self.get_operand_node(name))

	def get_operand_node(self, name):
		return self.__dict__[name]

	def operand_names(self):
		return self.operand_order

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
		return "\t".join(list)

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
		klone = copy.deepcopy(self)

		for name in klone.operand_names():
			#print name
			asm_node = klone.get_operand_node(name)
			if not isinstance(asm_node, Var):
				continue
			
			#print("patch op %s" % repr(name))
			setattr(klone, name, fn_to_mem_loc(asm_node) )

		return klone


	@staticmethod
	def is_mem_to_mem(op1, op2):
		return isinstance(op1, MemoryRef) and isinstance(op2, MemoryRef)
	
	@staticmethod
	def fix_two_op_operand_violation(instance, op_a, op_b):
		a = getattr(instance, op_a)
		b = getattr(instance, op_b)
		if not Inst.is_mem_to_mem(a, b):
			return []

		temp = Var(Inst.gen_name(), True)
		return [
			instance.beget(Mov, copy.deepcopy(a), temp),
			instance.beget(instance.__class__, temp, copy.deepcopy(b))
		]

	def fix_operand_violations(self):
		return []

	def __repr__(self):
		return common_repr(self.__class__.__name__, *self.operand_nodes() )
		
	def beget(self, klass, *args):
		new_inst = klass(*args)
		new_inst.origin = self.origin
		return new_inst
		

class Mov(Inst):
	def __init__(self, src, dest):
		Inst.__init__(self)
		self.read_operand('src', src)
		self.write_operand('dest', dest)

	def __str__(self):
		return self.inst_join(["movl", "%s, %s" % (str(self.src), str(self.dest) )])

	def fix_operand_violations(self):
		return Inst.fix_two_op_operand_violation(self, 'src', 'dest')

	def is_noop(self):
		if self.src == self.dest:
			return True

		return False
		
	
class Add(Inst):
	def __init__(self, left, right):
		Inst.__init__(self)
		self.read_operand('left', left)
		self.read_write_operand('right', right)

	def __str__(self):
		return self.inst_join(["addl", "%s, %s" % (str(self.left), str(self.right) )])

	def fix_operand_violations(self):
		return Inst.fix_two_op_operand_violation(self, 'left', 'right')


class Push(Inst):
	def __init__(self, operand):
		Inst.__init__(self)
		self.read_operand('operand', operand)

	def __str__(self):
		return self.inst_join(["push", str(self.operand)])

class Pop(Inst):
	def __init__(self, operand):
		Inst.__init__(self)
		self.write_operand('operand', operand)
		
	def __str__(self):
		return self.inst_join(["pop", str(self.operand)])


class Neg(Inst):
	def __init__(self, operand):
		Inst.__init__(self)
		self.read_write_operand('operand', operand)

	def __str__(self):
		return self.inst_join(["negl", str(self.operand)])

class Call(Inst):
	def __init__(self, name):
		Inst.__init__(self)
		self.name = name

	def __str__(self):
		return self.inst_join(["call", self.name])

	def writes(self):
		return [Register(x) for x in Register.caller_save ]

	def patch_vars(self, mem_map):
		return self.beget(Call, self.name)

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.name)


class Cmp(Inst):
	def __init__(self, left, right):
		Inst.__init__(self)
		self.read_operand('left', left)
		self.read_operand('right', right)
	
	def __str__(self):
		return self.inst_join(["cmpl", "%s, %s" % (str(self.left), str(self.right) ) ] )

	def fix_operand_violations(self):
		return Inst.fix_two_op_operand_violation(self, 'left', 'right')

class Sete(Inst):
	def __init__(self, dest):
		Inst.__init__(self)
		self.write_operand('dest', dest)

	def __str__(self):
		return self.inst_join(["sete", str(self.dest)])

	def fix_operand_violations(self):
		if isinstance(self.dest, CuteReg):
			return []

		raise Exception("ohnos!")

class Setne(Sete):
	def __init__(self, dest):
		Sete.__init__(self, dest)

	def __str__(self):
		return self.inst_join(["setne", str(self.dest)])

class Movzbl(Inst):
	def __init__(self, src, dest):
		Inst.__init__(self)
		self.read_operand('src', src)
		self.write_operand('dest', dest)

	def __str__(self):
		return self.inst_join(["movzbl", "%s, %s" % (str(self.src), str(self.dest) ) ] )

	def fix_operand_violations(self):
		if not Inst.is_mem_to_mem():
			return []

		raise Exception("im working on this...")

class Interrupt(Inst):
	def __init__(self, code):
		Inst.__init__(self)
		self.read_operand('code', code)
		
	def __str__(self):
		return self.inst_join(["int", str(code)])


class AsmIf(Inst):
	def __init__(self, test, body, orelse):
		Inst.__init__(self)
		self.test = test
		self.body = body
		self.orelse = orelse

	def __repr__(self):
		return "\n".join(self.inspect())

	def inspect(self, depth=0):
		lines = []
		lines.append("%s%s(%r)" % (" "*depth, self.__class__.__name__, self.test) )
		lines.extend(self.inspect_branch(self.body, depth+1))
		lines.extend(self.inspect_branch(self.orelse, depth+1))
		lines.append("%send(%r)" % (" "*depth, self.test) )

		return lines

	def inspect_branch(self, list, depth=0):
		lines = []
		for ins in list:
			if isinstance(ins, AsmIf):
				lines.extend(ins.inspect(depth) )
			else:
				lines.append("%s%s" % (" "*depth, repr(ins)) )

		return lines
			
#END INSTRUCTIONS

class Immed(AsmNode):
	def __init__(self, node):
		AsmNode.__init__(self)
		self.node = node

	def __str__(self):
		return "$%s" % str(self.node)

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.node)

def get_vars(asm_nodes):
	return [x for x in asm_nodes if isinstance(x, Var)]

class Var(AsmNode):
	def __init__(self, name, needs_reg=False):
		AsmNode.__init__(self)
		self.name = name
		self.needs_reg = needs_reg

	def __str__(self):
		return self.name

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.name)

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

#awwww.... your just one lil byte arentcha?
class CuteReg(Register):
	
	def __init__(self, name):
		Register.__init__(self, name)
	
	def parent(self):
		map = {
			"a": "eax",
			"b": "ebx",
			"c": "ecx",
			"d": "edx"
		}

		return Register(map[self.name[0:1]])


class MemoryRef(AsmNode):
	pass

class Indirect(MemoryRef):
	def __init__(self, reg, offset):
		MemoryRef.__init__(self)
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
		
	def __repr__(self):
		return common_repr(self.__class__.__name__, self.reg, self.offset)
	
"""
an offset of 0 => -4(%ebp)
an offset of 4 => -8(%ebp)
...
an offset of N => -(4+N)(%ebp)
"""
class EBPIndirect(Indirect):
	def __init__(self, offset):
		Indirect.__init__(self, Register("ebp"), offset)

	def __str__(self):
		return self._to_s(-(self.offset+4) )
		
		
class DecInt(AsmNode):
	def __init__(self, val):
		AsmNode.__init__(self)
		self.val = val

	def __str__(self):
		return str(self.val)

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.val)

class HexInt(AsmNode):
	def __init__(self, val):
		AsmNode.__init__(self)
		self.val = val

	def __str__(self):
		return "%02x" % self.val

	def __repr__(self):
		return common_repr(self.__class__.__name__, str(self))

class GlobalString(AsmNode):
	def __init__(self, value):
		AsmNode.__init__(self)
		self.name = pyc_gen_name.new("global_str_")
		self.value = value

	def __str__(self):
		return self.name

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.name, self.value)






