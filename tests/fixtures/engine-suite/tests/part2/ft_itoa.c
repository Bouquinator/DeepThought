#include "libft_test.h"

static void	check(int n, const char *want)
{
	char	*r;

	dt_input("%d", n);
	r = ft_itoa(n);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, want);
	free(r);
}

DT_TEST(ft_itoa, basic, "Positive, negative and zero")
{
	check(42, "42");
	check(-42, "-42");
	check(0, "0");
}

DT_TEST(ft_itoa, limits, "INT_MAX and INT_MIN")
{
	check(INT_MAX, "2147483647");
	check(INT_MIN, "-2147483648");
}

DT_TEST(ft_itoa, powers, "Powers of ten")
{
	check(10, "10");
	check(-1000, "-1000");
}

DT_TEST(ft_itoa, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_all();
	DT_EXPECT_NULL(ft_itoa(123));
}
