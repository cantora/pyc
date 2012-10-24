def mult(x, y):
    return 0 if x == 0 else (y if x == 1 else y + mult(x + -1, y))

def less_helper(x, y, xp, yp):
    return True if xp == y else (False if yp == x else less_helper(x, y, xp + 1, yp + 1))

def less(x, y):
    return less_helper(x, y, x + 1, y)

def div(x, y):
    return 0 if less(x, y) else 1 + div(x + -y, y)

def derivative(f):
    epsilon = 1
    return lambda x: div(f(mult(10,x)+epsilon) + -f(mult(10,x)), mult(epsilon, 10))


def square(x):
    return mult(x, x)

ds = derivative(square)

print ds(10)
 
