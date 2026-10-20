#include "libft_test.h"

DT_TEST(ft_strdup, basic, "Returns a new copy")
{
	const char	*s = "duplicate me";
	char		*d = ft_strdup(s);

	DT_ASSERT_NOT_NULL(d);
	DT_EXPECT_EQ_STR(d, s);
	DT_EXPECT(d != s);
	DT_EXPECT_ALLOC_SIZE(d, strlen(s) + 1);
	free(d);
}

DT_TEST(ft_strdup, empty, "Empty string")
{
	char	*d = ft_strdup("");

	DT_ASSERT_NOT_NULL(d);
	DT_EXPECT_EQ_STR(d, "");
	free(d);
}

DT_TEST(ft_strdup, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_strdup("abc"));
}
