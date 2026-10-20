/*
** Example tests. Every DT_TEST is one test, run in its own process:
** a crash, an infinite loop or a leak only affects that test.
**
**   DT_TEST(group, name, "description shown in the UI") { ... }
**
** Checks (EXPECT continues on failure, ASSERT stops the test):
**   DT_EXPECT(cond)                 DT_EXPECT_EQ_INT(actual, expected)
**   DT_EXPECT_EQ_SIZE(a, e)         DT_EXPECT_EQ_STR(a, e)     (NULL-safe)
**   DT_EXPECT_EQ_MEM(a, e, n)       DT_EXPECT_EQ_PTR(a, e)
**   DT_EXPECT_NULL(p)               DT_EXPECT_NOT_NULL(p)
**   DT_EXPECT_SAME_SIGN(a, e)       (for strcmp-like results)
**   DT_COMPARE_OUTPUT(ft_call, ref_call)   same stdout bytes + return value
**   DT_EXPECT_ALLOC_SIZE(ptr, n)    malloc'd exactly n bytes
**
** Tools: dt_malloc_fail_at(n), dt_malloc_fail_all(), dt_leaks_ignore(),
**        dt_input("fmt", ...)  <- describe the input: shown with every failure
**        dt_fixture("file"), dt_note("fmt", ...),
**        dt_skip("reason"), DT_CAPTURE_FD(fd, cap, code)
*/
#include "dt.h"
/* #include "libft.h"   <- include the student's header here */

static char	*my_strdup(const char *s)
{
	size_t	n = strlen(s) + 1;
	char	*d = malloc(n);

	if (!d)
		return (NULL);
	return (memcpy(d, s, n));
}

DT_TEST(example, equal_strings, "Compares two strings (replace with a student function)")
{
	char	*copy;

	dt_input("\"42 school\"");
	copy = my_strdup("42 school");

	DT_ASSERT_NOT_NULL(copy);
	DT_EXPECT_EQ_STR(copy, "42 school");
	DT_EXPECT_ALLOC_SIZE(copy, 10);
	free(copy);
}

DT_TEST(example, malloc_failure, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(my_strdup("abc"));
}

DT_TEST(example, output, "Checks what a function writes on stdout")
{
	t_dt_capture	out;

	DT_CAPTURE_STDOUT(out, write(1, "hello\n", 6));
	dt_check_bytes(out.data, out.len, "hello\n", 6, 0, "output", __FILE__, __LINE__);
	dt_capture_free(&out);
}
