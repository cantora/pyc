
import compiler

class Movl(compiler.ast.Node):
	def __init__(self, src, dest):
		self.src = src
		self.dest = dest

class Immed(compiler.ast.Node):
	def __init__(self, node):
		self.node = node

class Register(compiler.ast.Node):
	def __init__(self, name):
		self.name = name

class Indirect(compiler.ast.Node):
	def __init__(self, reg, offset):
		self.reg = reg
		self.offset = offset
		
class Int(compiler.ast.Node):
	def __init__(self, val):
		self.val = val

class Global(compiler.ast.Node):
	def __init__(self, name):
		self.name = name

