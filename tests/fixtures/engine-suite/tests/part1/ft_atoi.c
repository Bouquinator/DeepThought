#include "libft_test.h"

static void	check(const char *s)
{
	dt_input("\"%s\"", s);
	DT_EXPECT_EQ_INT(ft_atoi(s), atoi(s));
}

DT_TEST(ft_atoi, basic, "Positive and negative numbers")
{
	check("42");
	check("-42");
	check("0");
}

DT_TEST(ft_atoi, whitespace, "Leading whitespace (\\t\\n\\v\\f\\r and space) is skipped")
{
	check(" \t\n\v\f\r 123");
}

DT_TEST(ft_atoi, one_sign, "A single + or - is accepted")
{
	check("+7");
	check("-7");
}

DT_TEST(ft_atoi, two_signs, "Two signs give 0")
{
	check("+-7");
	check("--7");
}

DT_TEST(ft_atoi, trailing, "Stops at the first non-digit")
{
	check("12ab34");
	check("1 2");
}

DT_TEST(ft_atoi, limits, "INT_MAX and INT_MIN")
{
	check("2147483647");
	check("-2147483648");
}

DT_TEST(ft_atoi, garbage, "Non-numeric input gives 0")
{
	check("abc");
	check("");
	check("- 1");
}
