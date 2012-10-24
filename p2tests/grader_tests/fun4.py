
# L = {y,x,f}

x = 1
y = 2

def f(y):          # H = {x,y}, L={z,g}, P={y}, F = {y}
    z = x + y
    def g(w):      # H = {x,y}, L={}, P={}
        v = w + y
        return v
    return g

print (f(3))(4)
        
