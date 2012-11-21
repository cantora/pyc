import pyc_lineage
import pickle
import struct

def bloc_table(blocs):
	d = {}
	
	for bloc in blocs:
		d[bloc.name] = {
			'insns': [{
				'sir_lineno':		i.origin.lineno,
				'src_lineno':		pyc_lineage.sir_src_line(i.origin)
			} for i in bloc.insns]
		}

	return d
						
def headers(src, sir_src, blocs):
	data = dump(src, sir_src, blocs)
	
	headers = [
		".section .pyc_dbg",
		".string %s" % repr(data)
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
	