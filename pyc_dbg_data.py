import pyc_lineage
import pyc_asm_nodes

import pickle
import struct

def bloc_table(blocs):
	d = {}
	
	for bloc in blocs:
		real_insns = []
		for ins in bloc.insns:
			if isinstance(ins, pyc_asm_nodes.PseudoInst):
				continue
 
			real_insns.append({
				'sir_lineno':		ins.origin.lineno,
				'src_lineno':		pyc_lineage.src_lineno(ins.origin)
			})
		
		bloc_src_lineno = pyc_lineage.src_lineno(bloc.origin)
		
		dummy_insns = [{
			'src_lineno': bloc_src_lineno, 
			'sir_lineno': bloc.origin.lineno
		}]*bloc.preamble_size()

		d[bloc.name] = {
			'insns': dummy_insns + real_insns
		}

	return d
	
def encode_as_byte_list(str):
	return ", ".join([
		hex(ord(x)) for x in str
	])

def headers(src, sir_src, blocs):
	data = dump(src, sir_src, blocs)
		
	headers = [
		".section .pyc_dbg",
		".byte %s" % encode_as_byte_list(data)
	]

	return headers

def dump(src, sir_src, blocs):
	b_table = bloc_table(blocs)

	dbg_table = {
		'src': 		src,
		'sir_src':	sir_src,
		'blocs':	b_table
	}
		
	return pickle.dumps(dbg_table)
	