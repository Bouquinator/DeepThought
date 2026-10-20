#include "libft_test.h"

DT_TEST(ft_strjoin, basic, "Concatenates two strings")
{
	char	*r = ft_strjoin("42 ", "school");

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, "42 school");
	DT_EXPECT_ALLOC_SIZE(r, 10);
	free(r);
}

DT_TEST(ft_strjoin, empty, "Empty strings on either side")
{
	char	*a = ft_strjoin("", "abc");
	char	*b = ft_strjoin("abc", "");
	char	*c = ft_strjoin("", "");

	DT_EXPECT_EQ_STR(a, "abc");
	DT_EXPECT_EQ_STR(b, "abc");
	DT_EXPECT_EQ_STR(c, "");
	free(a);
	free(b);
	free(c);
}

DT_TEST(ft_strjoin, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_strjoin("a", "b"));
}
