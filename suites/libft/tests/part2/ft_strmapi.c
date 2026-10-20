#include "libft_test.h"

static char	up_odd(unsigned int i, char c)
{
	return ((i % 2) ? (char)toupper(c) : c);
}

DT_TEST(ft_strmapi, basic, "Applies f(index, char) to every character")
{
	char	*r = ft_strmapi("abcdef", up_odd);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, "aBcDeF");
	free(r);
}

DT_TEST(ft_strmapi, empty, "Empty string")
{
	char	*r = ft_strmapi("", up_odd);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, "");
	free(r);
}

DT_TEST(ft_strmapi, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_strmapi("abc", up_odd));
}
