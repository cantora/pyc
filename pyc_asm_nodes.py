
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

	def __eq__(self, other):
		if type(other) is type(self):
			return self.__dict__ == other.__dict__
		else:
			return False
		
	def __ne__(self, other):
		return not __eq__(self, other)

class Mov(AsmNode):
	def __init__(self, src, dest):
		AsmNode.__init__(self, src, dest)
		self.src = src
		self.dest = dest

	def __str__(self):
		return self.asm_tab.join(["movl", "%s, %s" % (str(self.src), str(self.dest) )])

		
class Add(AsmNode):
	def __init__(self, left, right):
		AsmNode.__init__(self, left, right)
		self.left = left
		self.right = right

	def __str__(self):
		return self.asm_tab.join(["addl", "%s, %s" % (str(self.left), str(self.right) )])


class Push(AsmNode):
	def __init__(self, operand):
		AsmNode.__init__(self, operand)
		self.operand = operand

	def __str__(self):
		return self.asm_tab.join(["push", str(self.operand)])


class Pop(AsmNode):
	def __init__(self, amt=1):
		AsmNode.__init__(self, amt)
		if amt < 1:
			raise Exception("invalid pop amt: %d" % amt)
		self.amt = amt

	def __str__(self):
		return self.asm_tab.join(["subl", "%s, %s" % ("%esp", str(4*self.amt) ) ] )
		
class Neg(AsmNode):
	def __init__(self, operand):
		AsmNode.__init__(self, operand)
		self.operand = operand

	def __str__(self):
		return self.asm_tab.join(["negl", str(self.operand)])


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


class Call(AsmNode):
	def __init__(self, name):
		AsmNode.__init__(self, name)
		self.name = name

	def __str__(self):
		return self.asm_tab.join(["call", self.name])



