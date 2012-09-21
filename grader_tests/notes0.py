z = 4
# live {}
w = 0
# live {w}
z = 1
# live {w,z}
x = w
# live {x,w,z}
x = x + z
# live {x,w}
y = w
# live {x,y}
y = y + x
# live {x,y}
w = y
           # live {w,x}
w = w + x
