def dbd(b,s):
    if not b%s:
        return s
    return dbd(s, b%s)