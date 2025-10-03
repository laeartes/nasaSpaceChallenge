def dbd(b,s):
    if not b%s:
        return s
    return dbd(s, b%s)


print(dbd(12, 15))