a = 0
b = 1
n = 10

for i in range(1, n):
    c = a + b
    a = b
    b = c

print(c)

















# DEPRECATED:
#
# def fib(n):
#     a = 0
#     b = 1

#     if n < 2:
#         return n

#     for i in range(1, n):
#         c = a + b
#         a = b
#         b = c

#     return c

# print(fib(55))