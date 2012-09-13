import pyc_log

'''
identifier ::=  (letter|"_") (letter | digit | "_")*
letter     ::=  lowercase | uppercase
lowercase  ::=  "a"..."z"
uppercase  ::=  "A"..."Z"
digit      ::=  "0"..."9"
'''

reserved = {
	'print'  : 'PRINT',
	'and'    : 'AND',
	'del'    : 'DEL',
	'from'   : 'FROM',
	'not'    : 'NOT',
	'while'  : 'WHILE',
	'as'     : 'AS',
	'elif'   : 'ELIF',
	'global' : 'GLOBAL',
	'or'     : 'OR',
	'with'   : 'WITH',
	'assert' : 'ASSERT',
	'else'   : 'ELSE',
	'if'     : 'IF',
	'pass'   : 'PASS',
	'yield'  : 'YIELD',
    'break'  : 'BREAK',
	'except' : 'EXCEPT',
	'import' : 'IMPORT',
	'class'  : 'CLASS',
	'exec'   : 'EXEC',
	'in'     : 'IN',
	'raise'  : 'RAISE',
	'continue': 'CONTINUE',
	'finally': 'FINALLY',
	'is'     : 'IS',
	'return' : 'RETURN',
	'def'    : 'DEF',
	'for'    : 'FOR',
    'lambda' : 'LAMBDA',
	'try'    : 'TRY'
}

literals = ['=', '(', ')']

tokens = (
	'INT', 
	'PLUS', 
	'MINUS',
	'SEMI',
	'IDENT'
) + tuple(reserved.values())

t_PLUS = r'\+'
t_MINUS = r'-'
t_SEMI = r';'

def t_IDENT(t):
	r'[a-zA-Z_][a-zA-Z0-9_]*'
	t.type = reserved.get(t.value, 'IDENT')
	return t

def t_INT(t):
	r'\d+'
	try:
		t.value = int(t.value)
	except ValueError:
		pyc_log.log('integer value invalid: %s' % t.value)
		t.value = 0

	return t

t_ignore = ' \t'

def t_newline(t):
	r'\n+'
	t.lexer.lineno += t.value.count("\n")

def t_error(t):
	pyc_log.log("illegal character '%s'" % t.value[0])


import pyc_util
pyc_util.add_relative_dir_to_syspath("ply")
import ply.lex

ply.lex.lex(debug = pyc_log.isverbose())

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
	pyc_log.log("p_module: %s" % repr([x for x in m]))
	
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

def p_print_stmt(t):
	'stmt : PRINT expr'
	t[0] = compiler.ast.Printnl([t[2]], None)


def p_assign_stmt(t):
	'stmt : IDENT "=" expr'

	t[0] = compiler.ast.Assign(
		[compiler.ast.AssName(t[1], 'OP_ASSIGN')],
		t[3]
		)

def p_call_expr(t):
	'expr : IDENT "(" ")"'
	
	t[0] = compiler.ast.CallFunc(compiler.ast.Name(t[1]), [])
		

def p_ident_expr(t):
	'expr : IDENT'
	
	t[0] = compiler.ast.Name(t[1])

def p_plus_expr(t):
	'expr : expr PLUS expr'
	t[0] = compiler.ast.Add( (t[1], t[3]) )

def p_neg_expr(t):
	'expr : MINUS expr %prec UMINUS'
	t[0] = compiler.ast.UnarySub(t[2])

def p_int_expr(t):
	'expr : INT'
	t[0] = compiler.ast.Const(t[1])

def p_error(t):
	raise Exception("syntax error at line %d near: '%s'" % (t.lineno, t.value) )

import ply.yacc

ply.yacc.yacc()


def parse(src):
	# create console handler and set level to debug
	
	return ply.yacc.parse(src, debug=pyc_log.log_obj)