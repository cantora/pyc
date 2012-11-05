class A:
    0

B = A

class A:
    A.x = 1


print B.x
