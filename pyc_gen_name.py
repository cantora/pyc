
prefix_count = {
	"gen_": 0
}

def new(prefix="gen_"):
	global prefix_count
	if not prefix in prefix_count:
		prefix_count[prefix] = 0

	prefix_count[prefix] += 1
	n = "%s%d" % (prefix, prefix_count[prefix])
	
	return n

def user_name(s):
	return "user_%s" % s

