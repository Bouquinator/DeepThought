from dtharness import expect_eq, expect_output, expect_raises, given, test

import calc  # the student's module (their project folder is on sys.path)


@test("add() adds integers and floats")
def add_numbers():
    expect_eq(calc.add(2, 3), 5)
    expect_eq(calc.add(0.5, 0.25), 0.75)


@test("mean() of a list")
def mean_basic():
    expect_eq(calc.mean([1, 2, 3, 4]), 2.5)


@test("mean() of an empty list raises ValueError")
def mean_empty():
    given([])
    expect_raises(ValueError, calc.mean, [])


@test("is_prime() on small numbers")
def primes():
    for n, want in [(2, True), (3, True), (9, False), (13, True), (1, False)]:
        given(n=n)
        expect_eq(calc.is_prime(n), want, f"is_prime({n})")


@test("is_prime() terminates on bigger numbers")
def big_number():
    given(101)
    expect_eq(calc.is_prime(101), True)


@test("percent() formats a ratio")
def percent():
    expect_eq(calc.percent(1, 4), "25%")


@test("shout() prints the text in upper case with '!'")
def shout():
    expect_output(calc.shout, "HELLO 42!\n", "hello 42")
