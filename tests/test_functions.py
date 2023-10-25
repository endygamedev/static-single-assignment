a = 10
b = 20

def add(x, y):
    total = x + y
    return total

def function2(z, v):
    z = add(z, v)
    if z > 10:
        print("Sum greater than 10")
    else:
        print("Sum less than 10")

print(function2(a, b))
