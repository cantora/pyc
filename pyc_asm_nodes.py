from pyc_log import *
import pyc_gen_name
import copy

def asm_prefix():
	return [
		"pushl   %ebx",
		"pushl   %esi",
		"pushl   %edi",
		"pushl   %ebp",
		"movl    %esp, %ebp"
	]

def asm_suffix():
	return [
		"leave",
		"popl   %edi",
		"popl   %esi",
		"popl   %ebx",
		"ret"
	]
	

class AsmNode:
	def __init__(self):
		self.asm_tab = "\t"

	def __eq__(self, other):
		return str(self).__eq__(str(other))

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return str(self).__hash__()

class CodeBloc:
	def __init__(self, name, insns):
		self.name = name
		self.insns = insns

	def __repr__(self):
		return "\n".join(self.inspect())

	def inspect(self):
		lines = []
		lines.append("%s:" % (self.name) )
		for n in self.insns:
			r_lines = repr(n).split("\n")
			for l in r_lines:
				lines.append("  %s" % l)
		lines.append("end")

		return lines

	def end_label(self):
		return "%s_end" % self.name

class FlatCodeBloc(CodeBloc):
	def __init__(self, name, insns, symtbl):
		self.name = name
		self.insns = insns
		self.symtbl = symtbl

	def to_str(self, io, lamb = lambda s: s):

		for ins in self.insns:
			if not isinstance(ins, Inst):
				raise Exception("expected instruction node")
	
			if isinstance(ins, Return):
				patched = ins.convert(self.end_label())
			else:
				patched = ins.patch_vars(lambda node: self.symtbl.location(node) ) 
			
			if patched.is_noop():
				continue
			
			s = str(patched)
			print >>io, lamb(s)

		print >>io, lamb(str(Mov(Immed(0), Register("eax")) )) #if not return stmt, return 0
		print >>io, lamb(str(Label(self.end_label())))
	
	def to_asm(self, io, lamb = lambda s: s):
		for insn in asm_prefix():
			print >>io, lamb(insn)

		stacksize = self.symtbl.stack()
		align = 16
		if stacksize > 0:
			print >>io, lamb("subl\t$%s, %%esp" % (stacksize + (align - (stacksize % align))))
		
		self.to_str(io, lamb)

		for insn in asm_suffix():
			print >>io, lamb(insn)

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
		#log("patch vars: %r" % self)
		klone = copy.deepcopy(self)

		for name in klone.operand_names():
			#print name
			asm_node = klone.get_operand_node(name)
			if not isinstance(asm_node, Var):
				continue
			if isinstance(asm_node, Register):
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
			instance.beget(Mov, {}, copy.deepcopy(a), temp),
			instance.beget(instance.__class__, {}, temp, copy.deepcopy(b))
		]

	def fix_operand_violations(self):
		return []

	def __repr__(self):
		return common_repr(self.__class__.__name__, *self.operand_nodes() )
		
	def beget(self, klass, dc_memo, *args):
		new_inst = klass(*[copy.deepcopy(x, dc_memo) for x in args] )
		new_inst.origin = self.origin
		return new_inst

	def shallow_beget(self, klass, *args):
		new_inst = klass(*args)
		new_inst.origin = self.origin
		return new_inst

	#works only for instructions where all the data structure 
	#elements are operands
	def __deepcopy__(self, memo):
		return self.beget(self.__class__, memo, *(self.operand_nodes()) )

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

	#def patch_vars(self, mem_map):
	#	return copy.deepcopy(self)

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.name)

	def __deepcopy__(self, memo):
		return self.beget(self.__class__, memo, self.name)

class IndirectCall(Call):
	def __init__(self, name):
		Call.__init__(self, name)
		if not isinstance(self.name, Var):
			raise Exception("name must be a Var")

	def __str__(self):
		return self.inst_join(["call", "*%s" % str(self.name)])

class Cmp(Inst):
	def __init__(self, left, right):
		Inst.__init__(self)
		self.read_operand('left', left)
		self.read_operand('right', right)
	
	def __str__(self):
		a = self.left
		b = self.right
		if isinstance(self.left, Register) and isinstance(self.right, Immed):
			(a,b) = (b,a)
		
		return self.inst_join(["cmpl", "%s, %s" % (str(a), str(b) ) ] )

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
		if Inst.is_mem_to_mem(self.src, self.dest):
			raise Exception("im working on this...")

		#this works because we only alter our use of a memory ref, which will
		#not be reassigned in any allocator passes
		if isinstance(self.src, Register) and isinstance(self.dest, MemoryRef):
			temp = Var(Inst.gen_name(), True)
			return [
				self.beget(self.__class__, {}, copy.deepcopy(self.src), temp),
				self.beget(Mov, {}, temp, copy.deepcopy(self.dest))
			]
		
		return []

class Interrupt(Inst):
	def __init__(self, code):
		Inst.__init__(self)
		self.read_operand('code', code)
		
	def __str__(self):
		return self.inst_join(["int", str(self.code)])


class Jmp(Inst):
	def __init__(self, label):
		Inst.__init__(self)
		self.label = label
		
	def __str__(self):
		return self.inst_join(["jmp", self.label])

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.label)

	def __deepcopy__(self, memo):
		return self.beget(self.__class__, {}, self.label)

	@staticmethod
	def label_str(prefix=""):
		parts = []
		if len(prefix) > 0:
			parts.append(prefix)
		parts.append("label_")

		return pyc_gen_name.new("_".join(parts) )

class Je(Jmp):
	def __init__(self, label):
		Jmp.__init__(self, label)

	def __str__(self):
		return self.inst_join(["je", self.label])
	
class Return(Inst):
	def __init__(self):
		Inst.__init__(self)

	def __str__(self):
		return "Return"

	def __repr__(self):
		return common_repr(self.__class__.__name__)

	def convert(self, label):
		return self.beget(Jmp, {}, label)

def inspect_asm_branch(list, depth=0):
	lines = []
	for ins in list:
		if isinstance(ins, AsmFlow):
			lines.extend(ins.inspect(depth) )
		else:
			lines.append("%s%s" % (" "*depth, repr(ins)) )

	return lines

class AsmFlow(Inst):
	def __init__(self, test):
		Inst.__init__(self)
		self.read_operand('test', test)

	def __repr__(self):
		return "\n".join(self.inspect())

	def patch_vars(self, fn_to_mem_loc):
		raise Exception("cannot patch vars in %r node!" % self.__class__)

	def __deepcopy__(self, memo):
		raise Exception("cannot deepcopy %r" % self.__class__)
	
	def beget_test_compare(self):
		return self.beget(Cmp, {}, Immed(DecInt(0)), self.test)

	@staticmethod
	def patch(asm_list, depth=0):
		result = []
		
		log("patch AsmFlow nodes (%d instructions)" % len(asm_list) )
		for ins in asm_list:
			if isinstance(ins, AsmFlow):
				result.extend(ins.convert(depth))
			else:
				result.append(ins)

		return result

class AsmIf(AsmFlow):
	def __init__(self, test, body, orelse):
		AsmFlow.__init__(self, test)
		self.body = body
		self.orelse = orelse

	def inspect(self, depth=0):
		lines = []
		lines.append("%s%s(%r)" % (" "*depth, self.__class__.__name__, self.test) )
		lines.extend(inspect_asm_branch(self.body, depth+1))
		lines.append("%selse(%r)" % (" "*depth, self.test ) ) 
		lines.extend(inspect_asm_branch(self.orelse, depth+1))
		lines.append("%s%s(%r)" % (" "*depth, self.__class__.__name__ + "_end", self.test) )

		return lines

	def convert(self, depth=0):
		result = []
		else_label = Jmp.label_str("else")
		end_label = Jmp.label_str("end")
		result.extend([
			self.beget_test_compare(),
			self.beget(Je, {}, else_label)
		])

		result.extend(AsmFlow.patch(self.body, depth+1) )

		result.extend([
			self.beget(Jmp, {}, end_label),
			self.beget(Label, {}, else_label)
		])
		result.extend(AsmFlow.patch(self.orelse, depth+1) )
		result.append(self.beget(Label, {}, end_label) )

		return result
		

class AsmDoWhile(AsmFlow):
	def __init__(self, test, tbody, wbody):
		AsmFlow.__init__(self, test)
		self.tbody = tbody
		self.wbody = wbody

	def inspect(self, depth=0):
		lines = []
		lines.append("%s%s(%r)" % (" "*depth, self.__class__.__name__ + "_start", self.test) )
		lines.extend(inspect_asm_branch(self.tbody, depth+1))
		lines.append("%s%s(%r)" % (" "*(depth+1), self.__class__.__name__ + "_test", self.test) )
		lines.extend(inspect_asm_branch(self.wbody, depth+1))
		lines.append("%s%s(%r)" % (" "*depth, self.__class__.__name__ + "_end", self.test) )

		return lines

	def convert(self, depth=0):
		result = []
		start_label = Jmp.label_str("while_start")
		end_label = Jmp.label_str("while_end")

		result.append(self.beget(Label, {}, start_label) )
		result.extend(AsmFlow.patch(self.tbody, depth+1))

		result.extend([
			self.beget_test_compare(),
			self.beget(Je, {}, end_label)
		])

		result.extend(AsmFlow.patch(self.wbody, depth+1) )

		result.extend([
			self.beget(Jmp, {}, start_label),
			self.beget(Label, {}, end_label)
		])

		return result
		
class Label(Inst):
	def __init__(self, s):
		Inst.__init__(self)
		self.s = s

	def __str__(self):
		return "%s:" % self.s

	def __repr__(self):
		return common_repr(self.__class__.__name__, self.s)
		
	def __deepcopy__(self, memo):
		return self.beget(Label, memo, self.s)

class Leave(Inst):
	def __str__(self):
		return "leave"

	def __repr__(self):
		return common_repr(self.__class__.__name__)

class Ret(Inst):
	def __str__(self):
		return "ret"

	def __repr__(self):
		return common_repr(self.__class__.__name__)
		
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
	vars = []
	for x in asm_nodes:
		if isinstance(x, Var):
			if isinstance(x, Register) and hasattr(x, 'parent'):
				vars.append(x.parent())
			else:
				vars.append(x)

	return vars

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
		
class Param(Indirect):
	def __init__(self, n):
		Indirect.__init__(
			self, 
			Register("ebp"), 
			4*4 + 4 + (n*4) #saved ebp, ebx, esi, edi, ret addr
		)
	
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
		return "0x%02x" % self.val

	def __repr__(self):
		return common_repr(self.__class__.__name__, str(self))

class GlobalString(AsmNode):
	cache = {}

	def __init__(self, value):
		AsmNode.__init__(self)
		self.value = value
		if GlobalString.cache.get(value, None) is None:
			GlobalString.cache[value] = pyc_gen_name.new("global_str_")

	def __str__(self):
		return GlobalString.cache[self.value]

	def __repr__(self):
		return common_repr(self.__class__.__name__, GlobalString.cache[self.value], self.value)

	@staticmethod
	def data_headers():
		headers = []
		for (value, name) in GlobalString.cache.items():
			headers.append("%s:\n\t.ascii \"%s\x00\"" % (name, value))

		return headers
		





