
i = 50

class A:
  i = 0
  x = input()
  while i != x:
    class B:
      b = [i]
      i = i + 1
      
    i = i + 50
    print B().i
    print B().b[0]

  print i

print A.B.i
      