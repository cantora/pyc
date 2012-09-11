tokens = (
	'PRINT', 
	'INT', 
	'PLUS', 
	'MINUS',
	'SEMI'
)

t_PRINT = r'print'
t_PLUS = r'\+'
t_MINUS = r'-'

def t_INT(t):
	r'\d+'
	try:
		t.value = int(t.value)
	except ValueError:
		print 'integer value invalid: %s' % t.value
		t.value = 0

	return t

t_ignore = ' \t'

def t_newline(t):
	r'\n+'
	t.lexer.lineno += t.value.count("\n")

def t_SEMI(t):
	r';+'

def t_error(t):
	print "illegal character '%s'" % t.value[0]


import pyc_util
pyc_util.add_relative_dir_to_syspath("ply")
import ply.lex

ply.lex.lex()

import compiler
precedence = (
	('nonassoc', 'PRINT'),
	('left', 'PLUS', 'MINUS'),
	('right', 'UMINUS')
)

def p_module(m):
	'''module : module statement
			  | statement'''

	mlen = len(m)
	print "p_module: %s" % repr([x for x in m])
	
	if mlen == 2:
		m[0] = compiler.ast.Module(None, compiler.ast.Stmt([]))
		m[0].node.nodes.append(m[1])
	elif mlen == 3:
		m[0] = m[1]
		m[0].node.nodes.append(m[2])
	else:
		raise Exception("unexpected length for mlen: %d" % mlen)


def p_statement(t):
	'''statement : stmt SEMI
				 | stmt \n'''

	t[0] = t[1]

def p_print_statement(t):
	'stmt : PRINT expression'
	t[0] = compiler.ast.Printnl([t[2]], None)

def p_plus_expression(t):
	'expression : expression PLUS expression'
	t[0] = compiler.ast.Add( (t[1], t[3]) )

def p_neg_expression(t):
	'expression : MINUS expression %prec UMINUS'
	t[0] = compiler.ast.UnarySub(t[2])

def p_int_expression(t):
	'expression : INT'
	t[0] = compiler.ast.Const(t[1])

def p_error(t):
	raise Exception("syntax error at line %d near: '%s'" % (t.lineno, t.value) )

import ply.yacc

ply.yacc.yacc()

def parse(src):
	return ply.yacc.parse(src)