"""Example Python tests. The student's project folder is on sys.path,
so `import their_module` just works. Each test runs in its own process."""

from dtharness import capture_stdout, expect, expect_eq, expect_raises, given, test


# import ft_module   <- the student's module


@test("Compares two values (replace with a student function)")
def addition():
    given(1, 1)                       # shown with every failure below
    expect_eq(1 + 1, 2)


@test("Checks that an exception is raised")
def raises():
    expect_raises(ZeroDivisionError, lambda: 1 / 0)


@test("Checks what is printed")
def printed():
    with capture_stdout() as out:
        print("hello 42")
    expect_eq(out.text, "hello 42\n")
    expect("42" in out.text, "the output mentions 42")
