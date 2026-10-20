#include "libft_test.h"

static void	check(const char *init, const char *src, size_t size)
{
	char	a[32];
	char	b[32];

	memset(a, 'Z', sizeof(a));
	memset(b, 'Z', sizeof(b));
	strcpy(a, init);
	strcpy(b, init);
	DT_EXPECT_EQ_SIZE(ft_strlcat(a, src, size), ref_strlcat(b, src, size));
	DT_EXPECT_EQ_MEM(a, b, sizeof(a));
}

DT_TEST(ft_strlcat, fits, "Enough room: appends everything")
{
	check("abc", "def", 20);
}

DT_TEST(ft_strlcat, truncates, "Not enough room: truncates and NUL-terminates")
{
	check("abc", "defghij", 6);
}

DT_TEST(ft_strlcat, size_smaller_than_dst, "size <= strlen(dst): returns size + strlen(src), dst unchanged")
{
	check("abcdef", "xyz", 3);
}

DT_TEST(ft_strlcat, size_zero, "size = 0")
{
	check("abc", "xyz", 0);
}

DT_TEST(ft_strlcat, exact_fit, "size == strlen(dst) + strlen(src) + 1")
{
	check("abc", "de", 6);
}
