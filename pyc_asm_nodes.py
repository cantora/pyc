
import compiler


class OperandDesc():
	pass	

class StaticOperandDesc(OperandDesc):
	def __repr__(self):
		return "$$$"

class VarOperandDesc(OperandDesc):

	READ = 'read'
	WRITE = 'write'

	def __init__(self, operand, modes):
		self.operand = operand

		self.modes = set(modes)
		for mode in modes:
			if mode not in (VarOperandDesc.READ, VarOperandDesc.WRITE):
				raise Exception("invalid mode: %s" % mode)

	def __repr__(self):
		return "OperandDesc(%s, %s)" % (repr(self.operand), repr(self.modes))


def desc_read(asm_node):
	return desc(asm_node, [VarOperandDesc.READ])

def desc_write(asm_node):
	return desc(asm_node, [VarOperandDesc.WRITE])

def desc_rw(asm_node):
	return desc(asm_node, [VarOperandDesc.READ, VarOperandDesc.WRITE]) 

def desc(asm_node, modes):
	if isinstance(asm_node, Var):
		return VarOperandDesc(asm_node, modes)
	elif isinstance(asm_node, Immed):
		return StaticOperandDesc()

	raise Exception("unexpected asm_node type: %s" % repr(asm_node))


class AsmNode(compiler.ast.Node):
	def __init__(self, *args):
		self.con_args = args
		self.asm_tab = "\t"

	def __repr__(self):
		tup = tuple([self.__class__.__name__] + [repr(x) for x in self.con_args])
		arg_fmt = ", ".join(["%s" for x in self.con_args])
		fmt = "%%s(%s)" % arg_fmt
		return fmt % tup

	def __eq__(self, other):
		if type(other) is type(self):
			return self.__dict__ == other.__dict__
		else:
			return False
		
	def __ne__(self, other):
		return not __eq__(self, other)


class Inst(AsmNode):
	def operands(self):
		return []

	def inst_join(self, list):
		return self.asm_tab.join(list)

	def writes(self):
		return []

	def reads(self):
		return []

class Mov(Inst):
	def __init__(self, src, dest):
		Inst.__init__(self, src, dest)
		self.src = src
		self.dest = dest

	def __str__(self):
		return self.inst_join(["movl", "%s, %s" % (str(self.src), str(self.dest) )])

	def operands(self):
		return [self.reads()[0], self.writes()[0]]

	def reads(self):
		return [desc_read(self.src)]

	def writes(self):
		return [desc_write(self.dest)]
		

class Add(Inst):
	def __init__(self, left, right):
		Inst.__init__(self, left, right)
		self.left = left
		self.right = right

	def __str__(self):
		return self.inst_join(["addl", "%s, %s" % (str(self.left), str(self.right) )])

	def operands(self):
		return [desc_read(self.left), self.writes()[0]]

	def reads(self):
		return self.operands()

	def writes(self):
		return [desc_rw(self.right)]


class Push(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.operand = operand

	def __str__(self):
		return self.inst_join(["push", str(self.operand)])

	def operands(self):
		return [desc_read(self.operand)]

	def reads(self):
		return self.operands()

class Pop(Inst):
	def __init__(self, amt=1):
		Inst.__init__(self, amt)
		if amt < 1:
			raise Exception("invalid pop amt: %d" % amt)
		self.amt = amt

	def __str__(self):
		return self.inst_join(["subl", "%s, %s" % ("%esp", str(4*self.amt) ) ] )

	def operands(self):
		return [desc_read( Immed(Int(self.amt)) )]


class Neg(Inst):
	def __init__(self, operand):
		Inst.__init__(self, operand)
		self.operand = operand

	def __str__(self):
		return self.inst_join(["negl", str(self.operand)])

	def operands(self):
		return [desc_rw(self.operand)]

	def reads(self):
		return self.operands()

	def writes(self):
		return self.operands()


class Call(Inst):
	def __init__(self, name):
		Inst.__init__(self, name)
		self.name = name

	def __str__(self):
		return self.inst_join(["call", self.name])

	def writes(self):
		return [desc_write(Register(x)) for x in ["eax", "ecx", "edx"] ]


class Immed(AsmNode):
	def __init__(self, node):
		AsmNode.__init__(self, node)
		self.node = node

	def __str__(self):
		return "$%s" % str(self.node)

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





