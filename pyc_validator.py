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
from pyc_vis import Visitor
import pyc_vis
import ast

class AssumptionChecker(Visitor):
	def visit_FunctionDef(self, node):
		return (
			node.args.vararg is None and \
			node.args.kwarg is None and \
			len(node.args.defaults) == 0
		)

	def visit_Lambda(self, node):
		return self.visit_FunctionDef(node)
	
#check whether an ast node is constrained as expected
#for the particular level of python we are implementing
def isvalid(node):
	ac = AssumptionChecker()
	return pyc_vis.visit(ac, node)

def assert_valid(node):
	if not isvalid(node):
		raise Exception("node failed assumption: %s" % ast.dump(node))

