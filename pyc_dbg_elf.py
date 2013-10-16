# Copyright 2013 anthony cantor
# This file is part of pyc.
# 
# pyc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#  
# pyc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#  
# You should have received a copy of the GNU General Public License
# along with pyc.  If not, see <http://www.gnu.org/licenses/>.
import pickle
from StringIO import StringIO

import elftools
from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from pyc_log import log

class ElfError(Exception):
	pass

def cont_pp(f, cont, depth=0):
	for (k,v) in cont.__dict__.items():
		if isinstance(v, elftools.construct.lib.container.Container):
			print >>f, "%s%s:" % (" "*depth, k)
			cont_pp(f, v, depth+1)
		else:
			f.write("%s%s: " % (" "*depth, k) )
			if isinstance(v, int):
				print >>f, "%s" % hex(v)
			else:
				print >>f, repr(v)

	return f
		
def extract_dbg_map(elf):
	dbg_sec = elf.get_section_by_name(b'.pyc_dbg')
	if not dbg_sec:
		raise ElfError("pyc debug symbol section not found")

	if dbg_sec.is_null():
		raise ElfError("pyc debug symbol section is null")

	log("pyc_dbg sec header: %s" % repr(dbg_sec.header) )
	return pickle.loads(dbg_sec.data())	

def map_blocs(elf, dbg_map):
	bmap = {}

	if len(dbg_map['blocs']) < 1:
		raise ArgumentError("no blocs defined in dbg_map")

	sec = elf.get_section_by_name(b'.symtab')
	if not sec or not isinstance(sec, SymbolTableSection):
		raise ElfError("invalid symbol table")

	for sym in sec.iter_symbols():
		if sym.name in dbg_map['blocs'].keys():
			log("map bloc %s" % sym.name)
			#log(cont_pp(StringIO(), sym).getvalue())

			bmap[sym.name] = {
				'addr':		sym.entry.st_value,
				'size':		sym.entry.st_size
			}

	if len(bmap) != len(dbg_map['blocs']):
		raise ElfError("could not map blocs: %r" % (set(dbg_map['blocs'].keys()) - set(bmap.keys()) ) )

	return bmap
		
def extract_from_bin(f):
	elf = ELFFile(f)
	if not elf:
		raise ElfError("invalid ELF file")

	dbg_map = extract_dbg_map(elf)
	#log("dbg_map: %r" % dbg_map)
	bloc_map = map_blocs(elf, dbg_map)
	for (name, info) in bloc_map.items():
		for (k,v) in info.items():
			dbg_map['blocs'][name][k] = v

	return dbg_map
