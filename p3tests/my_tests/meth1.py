def f(a,b):
  return input() + 100 + b

class A:
  def f(self, x):
    return input() + 1 + x

print f(1,2)

o = A()
print o.f(8)

o.f = f
print o.f(7,345)

