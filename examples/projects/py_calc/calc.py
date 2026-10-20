"""A tiny 'student' Python module with a few deliberate bugs."""


def add(a, b):
    return a + b


def mean(values):
    return sum(values) / len(values)          # bug: crashes on an empty list


def is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        if n > 100:
            continue                          # bug: infinite loop for big numbers
        i += 1
    return True


def shout(text):
    print(text.upper() + "!")
