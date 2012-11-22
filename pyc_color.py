
def ansi_escape(s, code_arr):
	return "\x1b[%sm%s\x1b[0m" % (
		";".join(code_arr),
		s
	)

def yellow(s):
	return ansi_escape(s, ['33'])

