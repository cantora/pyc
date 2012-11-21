#-------------------------------------------------------------------------------
# elftools example: elf_low_high_api.py
#
# A simple example that shows some usage of the low-level API pyelftools
# provides versus the high-level API while inspecting an ELF file's symbol
# table.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If elftools is not installed, maybe we're running from the root or examples
# dir of the source distribution
try:
	import elftools
except ImportError:
	sys.path.extend(['.', '..'])

from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits

def process_file(filename):
	print('Processing file:', filename)
	with open(filename, 'rb') as f:
		section_info_highlevel(f)


def section_info_highlevel(stream):
	print('High level API...')
	elffile = ELFFile(stream)
	
	# Just use the public methods of ELFFile to get what we need
	# Note that section names, like everything read from the file, are bytes
	# objects.
	print('  %s sections' % elffile.num_sections())
	section = elffile.get_section_by_name(b'.symtab')
	
	if not section:
		print('  No symbol table found. Perhaps this ELF has been stripped?')
		return

	# A section type is in its header, but the name was decoded and placed in
	# a public attribute.
	# bytes2str is used to print the name of the section for consistency of
	# output between Python 2 and 3. The section name is a bytes object.
	print('  Section name: %s, type: %s' %(
		bytes2str(section.name), section['sh_type']))

	# But there's more... If this section is a symbol table section (which is
	# the case in the sample ELF file that comes with the examples), we can
	# get some more information about it.
	if isinstance(section, SymbolTableSection):
		num_symbols = section.num_symbols()
		print("  It's a symbol section with %s symbols" % num_symbols)
		print("  The name of the last symbol in the section is: %s" % (bytes2str(section.get_symbol(num_symbols - 1).name)))
		
		bloc1 = None
		for x in section.iter_symbols():
			#print("    %r:%r" % (x.name, x.entry.__class__))
			if x.name == 'bloc1':
				bloc1 = x
			cont_pp(x, 4)

		if bloc1 is not None:
			print("  found symbol 'bloc1':")
			cont_pp(bloc1, 4)
			print("  disassembly:")
			stream.seek(0)
			stream.seek(bloc1.entry.st_value - 0x08048000)
			l = Decode(bloc1.entry.st_value, stream.read(100), Decode32Bits)
			for i in l:
				print("0x%08x (%02x) %-20s %s" % (i[0],  i[1],  i[3],  i[2]) )
		else:
			print("  could not find 'bloc1'")

		#print("elf header: %s" % (repr(elffile.header)) )
		cont_pp(elffile.header)

		for seg in elffile.iter_segments():
			print("segment header:")
			cont_pp(seg.header)
			print("")

		print('iter sections:')
		for sec in elffile.iter_sections():
			print("name: %s" % (sec.name))
			cont_pp(sec.header)
			print("")



import sys

def cont_pp(cont, depth=0):
	for (k,v) in cont.__dict__.items():
		if isinstance(v, elftools.construct.lib.container.Container):
			print("%s%s:" % (" "*depth, k))
			cont_pp(v, depth+1)
		else:
			sys.stdout.write("%s%s: " % (" "*depth, k) )
			if isinstance(v, int):
				print("%s" % hex(v))
			else:
				print(repr(v))

if __name__ == '__main__':
	for filename in sys.argv[1:]:
		process_file(filename)


