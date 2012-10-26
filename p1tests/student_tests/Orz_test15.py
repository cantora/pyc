l1 = [1, 2, 3]
l2 = [9, 8, 7]
l3 = [3]

(l1 if input() else l2)[input()] = input()
print l1
print l2
print l3

list = []
l = list
print list is list
print l is list
print list is l

print [1] is [1] + []
print [1] != [1] + []

print not []
print not [1]
print not [] + []

list = [9, 8 , 7]
list[True]=True
list[False]=False
list[not False and True]=False
print list
