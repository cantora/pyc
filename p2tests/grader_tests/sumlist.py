def sum(l, i, n):
    return l[i] + sum(l, i + 1, n) if i != n else 0

print sum([1,2,3], 0, 3)
print sum([4,5,6], 0, 3)
