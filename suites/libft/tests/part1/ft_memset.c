#include "libft_test.h"

DT_TEST(ft_memset, basic, "Fills n bytes and returns the destination")
{
	char	a[20];
	char	b[20];

	memset(a, 'z', 20);
	memset(b, 'z', 20);
	DT_EXPECT_EQ_PTR(ft_memset(a, 'A', 10), a);
	memset(b, 'A', 10);
	DT_EXPECT_EQ_MEM(a, b, 20);
}

DT_TEST(ft_memset, int_conversion, "The int value is converted to unsigned char (c = 300)")
{
	unsigned char	a[8] = {0};
	unsigned char	b[8] = {0};

	ft_memset(a, 300, 8);
	memset(b, 300, 8);
	DT_EXPECT_EQ_MEM(a, b, 8);
}

DT_TEST(ft_memset, zero_length, "n = 0 changes nothing")
{
	char	a[4] = "abc";

	ft_memset(a, 'x', 0);
	DT_EXPECT_EQ_STR(a, "abc");
}
