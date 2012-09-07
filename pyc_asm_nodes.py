
import compiler

class AsmNode(compiler.ast.Node):
	def __init__(self, *args):
		self.con_args = args
		self.asm_tab = "\t"

	def __repr__(self):
		tup = tuple([self.__class__.__name__] + [repr(x) for x in self.con_args])
		arg_fmt = ", ".join(["%s" for x in self.con_args])
		fmt = "%%s(%s)" % arg_fmt
		return fmt % tup


class Mov(AsmNode):
	def __init__(self, src, dest):
		AsmNode.__init__(self, src, dest)
		self.src = src
		self.dest = dest

	def to_s(self):
		return self.asm_tab.join(["movl", "%s, %s" % (self.src.to_s(), self.dest.to_s() )])

		
class Add(AsmNode):
	def __init__(self, left, right):
		AsmNode.__init__(self, left, right)
		self.left = left
		self.right = right

	def to_s(self):
		return self.asm_tab.join(["addl", "%s, %s" % (self.left.to_s(), self.right.to_s() )])


class Push(AsmNode):
	def __init__(self, operand):
		AsmNode.__init__(self, operand)
		self.operand = operand

	def to_s(self):
		return self.asm_tab.join(["push", self.operand.to_s()])


class Pop(AsmNode):
	def __init__(self, amt=1):
		AsmNode.__init__(self, amt)
		if amt < 1:
			raise Exception("invalid pop amt: %d" % amt)
		self.amt = amt

	def to_s(self):
		return self.asm_tab.join(["subl", "%s, %s" % ("%esp", str(4*self.amt) ) ] )
		
class Neg(AsmNode):
	def __init__(self, operand):
		AsmNode.__init__(self, operand)
		self.operand = operand

	def to_s(self):
		return self.asm_tab.join(["neg", self.operand.to_s()])


class Immed(AsmNode):
	def __init__(self, node):
		AsmNode.__init__(self, node)
		self.node = node

	def to_s(self):
		return "$%s" % self.node.to_s()


class Register(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name

	def to_s(self):
		return "%%%s" % self.name

class Indirect(AsmNode):
	def __init__(self, reg, offset):
		AsmNode.__init__(self, reg, offset)
		if isinstance(reg, Register) != True:
			raise Exception("invalid register: %s" % reg.__class__.__name__)
			
		self.reg = reg
		self.offset = offset

	def to_s(self):
		return self._to_s(self.offset)

	def _to_s(self, offset):
		off_str = ""
		if offset != 0:
			off_str = str(offset)

		s = "%s(%s)" % (off_str, self.reg.to_s())

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

	def to_s(self):
		return self._to_s(-(self.offset+4) )
		
		
class Int(AsmNode):
	def __init__(self, val):
		AsmNode.__init__(self, val)
		self.val = val

	def to_s(self):
		return str(self.val)

class Global(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name


class Call(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name

	def to_s(self):
		return self.asm_tab.join(["call", self.name])



