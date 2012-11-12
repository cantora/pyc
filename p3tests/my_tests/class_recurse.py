x = 0
class A:
  x = 1
  class A:
    x = 2
    class A:
      x = 3
      class A:
        x = 4
        class A:
          print x
          x = 10

print A.A.x
print A.A.A.A.A.x + input()

