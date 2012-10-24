def sum(n):
    return n + sum(n + -1) if n else 0

print sum(1)
