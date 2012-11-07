class C:
    def __init__(self):
        self.x = 42

    def foo(self):
        return self.x

o = C()
print o.foo()
