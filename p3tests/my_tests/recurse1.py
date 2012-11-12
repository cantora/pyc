x = input()

def f(y, z):
  if y == x:
    return z

  return f(y+1,  z + 3)

print f(1, 4)
