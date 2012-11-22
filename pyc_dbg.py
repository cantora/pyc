import gdb
from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits
import distorm3
import pyc_dbg_elf
from pyc_log import *
import pyc_color

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

	def assert_frame(self, frame):
		if not frame.is_valid():
			raise Exception("expected valid frame")
		if frame.type() != gdb.NORMAL_FRAME:
			raise Exception("expected frame.type == NORMAL_FRAME. got: %s" % frame.type())
		if frame.name() is None:
			raise Exception("frame has no name!")
		if frame.name() not in self.dbg_map['blocs']:
			raise CodeOutsideScope("this is not a pyc frame")

	def frame_to_linenos(self, frame):
		bloc = self.frame_to_bloc(frame)
		if frame.pc() == bloc['addr']:
			return (bloc['insns'][0]['src_lineno'], bloc['insns'][0]['sir_lineno'])

		l = self.frame_to_asm_lineno(frame, bloc)		
		if l >= len(bloc['insns']):
			raise CodeOutsideScope("exceeded edge of pyc code block")

		return (bloc['insns'][l]['src_lineno'], bloc['insns'][l]['sir_lineno'])

	def frame_to_bloc(self, frame):
		bloc = self.dbg_map['blocs'][frame.name()]
		if frame.pc() < bloc['addr']:
			raise Exception("frame.pc < bloc['addr']")
		
		return bloc

	def frame_to_asm_lineno(self, frame, bloc):
		self.assert_frame(frame)

		inf = gdb.selected_inferior()
		amt = frame.pc() - bloc['addr']
		log("read memory from inferior %d@%s:" % (amt, hex(bloc['addr'])) )
		buf = inf.read_memory(bloc['addr'], amt)
		buf = str(buf)
		log("buf: %s" % ([hex(ord(x)) for x in buf]) )
		il = Decode(bloc['addr'], buf, Decode32Bits)
		l = len(il)
		log("decoded %d instructions" % (l))

		return l
		
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
		try:
			(src_lines, src_lineno, sir_lines, sir_lineno) = self.adjusted_linenos()
		except NoFrame:
			return
		except CodeOutsideScope:
			return
			
		src_ctx = self.context_lines(src_lines, src_lineno)
		sir_ctx = self.context_lines(sir_lines, sir_lineno)
		asm_ctx = gdb.execute("x/1i $pc", False, True)

		print "src:%s" % (src_ctx[0])
		print "sir:%s" % (sir_ctx[0])
		print "asm:\t%s" % (asm_ctx)

	def on_cont(self, event):
		log("cont: %r" % (event))
	
	def get_frame(self):
		try:
			frame = gdb.selected_frame()
		except gdb.error:
			raise NoFrame("no frame is selected")

		return frame

	def linenos(self):
		"""raises: NoFrame, CodeOutsideScope"""

		return self.frame_to_linenos(self.get_frame())

	def adjusted_asm_linenos(self):
		"""raises: NoFrame, CodeOutsideScope"""

		frame = self.get_frame()
		bloc = self.frame_to_bloc(frame)

		frame_lines = gdb.execute(
			"x/%di %s" % (len(bloc['insns']), hex(bloc['addr']) ),
			False,
			True
		).split("\n")

		frame_lines.insert(0, "")
		if frame.pc() == bloc['addr']:
			asm_lineno = 0
		else:
			asm_lineno = self.frame_to_asm_lineno(frame, bloc)
		
		return (frame_lines, asm_lineno+1)

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

		#insert a blank line at start b.c. line numbers start at 1 not 0
		src_lines.insert(0, "")
		sir_lines.insert(0, "")

		#bump up any lines to first valid line 
		#(this may happen from preamble instructions that arent generated
		#by an actual statement, i.e. push %ebp)
		if src_lineno < 1:
			src_lineno = 1
			while src_lines[src_lineno].strip() == '':
				src_lineno += 1

		if sir_lineno < 1:
			sir_lineno = 1 #line 1 should never be blank in SIR source
		
		return (
			src_lines, 
			src_lineno,
			sir_lines,
			sir_lineno
		)

	def sir_linenos(self, src_lineno):
		lns = set([])
		for (name, bloc) in self.dbg_map['blocs'].items():
			for i in bloc['insns']:
				if i['src_lineno'] == src_lineno:
					lns.add(i['sir_lineno'])
		
		return lns

	def asm_linenos(self, sir_lineno):
		indices = set([])
		for (name, bloc) in self.dbg_map['blocs'].items():
			for i in range(0, len(bloc['insns'])):
				if bloc['insns'][i]['sir_lineno'] == sir_lineno:
					indices.add(i+1)

		log("asm_linenos for %d: %r" % (sir_lineno, indices) )
		return indices

	def context_lines(self, lines, lineno, **kwargs):
		opts = {
			'highlight':			set([]),  			#highlight any line within this set
			'highlight_color':		33,
			'output_size':			1,					#total number of context lines
			'prev_lines':			0,					#amt of preceding lines of context
			'arrow':				False,
			'arrow_color':			None
		}

		for k in opts.keys():
			if k in kwargs:
				opts[k] = kwargs[k]

		start = lineno - opts['prev_lines']
		if start < 1:
			start = 1 
		
		fin = start + opts['output_size']
		if fin > (len(lines) - 1):
			fin = (len(lines) - 1)

		output = []
		for i in range(start, fin):
			if opts['arrow'] and i == (lineno):
				arr_s = "<<"+"-"*40
				if opts['arrow_color']:
					arr_s = pyc_color.ansi_color(arr_s, opts['arrow_color'])
				out = "%d\t%s %s" % (i, lines[i], arr_s)
			else:
				out = "%d\t%s" % (i, lines[i])

			if i in opts['highlight']:
				out = pyc_color.ansi_color(out, opts['highlight_color'])

			output.append(out)
		
		return output

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

			
			def invoke (self, arg, from_tty):
				try:
					(src_lines, src_lineno, sir_lines, sir_lineno) = self.state.adjusted_linenos()
				except NoFrame:
					print "no selected frame"
					return
				except CodeOutsideScope as e:
					log("e: %s" % e)
					print "not currently executing pyc generated code"
					return
					
				print "\n".join(self.state.context_lines(
					src_lines, 
					src_lineno,
					output_size = 8,
					prev_lines = 4,
					arrow = True,
					arrow_color = 33
				))

				print "#"*60
				print "\n".join(self.state.context_lines(
					sir_lines, 
					sir_lineno,
					output_size = 15,
					prev_lines = 10,
					arrow = True,
					arrow_color = 36,
					highlight = self.state.sir_linenos(src_lineno),
					highlight_color = 33
				))
	
				(asm_lines, asm_lineno) = self.state.adjusted_asm_linenos()
				print "#"*60
				print "\n".join(self.state.context_lines(
					asm_lines, 
					asm_lineno,
					output_size = 8,
					prev_lines = 3,
					highlight = self.state.asm_linenos(sir_lineno),
					highlight_color = 36
				))
				

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

	
