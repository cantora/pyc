
import compiler

def to_str_fmt_func(node, user, depth):
	val = node.__class__.__name__
	if len(node.getChildNodes()) == 0:
		val = repr(node)

	user.append( "%s%s" % (' '*depth, val) )


def to_str(as_tree):
	lines = []

	traverse(as_tree, to_str_fmt_func, lines)
	return "\n".join(lines)

def traverse(node, func, user):
	_traverse(node, func, user)

def _traverse(node, func, user, depth=0):
	func(node, user, depth)
	for n in node.getChildNodes():
		_traverse(n, func, user, depth+1)

#convert an abstract syntax tree into a list of
#simple expressions
#a simple expression: an expression which has only
#one operation on at most two things
def to_se_list(as_tree):
	dummy, se_list = _to_se_list(as_tree)
	return se_list


gen_count = 0
def gen_name():
	global gen_count
	gen_count += 1
	n = "gen_%d" % gen_count
	
	return n

def assert_simple_node(node):
	if( isinstance(node, compiler.ast.Name) != True \
			and isinstance(node, compiler.ast.Const) != True):
		raise TypeError("expected simple node type, got %s" % node.__class__.__name__) 

	
def _to_se_list(node, depth=0):
	val = node.__class__.__name__
	if len(node.getChildNodes()) < 1:
		val = repr(node)

	print "_to_se_list:%s %s" % (' '*depth, val)
	result = None

	if( isinstance(node, compiler.ast.Module) ):
		result = _to_se_list(node.node, depth+1)

	elif( isinstance(node, compiler.ast.Stmt) ):
		l = []
		for n in node.nodes:
			(name, se_list) = _to_se_list(n, depth+1)
			print repr(se_list)
			l += se_list

		result = (compiler.ast.Name("dummy"), l)
	
	elif( isinstance(node, compiler.ast.Assign) ):
		(name, se_list) = _to_se_list(node.expr, depth + 1)

		new_ass = compiler.ast.Assign(node.nodes, node.expr)
		se_list.append(new_ass)
		result = (name, se_list)

	elif( isinstance(node, compiler.ast.Add) ):
		(l_name, l_se_list) = _to_se_list(node.left, depth + 1)
		(r_name, r_se_list) = _to_se_list(node.right, depth + 1)
		
		result_name = gen_name()
		l_se_list += r_se_list
		l_se_list.append( compiler.ast.Assign( \
							[compiler.ast.AssName(result_name, 0)], \
							compiler.ast.Add( (l_name, r_name) ) \
						) )
		result = (compiler.ast.Name(result_name), l_se_list)

	elif( isinstance(node, compiler.ast.CallFunc) ):
		#print repr(node.args) #result = (node		
		args = []
		l = []

		for n in node.args:
			(name, se_list) = _to_se_list(n, depth+1)
			args.append( name )
			l += se_list
		
		result_name = gen_name()
		new_ass = compiler.ast.Assign( \
			[compiler.ast.AssName(result_name, 0)], \
			compiler.ast.CallFunc(node.node, args) \
			)

		l.append( new_ass )
		result = (compiler.ast.Name(result_name), l)

	elif( isinstance(node, compiler.ast.Name) ):
		result = (compiler.ast.Name("user_%s" % node.name), [])

	elif( isinstance(node, compiler.ast.Const) ):
		result = (node, [])
	else:
		raise Exception("unexpected node: %s" % (node.__class__.__name__) )

	print '_to_se_list:%s %s => %s' % (' '*depth, val, repr(result) )
	assert_simple_node(result[0])

	return result





