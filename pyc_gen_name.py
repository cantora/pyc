
gen_count = 0
def new():
	global gen_count
	gen_count += 1
	n = "gen_%d" % gen_count
	
	return n
