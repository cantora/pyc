print [] is {}
print (not []) is (not {})
print (not []) + (not {}) + 2
print - (not [])

print ----(not not not not not {})
{1:2}
{2:1}
print {1:2} != {2:1}
print {1:2, 2:1, 1:3} != {1:3, 2:1, 1:3}

print ({} if input() else []) + [2]
print {input(): input(), input(): input(), 4:2} == {2: 1, 4:2}
print 1 if not {input(): input()} else True

print {} and {}+1
print []

print {}
print not {}
print {1:2}
print not {1:3}
print {1:2} or {1:3}
print {1:2} and {1:3}
print {1:2, 2:3} == {2:3, 1:2}
print {1:2, 2:3} is {2:3, 1:2}
print {} is {}
d = {1: 2}
d[True] = d
print d is d[1]
