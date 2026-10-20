#include "libft_test.h"

static void	check(const char *src, size_t size)
{
	char	a[32];
	char	b[32];

	memset(a, 'Z', sizeof(a));
	memset(b, 'Z', sizeof(b));
	DT_EXPECT_EQ_SIZE(ft_strlcpy(a, src, size), ref_strlcpy(b, src, size));
	DT_EXPECT_EQ_MEM(a, b, sizeof(a));
}

DT_TEST(ft_strlcpy, fits, "Source fits: full copy, returns strlen(src)")
{
	check("hello", 20);
}

DT_TEST(ft_strlcpy, truncates, "Source too long: copies size-1 chars and NUL-terminates")
{
	check("hello world", 6);
}

DT_TEST(ft_strlcpy, size_zero, "size = 0: writes nothing, returns strlen(src)")
{
	check("hello", 0);
}

DT_TEST(ft_strlcpy, size_one, "size = 1: writes only the NUL")
{
	check("hello", 1);
}

DT_TEST(ft_strlcpy, empty_src, "Empty source")
{
	check("", 10);
}
