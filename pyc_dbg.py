import gdb
#from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits
import distorm3
import pyc_dbg_elf
from pyc_log import *

class PycCmd(gdb.Command):
	
	def __init__ (self, state, name, type):
		self.state = state
		self.name = self.state.cmd_name(name)
		super (PycCmd, self).__init__(self.name, type)

class CodeOutsideScope(Exception):
	"""
	we tried to determine pyc context outside of a
	pyc defined x86 instruction
	"""
	pass
	
class State(object):
	
	def __init__(self, **kwargs):
		for attr in ('file', 'cmd_prefix', 'input'):
			setattr(self, attr, kwargs[attr])

		self.init_cmds()
		self.extract_from_bin()

	def extract_from_bin(self):
		try:
			with open(self.file, 'r') as f:
				self.dbg_map = pyc_dbg_elf.extract_from_bin(f)
		except pyc_dbg_elf.ElfError as e:
			raise Exception("invalid binary '%s': %s" % (self.file, e))
		
	def frame_to_linenos(self, frame):
		if not frame.is_valid():
			raise Exception("expected valid frame")
		if frame.type() != gdb.NORMAL_FRAME:
			raise Exception("expected frame.type == NORMAL_FRAME. got: %s" % frame.type())
		if frame.name() is None:
			raise Exception("frame has no name!")
		if frame.name() not in self.dbg_map['blocs']:
			raise CodeOutsideScope("this is not a pyc frame")

		bloc = self.dbg_map['blocs'][frame.name()]
		if frame.pc() < bloc['addr']:
			raise Exception("frame.pc < bloc['addr']")
		elif frame.pc() == bloc['addr']:
			return (bloc['insns'][0]['src_lineno'], bloc['insns'][0]['sir_lineno'])

		inf = gdb.selected_inferior()
		buf = inf.read_memory(bloc['addr'], frame.pc() - bloc['addr'])
		il = Decode(bloc['addr'], buf, Decode32Bits)
		l = len(il)

		return (bloc['insns'][l]['src_lineno'], bloc['insns'][l]['sir_lineno'])

	def blocs(self):
		return self.dbg_map['blocs'].keys()

	def src(self):
		return self.dbg_map['src']

	def sir_src(self):
		return self.dbg_map['sir_src']

	def cmd_name(self, cmd):
		return "%s-%s" % (self.cmd_prefix, cmd)

	def init_cmds(self):
		self.cmds = []
		
		class Functions(PycCmd):
			"""list the x86 functions from user functions/lambdas/methods."""
	
			def __init__ (self, state):
				super (Functions, self).__init__(state, "functions", gdb.COMMAND_FILES)
			
			def invoke (self, arg, from_tty):
				for bloc in self.state.blocs():
					print bloc
			
		self.cmds.append(Functions(self))

		class List(PycCmd):
			"""list the source code."""
	
			def __init__ (self, state):
				super (List, self).__init__(state, "list", gdb.COMMAND_FILES)
			
			def invoke (self, arg, from_tty):
				print self.state.src()
			
		self.cmds.append(List(self))
		
		class SIRList(PycCmd):
			"""list the sir source code."""
			
			def __init__ (self, state):
				super (SIRList, self).__init__(state, "sir-list", gdb.COMMAND_FILES)
			
			def invoke (self, arg, from_tty):
				print self.state.sir_src()
#				for i in range(lineno-5, lineno+(output_size-5)):
#					if i == lineno:
#						print "%s <<-------------------" % lines[i]
#					else:
#						print lines[i]
			
		self.cmds.append(SIRList(self))

		class Context(PycCmd):
			"""list the user and sir source context"""

			output_size = 15

			def __init__ (self, state):
				super (Context, self).__init__(state, "context", gdb.COMMAND_RUNNING)
			
			def invoke (self, arg, from_tty):
				try:
					frame = gdb.selected_frame()
				except gdb.error:
					frame = None

				if frame is None:
					print "no active frame"
					return

				try:
					(src_lineno, sir_lineno) = self.state.frame_to_linenos(frame)
				except CodeOutsideScope:
					print "active frame is not a pyc frame"
					return 

				log("%s(%s) => (%d, %d)" % (frame.name(), hex(frame.pc()), src_lineno, sir_lineno) )
				src_lines = self.state.src().split('\n')
				sir_lines = self.state.sir_src().split('\n')

				log(repr(src_lines))
				if src_lineno < 1:
					log("Asdf")
					src_lineno = 1
					while src_lines[src_lineno-1].strip() == '':
						log("Qwer")
						src_lineno += 1

				if sir_lineno < 1:
					sir_lineno = 1

				log("%s(%s) => (%d, %d)" % (frame.name(), hex(frame.pc()), src_lineno, sir_lineno) )
				print src_lines[src_lineno-1]
				print sir_lines[sir_lineno-1]

		self.cmds.append(Context(self))

		class Cmds(PycCmd):
			"""list pyc related gdb commands"""
	
			def __init__ (self, state):
				super (Cmds, self).__init__(state, "cmds", gdb.COMMAND_SUPPORT)
			
			def invoke (self, arg, from_tty):
				for cmd in self.state.cmds:
					print("%s %s" % (cmd.name.ljust(15), cmd.__doc__ ) )
				
		self.cmds.append(Cmds(self))

def init(opts):
	if opts.verbose == True:
		log_set_verbose()
	else:
		log_set_quiet()

	log("opts: %r" % (opts.__dict__))
	
	state = State(**(opts.__dict__))

	