import logging

log_obj = logging.getLogger()
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log_obj.addHandler(ch)

def isverbose():
	global ch
	return (ch.level == logging.DEBUG)

def log_set_verbose():
	global ch
	ch.setLevel(logging.DEBUG)
	
def log_set_quiet():
	global ch
	ch.setLevel(logging.ERROR)

def log(str):
	global ch
	if ch.level == logging.DEBUG:
		print str

