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
import pyc_lineage
import pyc_asm_nodes

import pickle
import struct

def get_vars(live_set):
	result = set([])

	for n in live_set:
		if isinstance(n, pyc_asm_nodes.Register): continue
		result.add(n.name)

	return result

def bloc_table(blocs):
	d = {}
	
	for bloc in blocs:
		real_insns = []

		for ins in bloc.insns:
			if isinstance(ins, pyc_asm_nodes.PseudoInst):
				continue
 
			real_insns.append({
				'sir_lineno':		ins.origin.lineno,
				'src_lineno':		pyc_lineage.src_lineno(ins.origin),
				'live':				get_vars(ins.live),
				'dummy':			False
			})
		
		bloc_src_lineno = pyc_lineage.src_lineno(bloc.origin)
		
		dummy_prefix_insns = [{
			'src_lineno': bloc_src_lineno, 
			'sir_lineno': bloc.origin.lineno,
			'live':	set([]),
			'dummy': True
		}]*bloc.preamble_size()

		dummy_suffix_insns = [{
			'src_lineno': bloc_src_lineno, 
			'sir_lineno': bloc.origin.lineno,
			'live':	set([]),
			'dummy': True
		}]*bloc.postamble_size()

		d[bloc.name] = {
			'insns':		dummy_prefix_insns + real_insns + dummy_suffix_insns,
			'src_lineno':	bloc_src_lineno,
			'sir_lineno':	bloc.origin.lineno,
			'mem_map':		bloc.symtbl.mem_map
		}

	return d
	
def encode_as_byte_list(str):
	return ", ".join([
		hex(ord(x)) for x in str
	])

def headers(src, sir_src, blocs, name_map):
	data = dump(src, sir_src, blocs, name_map)
		
	headers = [
		".section .pyc_dbg",
		".byte %s" % encode_as_byte_list(data)
	]

	return headers

def dump(src, sir_src, blocs, name_map):
	b_table = bloc_table(blocs)

	dbg_table = {
		'src': 		src,
		'sir_src':	sir_src,
		'blocs':	b_table,
		'name_map': name_map
	}
		
	return pickle.dumps(dbg_table)
	