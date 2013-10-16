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

