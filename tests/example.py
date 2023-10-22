def function(x, y, z):
    while z > 10:
        while x > 20:
            x = x + 1
            if x > 100:
                break
        if x > 10:
            return y
    return x