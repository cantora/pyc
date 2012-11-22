import gdb
from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits
import distorm3
import pyc_dbg_elf
from pyc_log import *

class PycCmd(gdb.Command):
	
	def __init__ (self, state, name, type):
		self.state = state
		self.name = self.state.cmd_name(name)
		super (PycCmd, self).__init__(self.name, type)

class NoFrame(Exception):
	"""there is no frame context"""
	pass
	
class CodeOutsideScope(Exception):
	"""
	we tried to determine pyc context outside of a
	pyc defined x86 instruction
	"""
	pass

def list_with_linenos(str):
	lines = str.split("\n")
	for i in range(0, len(lines)):
		print "%d\t%s" % (i+1, lines[i])
	
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
		amt = frame.pc() - bloc['addr']
		log("read memory from inferior %d@%s:" % (amt, hex(bloc['addr'])) )
		buf = inf.read_memory(bloc['addr'], amt)
		buf = str(buf)
		log("buf: %s" % ([hex(ord(x)) for x in buf]) )
		il = Decode(bloc['addr'], buf, Decode32Bits)
		l = len(il)
		log("decoded %d instructions" % (l))

		return (bloc['insns'][l]['src_lineno'], bloc['insns'][l]['sir_lineno'])

	def blocs(self):
		return self.dbg_map['blocs'].keys()

	def src(self):
		return self.dbg_map['src']

	def sir_src(self):
		return self.dbg_map['sir_src']

	def cmd_name(self, cmd):
		return "%s%s" % (self.cmd_prefix, cmd)

	def on_stop(self, event):
		log("stopped: %r" % (event))

	def on_cont(self, event):
		log("cont: %r" % (event))
	
	def linenos(self):
		"""raises: NoFrame, CodeOutsideScope"""

		try:
			frame = gdb.selected_frame()
		except gdb.error:
			raise NoFrame("no frame is selected")

		return self.frame_to_linenos(frame)

	def adjusted_linenos(self):
		"""
		get line numbers with adjustment to avoid 'line 0'
		and also adjust to map line 1 to index 0 in the 
		source line arrays.

		raises: NoFrame, CodeOutsideScope
		"""

		(src_lineno, sir_lineno) = self.linenos()

		src_lines = self.src().split('\n')
		sir_lines = self.sir_src().split('\n')

		if src_lineno < 1:
			src_lineno = 1
			while src_lines[src_lineno-1].strip() == '':
				src_lineno += 1

		if sir_lineno < 1:
			sir_lineno = 1
		
		return (
			src_lines, 
			src_lineno-1,
			sir_lines,
			sir_lineno-1
		)

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
				list_with_linenos(self.state.src())
			
		self.cmds.append(List(self))
		
		class SIRList(PycCmd):
			"""list the sir source code."""
			
			def __init__ (self, state):
				super (SIRList, self).__init__(state, "sir-list", gdb.COMMAND_FILES)
			
			def invoke (self, arg, from_tty):
				list_with_linenos(self.state.sir_src())
			
		self.cmds.append(SIRList(self))

		class Context(PycCmd):
			"""list the user and sir source context"""

			def __init__ (self, state):
				super (Context, self).__init__(state, "context", gdb.COMMAND_RUNNING)

			def print_context(self, lines, lineno):
				output_size = 15
				prev_lines = 10

				start = lineno-prev_lines
				if start < 0:
					start = 0 
				
				fin = start + output_size
				if fin > (len(lines) - 1):
					fin = (len(lines) - 1)

				for i in range(start, fin):
					if i == (lineno):
						print "%d\t%s <<%s" % (i+1, lines[i], "-"*40)
					else:
						print "%d\t%s" % (i+1, lines[i])
			
			def invoke (self, arg, from_tty):
				try:
					(src_lines, src_lineno, sir_lines, sir_lineno) = self.state.adjusted_linenos()
				except NoFrame:
					print "no selected frame"
					return
				except CodeOutsideScope:
					print "current frame is not pyc generated code"
					return
					
				self.print_context(src_lines, src_lineno)
				print "#"*60
				self.print_context(sir_lines, sir_lineno)

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
		gdb.execute("set python print-stack full")
	else:
		log_set_quiet()

	log("opts: %r" % (opts.__dict__))
	
	state = State(**(opts.__dict__))

	def on_stop(event):
		state.on_stop(event)

	def on_cont(event):
		state.on_cont(event)
	
	gdb.events.stop.connect(on_stop)
	gdb.events.cont.connect(on_cont)

	
