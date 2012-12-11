
def ansi_escape(s, code_arr):
	return "\x1b[%sm%s\x1b[0m" % (
		";".join(code_arr),
		s
	)

def ansi_color(s, num):
	return ansi_escape(s, [str(num)])

def yellow(s):
	return ansi_color(s, 33)

def red(s):
	return ansi_color(s, 31)

