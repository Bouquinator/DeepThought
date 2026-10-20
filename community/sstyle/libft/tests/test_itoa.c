#include "sstyle.h"
#include <stdlib.h>

static void	t_itoa(const char *label, int n, const char *expected)
{
	char	*r;

	r = ft_itoa(n);
	DT_CHECK_STR(label, r, expected);
	free(r);
}

DT_TEST(ft_itoa, itoa_0, "itoa(0)")
{
	t_itoa("itoa(0)", 0, "0");
}

DT_TEST(ft_itoa, itoa_9, "itoa(9)")
{
	t_itoa("itoa(9)", 9, "9");
}

DT_TEST(ft_itoa, itoa_minus_9, "itoa(-9)")
{
	t_itoa("itoa(-9)", -9, "-9");
}

DT_TEST(ft_itoa, itoa_10, "itoa(10)")
{
	/* digit-count transitions */
	t_itoa("itoa(10)", 10, "10");
}

DT_TEST(ft_itoa, itoa_minus_10, "itoa(-10)")
{
	/* digit-count transitions */
	t_itoa("itoa(-10)", -10, "-10");
}

DT_TEST(ft_itoa, itoa_1000, "itoa(1000)")
{
	/* digit-count transitions */
	t_itoa("itoa(1000)", 1000, "1000");
}

DT_TEST(ft_itoa, itoa_2147483647, "itoa(2147483647)")
{
	/* digit-count transitions */
	t_itoa("itoa(2147483647)", 2147483647, "2147483647");
}

DT_TEST(ft_itoa, int_min_tricky, "INT_MIN — tricky: abs overflows if done naively")
{
	t_itoa("itoa(-2147483648)", -2147483647 - 1, "-2147483648");
}
