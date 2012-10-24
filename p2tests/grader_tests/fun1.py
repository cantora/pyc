def mult(x, y):
    return 0 if x == 0 else (y if x == 1 else y + mult(x + -1, y))

def fact(x):
    return 1 if x == 1 else mult(x, fact(x + -1))

print fact(5)
