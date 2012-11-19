import gdb
import elftools
#from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits
import distorm3

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

	#def extract_from_bin(self):
	#	with open(self.file, 'r') as f:
	#		elffile = ELFFile(f)
		
	def cmd_name(self, cmd):
		return "%s-%s" % (self.cmd_prefix, cmd)

	def init_cmds(self):
		self.cmds = []
		
		class Blocks(PycCmd):
			"""list the code blocks (functions) of user functions/lambdas/methods."""
	
			def __init__ (self, state):
				super (Blocks, self).__init__(state, "blocks", gdb.COMMAND_FILES)
			
			def invoke (self, arg, from_tty):
				print("blocks!")
			
		self.cmds.append(Blocks(self))
		
		class Cmds(PycCmd):
			"""list pyc related gdb commands"""
	
			def __init__ (self, state):
				super (Cmds, self).__init__(state, "cmds", gdb.COMMAND_SUPPORT)
			
			def invoke (self, arg, from_tty):
				for cmd in self.state.cmds:
					print("%s %s" % (cmd.name.ljust(15), cmd.__doc__ ) )
				
		self.cmds.append(Cmds(self))

def init(opts):
	print repr(opts.__dict__)
	
	state = State(**(opts.__dict__))

	