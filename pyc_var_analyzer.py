from pyc_log import *
from pyc_asm_nodes import *

def live_list_to_str_lines(live_list):
	lines = []
	for x in reversed(live_list):
		if isinstance(x[0], AsmIf):
			lines.append("(AsmIf(%s), %s)" % (x[0].test, repr(x[1]) ) )
		else:
			lines.append(repr(x))

	return lines

def interference_graph(asm_list):
	live_list = to_live_list(asm_list)
	log(lambda: "live_list:\n\t%s" % ("\n\t".join(live_list_to_str_lines(live_list) ) ) )

	graph = to_intf_graph(live_list)

	log(lambda: "graph:\n\t%s" % "\n\t".join(["%s: %s" % (repr(k), repr(v)) for (k,v) in graph.items()]) )
	
	return (live_list, graph)

class IntfGraph(dict):
	def add_edge(self, n1, n2):
		if n1 != n2:
			self[n1] = self.get(n1, set([])) | set([n2])
			self[n2] = self.get(n2, set([])) | set([n1])

	def init_node(self, node):
		self[node] = self.get(node, set([]))

def to_intf_graph(live_list):
	graph = IntfGraph({})
	
	for reg in Register.registers:
		graph.init_node(Register(reg))

	for (ins, live) in live_list:
		writes = get_vars(ins.writes())
		if len(writes) < 1:
			continue

		log("(%s) => %s \n\t%s" % (ins.__class__.__name__, repr(writes), repr(live) ) )

		for write in writes:
			graph.init_node(write)

		for var in live:
			graph.init_node(var)			
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


def to_live_list(asm_list, live = set([]), depth=0):
	result = []

	log("%sprocess asm_list into live_list: %s" % (" "*depth, repr(live)) )
	for ins in reversed(asm_list):
		if isinstance(ins, AsmIf):
			log("%sins: AsmIf-end" % (" "*depth) )
			els_live_list = to_live_list(ins.orelse, live, depth+1)
			log("%sins: AsmIf-else" % (" "*depth) )
			body_live_list = to_live_list(ins.body, live, depth+1)
			ins = ins.shallow_beget(ins.__class__, ins.test, body_live_list, els_live_list)
			live = body_live_list[-1][1] | els_live_list[-1][1]
			log("%sins: AsmIf" % (" "*depth) )
		else:
			log("%sins: %s" % (" "*depth, ins) )

		live = (
			live - set( get_vars(ins.writes()) ) ) \
				| set( get_vars(ins.reads()) 
		)
		result.append((ins, set(live)) )
		log("%slive: %s" % (" "*depth, repr(live) ) )


	return result

