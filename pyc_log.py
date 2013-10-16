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
		if hasattr(str, '__call__'):
			str = str()

		print str

