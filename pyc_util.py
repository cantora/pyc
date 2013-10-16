# Copyright 2013 anthony cantor
# This file is part of pyc.
# 
# pyc is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#  
# pyc is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#  
# You should have received a copy of the GNU General Public License
# along with pyc.  If not, see <http://www.gnu.org/licenses/>.
import os, sys, inspect

def add_relative_dir_to_syspath(dir):
	path = os.path.realpath(os.path.abspath(os.path.join( \
		os.path.split(inspect.getfile( inspect.currentframe() ))[0], dir) \
	))
	if path not in sys.path:
		sys.path.insert(0, path)
		return 0

	return 1



