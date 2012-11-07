class C:
    def __init__(self, a):
        self.a = a
class D:
    def __init__(self, a):
        self.a = a

x = C(1)
y = D(2)

def swap(x,y):
    temp = x
    x = y
    y = temp

swap(x, y)

print x.a
print y.a
