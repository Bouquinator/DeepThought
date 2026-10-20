#include "libft_test.h"

static void	check(const char *s, unsigned int start, size_t len, const char *want)
{
	char	*r = ft_substr(s, start, len);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, want);
	free(r);
}

DT_TEST(ft_substr, basic, "Extracts a substring")
{
	check("lorem ipsum dolor", 6, 5, "ipsum");
}

DT_TEST(ft_substr, len_too_big, "len larger than the rest of the string")
{
	check("lorem ipsum", 6, 100, "ipsum");
}

DT_TEST(ft_substr, start_too_big, "start beyond the end gives an empty string")
{
	check("lorem", 10, 3, "");
}

DT_TEST(ft_substr, minimal_alloc, "Allocates only what is needed (len clamped)")
{
	char	*r = ft_substr("hello", 1, 1000);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_ALLOC_SIZE(r, 5);
	free(r);
}

DT_TEST(ft_substr, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_substr("hello", 1, 2));
}
