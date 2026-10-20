#include "libft_test.h"

static void	check(const char *s, char c, const char **want)
{
	char	**r;
	size_t	i = 0;

	dt_input("ft_split(\"%s\", '%c')", s, c);
	r = ft_split(s, c);

	DT_ASSERT_NOT_NULL(r);
	while (want[i])
	{
		if (!DT_EXPECT_EQ_STR(r[i], want[i]))
			break ;
		i++;
	}
	if (want[i] == NULL)
		DT_EXPECT_NULL(r[i]);
	free_split(r);
}

DT_TEST(ft_split, basic, "Splits on a separator")
{
	const char	*want[] = {"lorem", "ipsum", "dolor", NULL};

	check("lorem ipsum dolor", ' ', want);
}

DT_TEST(ft_split, repeated_separators, "Consecutive / leading / trailing separators produce no empty words")
{
	const char	*want[] = {"a", "b", "c", NULL};

	check(",,a,,,b,c,,", ',', want);
}

DT_TEST(ft_split, empty_string, "Empty string gives an array with only NULL")
{
	const char	*want[] = {NULL};

	check("", ' ', want);
}

DT_TEST(ft_split, only_separators, "Only separators gives an array with only NULL")
{
	const char	*want[] = {NULL};

	check("     ", ' ', want);
}

DT_TEST(ft_split, no_separator, "No separator: one word")
{
	const char	*want[] = {"hello", NULL};

	check("hello", ' ', want);
}

DT_TEST(ft_split, nul_separator, "c = '\\0': the whole string is one word")
{
	const char	*want[] = {"a b c", NULL};

	check("a b c", '\0', want);
}

DT_TEST(ft_split, malloc_fail_first, "First malloc fails: returns NULL")
{
	dt_malloc_fail_at(1);
	DT_EXPECT_NULL(ft_split("a b c", ' '));
}

DT_TEST(ft_split, malloc_fail_middle, "A malloc fails midway: returns NULL and frees everything (no leak)")
{
	dt_malloc_fail_at(3);
	DT_EXPECT_NULL(ft_split("a b c d", ' '));
}
