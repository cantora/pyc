
verbose = False

def log_set_verbose():
	global verbose
	verbose = True
	
def log_set_quiet():
	global verbose
	verbose = False

def log(str):
	global verbose
	if verbose:
		print(str)

