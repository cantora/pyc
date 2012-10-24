def even(x):
    return True if x == 0 else odd(x + -1)

def odd(x):
    return True if x == 1 else even(x + -1)

print even(8)
