
x = input()

class C:
  print x
  x = 3
  print x

  def a(self):
    class D:
      print x
      x = 4
      print x

    return D.x

def b():
  class E:
    print x
    x = 5
    print x

  return E.x

print x
print C().a()
print b()
