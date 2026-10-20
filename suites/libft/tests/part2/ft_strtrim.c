#include "libft_test.h"

static void	check(const char *s, const char *set, const char *want)
{
	char	*r = ft_strtrim(s, set);

	DT_ASSERT_NOT_NULL(r);
	DT_EXPECT_EQ_STR(r, want);
	free(r);
}

DT_TEST(ft_strtrim, basic, "Trims set characters from both ends")
{
	check("  \t hello world \n ", " \t\n", "hello world");
}

DT_TEST(ft_strtrim, inner_kept, "Characters in the middle are kept")
{
	check("xxhexllox", "x", "hexllo");
}

DT_TEST(ft_strtrim, everything, "Everything trimmed gives an empty string")
{
	check("aaaa", "a", "");
}

DT_TEST(ft_strtrim, empty_set, "Empty set returns a copy")
{
	check(" abc ", "", " abc ");
}

DT_TEST(ft_strtrim, malloc_fail, "Returns NULL when malloc fails")
{
	dt_malloc_fail_all();
	DT_EXPECT_NULL(ft_strtrim(" ab ", " "));
}
