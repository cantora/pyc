def add(x, y):
    return x + y

def fold(f, l, acc, i, n):
    return fold(f, l, f(acc, l[i]), i + 1, n) if i != n else acc

print fold(add, [1,2,3], 0, 0, 3)
print fold(add, [4,5,6], 0, 0, 3)

l = [input(), input(), input()]

print fold(add, l, 0, 0, 3)
