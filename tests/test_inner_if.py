x = input("Enter number: ")

value = x % 2
if value == 0:
    if x > 7:
        print("Number is greater than 7 and even")
    elif x > 6:
        print("Number is greater than 6 and even")
    elif x > 5:
        print("Number is greater than 5 and even")
    else:
        print("Number is even")
else:
    y = 100
    value = y % 2
    if value != 0:
        print(value)
    y -= 1
