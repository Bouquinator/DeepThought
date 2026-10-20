#include "libft_test.h"

DT_TEST(ft_bzero, basic, "Zeroes exactly n bytes")
{
	char	a[10];
	char	b[10];

	memset(a, 'q', 10);
	memset(b, 'q', 10);
	ft_bzero(a, 5);
	memset(b, 0, 5);
	DT_EXPECT_EQ_MEM(a, b, 10);
}

DT_TEST(ft_bzero, zero_length, "n = 0 changes nothing")
{
	char	a[4] = "abc";

	ft_bzero(a, 0);
	DT_EXPECT_EQ_STR(a, "abc");
}
