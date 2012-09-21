import pyc_var_analyzer
from pyc_asm_nodes import *

asm_list = [
	Mov(Immed(Int(4)), Var("z")),
	Mov(Immed(Int(0)), Var("w")),
	Mov(Immed(Int(1)), Var("z")),
	Mov(Var("w"), Var("x")),
	Add(Var("z"), Var("x")),
	Mov(Var("w"), Var("y")),
	Add(Var("x"), Var("y")),
	Mov(Var("y"), Var("w")),
	Add(Var("x"), Var("w"))
]

live_list = pyc_var_analyzer.to_live_list(asm_list)

print ""
print "live_list:\n\t%s" % "\n\t".join([repr(x) for x in reversed(live_list)])

graph = pyc_var_analyzer.to_intf_graph(live_list)

print "graph:\n\t%s" % "\n\t".join(["%s: %s" % (repr(k), repr(v)) for (k,v) in graph.items()]) 