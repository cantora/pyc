from pyc_log import *
from pyc_asm_nodes import *
import time

def live_list_to_str_lines(live_list):
	lines = []
	for x in reversed(live_list):
		if isinstance(x[0], AsmFlow):
			lines.append("(%s(%s), %s)" % (x[0].__class__.__name__, x[0].test, repr(x[1]) ) )
		else:
			lines.append(repr(x))

	return lines

def interference_graph(asm_list):
	t0 = time.time()
	live_list = to_live_list(asm_list)
	#print "    live list time %d" % (time.time() - t0)
	log(lambda: "live_list:\n\t%s" % ("\n\t".join(live_list_to_str_lines(live_list) ) ) )

	t0 = time.time()
	graph = to_intf_graph(live_list)
	#print "    interference time: %d" % (time.time() - t0)

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

	def _to_intf_graph(live_list, graph, depth):
		log("%screate interference graph from live_list" % (" "*depth))	
		for (ins, live) in live_list:
			#print "live=%d, depth=%d" % (len(live), depth)
			if isinstance(ins, AsmIf):
				log("%sAsmIf.orelse" % (" "*depth))
				graph = _to_intf_graph(ins.orelse, graph, depth+1)
				log("%sAsmIf.body" % (" "*depth) )
				graph = _to_intf_graph(ins.body, graph, depth+1)
				log("%sAsmIf(%s)" % (" "*depth, repr(ins.test) ) )
				#dont care about test b.c. its just a read
			elif isinstance(ins, AsmDoWhile):
				log("%sins: AsmDoWhile-tbody" % (" "*depth))
				graph = _to_intf_graph(ins.tbody, graph, depth+1)
				log("%sins: AsmDoWhile-wbody" % (" "*depth))
				graph = _to_intf_graph(ins.wbody, graph, depth+1)
				log("%sins: AsmDoWhile(%s)" % (" "*depth, repr(ins.test)))
				#dont care about test b.c. its just a read
			else:
				writes = get_vars(ins.writes())
				if len(writes) < 1:
					continue
		
				log("%s(%s) => %s \n\t%s" % (" "*depth, ins.__class__.__name__, repr(writes), repr(live) ) )
						
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
				#for var in live
			#else (not AsmIf)
		return graph
	#def _to_intf_graph

	return _to_intf_graph(live_list, graph, 0)

def to_live_list(asm_list, live = set([]), depth=0):
	result = []

	log("%sprocess asm_list into live_list: %s" % (" "*depth, repr(live)) )
	for ins in reversed(asm_list):
		reads = set([])
		writes = set([])

		if isinstance(ins, AsmIf):
			log("%sins: AsmIf-end" % (" "*depth) )
			els_live_list = to_live_list(ins.orelse, live, depth+1)

			log("%sins: AsmIf-else" % (" "*depth) )
			body_live_list = to_live_list(ins.body, live, depth+1)
			ins = ins.shallow_beget(ins.__class__, ins.test, body_live_list, els_live_list)

			live = body_live_list[-1][1] | els_live_list[-1][1]
			log("%sins: AsmIf" % (" "*depth) )
			reads = set( get_vars(ins.reads()) )
		elif isinstance(ins, AsmDoWhile):
			i = 0
			prev_live = set([])

			while True:
				log("%sins: AsmDoWhile(%d)-test" % (" "*depth, i))
				live = live | prev_live #union back in the condition live set
				live = live | set( get_vars(ins.reads()) )
				log("%slive(%d): %s" % (" "*depth, len(live), repr(live) ) )
				if live == prev_live && i > 0:
					break
				prev_live = set([]) | live

				log("%sins: AsmDoWhile(%d)-tbody" % (" "*depth, i))
				tbody_live_list = to_live_list(ins.tbody, live, depth+1)
				live = tbody_live_list[-1][1]
				
				log("%sins: AsmDoWhile(%d)-wbody" % (" "*depth, i))
				wbody_live_list = to_live_list(ins.wbody, live, depth+1)
				live = wbody_live_list[-1][1] 
				i += 1
			
			ins = ins.shallow_beget(ins.__class__, ins.test, tbody_live_list, wbody_live_list)
		else:
			log("%sins: %s" % (" "*depth, ins) )
			reads = set( get_vars(ins.reads()) )
			writes = set( get_vars(ins.writes()) )

		live = (live - writes) | reads
		result.append((ins, set(live)) )
		log("%slive(%d): %s" % (" "*depth, len(live), repr(live) ) )


	return result

