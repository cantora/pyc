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
import pyc_ir_nodes
import pyc_gen_name
import inspect

def assert_klass(klass, *args):
	for obj in args:
		if not isinstance(obj, klass):
			raise Exception("expected %r, got: %r" % (klass, obj))

	return True

def assert_pyobj(*args):
	return assert_klass(PyObj, *args)

def assert_closure(*args):
	return assert_klass(Closure, *args)

def assert_bool(*args):
	for obj in args:
		if (not assert_int(obj)) or obj < 0 or obj > 1:
			raise Exception("invalid range for bool: %r" % obj)

	return True

def assert_int(*args):
	return assert_klass(int, *args)

def assert_big(*args):
	for obj in args:
		if not isinstance(obj, BigObj):
			raise Exception("unexpected big class: %r" % obj)

	return True

class PyObj(object):
	def __init__(self, value, type):
		self.value = value
		self.type = type
		if type not in pyc_ir_nodes.tag_types:
			raise Exception("unexpected type: %r" % type)
	
	def __setitem__(self, key, val):
		assert_pyobj(key)	
		return self.value.value.__setitem__(key.value, val)

	def __getitem__(self, key):
		assert_pyobj(key)	
		return self.value.value.__getitem__(key.value)

	def __getattr__(self, name):
		if name[0:1] == "_":
			assert_big(self.value)
			result = getattr(self.value.value, name)

			if isinstance(result.value, BigObj) and \
						isinstance(result.value.value, Closure):
				if IsClass(self):
					result = UnboundMethod(
						self.value.value,
						result.value.value
					)
				else: #object
					if name in self.value.value.__dict__:
						return result #its an object attr
	
					#else its a class attr
					result = BoundMethod(
						self.value.value,
						result.value.value
					)

				return InjectFromBig(BigObj(result))
			else:
				return result
		else:
			return super(PyObj, self).__getattr__(name)
		
	def __setattr__(self, name, value):
		if name[0:1] == "_":
			return setattr(self.value.value, name, value)
		else:
			return super(PyObj, self).__setattr__(name, value)

	def __repr__(self):
		return "%s%s" % (self.__class__.__name__, repr((self.type, self.value)))

	def tag(self):
		return pyc_ir_nodes.Tag.type_to_tag(self.type)

	def to_str(self):
		if self.type == 'int':
			return str(self.value)
		elif self.type == 'bool':
			return str(self.value == 1)
		else:
			if isinstance(self.value.value, list):
				return "[" + ", ".join([x.to_str() for x in self.value.value]) + "]"
			else:
				return repr(self.value.value)

	def __cmp__(self, other):
		return self.value.__cmp__(other.value)

class BigObj(object):

	def __init__(self, val):
		self.value = val

	def __eq__(self, other):
		return self is other

	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, repr(self.value))

class Closure(BigObj):
	def __init__(self, fn, fvs):
		self.fn = fn
		self.fvs = fvs
		self.value = self #...yeah i know this is weird...probly will change it later

	def __repr__(self):
		return "%s%s" % (self.__class__, repr((self.fn, self.fvs)))

class UnboundMethod:
	def __init__(self, klass, closure):
		self.klass = klass
		self.closure = closure

class BoundMethod:
	def __init__(self, obj, closure):
		self.obj = obj
		self.closure = closure

def ClosureFVS(pobj):
	assert_pyobj(pobj)
	assert_closure(pobj.value)
	
	return pobj.value.fvs
	
def ClosureCall(pobj_clsr, fvs, *args):
	assert_pyobj(pobj_clsr, fvs, *args)
	assert_closure(pobj_clsr.value)
	return pobj_clsr.value.fn(fvs, *args)

class Trap(object):
	def __getattribute__(self, *args):
		raise Exception("this value shouldnt exist")

	def __setattribute__(self, *args):
		raise Exception("this value shouldnt exist")

	def __repr__(self, *args):
		return "(no-init)"

	def __str__(self, *args):
		raise Exception("this value shouldnt exist")

trap_obj = Trap()
def set_trap():
	return trap_obj
		
def InjectFromBool(val):
	assert_bool(val)	
	return PyObj(val, 'bool')

def InjectFromInt(val):
	assert_int(val)
	return PyObj(val, 'int')

def ListRef(pobj_size):
	assert_pyobj(pobj_size)
	return BigObj([set_trap() for i in range(0, pobj_size.value)])
	
def DictRef():
	return BigObj({})

def ClassRef(bases):
	assert_pyobj(bases)
	assert_big(bases.value)

	parents = [x.value.value for x in bases.value.value] + [object]
	name = pyc_gen_name.new("pyrun_class")
	return BigObj(type(
		name,
		tuple(parents),
		{}
	))
	
def InjectFromBig(val):
	assert_big(val)
	return PyObj(val, 'big')

def ProjectToBool(pobj):
	assert_pyobj(pobj)
	assert_bool(pobj.value)
	
	return pobj.value

def ProjectToInt(pobj):
	assert_pyobj(pobj)
	assert_int(pobj.value)

	return pobj.value
	
def ProjectToBig(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	return pobj.value

def CastBoolToInt(val):
	return val

def CastIntToBool(val):
	return val

def IsClass(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	return inspect.isclass(pobj.value.value)

def IsBoundMethod(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	return isinstance(
		pobj.value.value,
		BoundMethod
	)

def IsUnboundMethod(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	return isinstance(
		pobj.value.value,
		UnboundMethod
	)

def GetReceiver(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	if not isinstance(pobj.value.value, BoundMethod):
		raise Exception("expected BoundMethod, got %r" % pobj)	
	
	return BigObj(
		pobj.value.value.obj
	)

def IsTrue(pobj):
	assert_pyobj(pobj)
	if pobj.type == 'big':
		val = pobj.value.value
	else:
		val = pobj.value

	if val:
		return True
	else:
		return False

def Tag(pobj):
	assert_pyobj(pobj)
	return pobj.tag()
	
def CreateClosure(fn, fvs):
	#raise Exception("fn: %r, fvs: %r" % (fn, fvs))
	return Closure(fn, fvs)

def CreateObject(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)
	
	return BigObj(pobj.value.value())

def HasAttr(pobj, attr):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	return hasattr(pobj.value.value, attr)

def GetFunction(pobj):
	assert_pyobj(pobj)
	assert_big(pobj.value)

	if pobj.value.value.__class__ in set([BoundMethod, UnboundMethod]):
		return pobj.value.value.closure

	#else this is a closure
	return pobj.value

def add(bigobj1, bigobj2):
	return BigObj(bigobj1.value + bigobj2.value)

def equal(bigobj1, bigobj2):
	return bigobj1.value == bigobj2.value 

def Error(s):
	raise Exception(s)

def Print(pobj):
	assert_pyobj(pobj)
	print pobj.to_str()