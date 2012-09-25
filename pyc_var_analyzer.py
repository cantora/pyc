from pyc_log import *
from pyc_asm_nodes import *

"""
		if write is None:
			continue
		
		try:
			graph[write]
		except KeyError:
			graph[write] = set([])

		if isinstance(ins, Mov):
			graph[write] 
		else:
"""

def interference_graph(asm_list):
	live_list = to_live_list(asm_list)
	log(lambda: "live_list:\n\t%s" % "\n\t".join([repr(x) for x in reversed(live_list)]))

	graph = to_intf_graph(live_list)

	log(lambda: "graph:\n\t%s" % "\n\t".join(["%s: %s" % (repr(k), repr(v)) for (k,v) in graph.items()]) )
	
	return (live_list, graph)

class IntfGraph(dict):
	def add_edge(self, n1, n2):
		if n1 != n2:
			self[n1] = self.get(n1, set([])) | set([n2])
			self[n2] = self.get(n2, set([])) | set([n1])

def to_intf_graph(live_list):
	graph = IntfGraph({})

	for (ins, live) in live_list:
		writes = get_vars(ins.writes())
		if len(writes) < 1:
			continue

		log("(%s) => %s \n\t%s" % (ins.__class__.__name__, repr(writes), repr(live) ) )

		for var in live:
			if isinstance(ins, Call):
				for write in writes:
					graph.add_edge(write, var)

			elif isinstance(ins, Mov):
				reads = get_vars(ins.reads())
				if len(reads) > 0 and var == reads[0]:
					continue

				graph.add_edge(writes[0], var)

			else:
				if len(writes) != 1:
					raise Exception("expected 1 write from %s" % ins)

				graph.add_edge(writes[0], var)

	return graph


def to_live_list(asm_list):
	result = []
	live = set([])

	log("process asm_list into live_list")
	for ins in reversed(asm_list):
		log("ins: %s" % ins)

		live = (live - set( get_vars(ins.writes()) ) ) \
				| set( get_vars(ins.reads()) )
		
		result.append((ins, set(live)) )
		log("live: %s" % repr(live))


	return result

