import os, sys, inspect

def add_relative_dir_to_syspath(dir):
	path = os.path.realpath(os.path.abspath(os.path.join( \
		os.path.split(inspect.getfile( inspect.currentframe() ))[0], dir) \
	))
	if path not in sys.path:
		sys.path.insert(0, path)
		return 0

	return 1



