class C:
    def __init__(self, a):
        self.a = a
class D:
    def __init__(self, a):
        self.a = a

x = C(1)
y = D(2)

def swap(x,y):
    temp = x.a
    x.a  = y.a
    y.a = temp

swap(x, y)

print x.a
print y.a
