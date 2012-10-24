def mult(x, y):
    return 0 if x == 0 else (y if x == 1 else y + mult(x + -1, y))

print mult(3, 5)
