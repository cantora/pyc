def f(x):
    y = 4
    return lambda z: x + y + z

f1 = f(1)
print f1(3)
