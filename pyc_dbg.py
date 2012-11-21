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
			
		self.cmds.append(SIRList(self))
		
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

	