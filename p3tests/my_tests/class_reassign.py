x = 1

class C:
  x = 2
  def m(y):
    return x

o = C()

class C:
  def m(self):
    return self.x
  n = C.m
  def __init__(self):
    self.x = 3

print C.n(o)
