#include "sstyle.h"
#include <stdlib.h>
#include <string.h>

static void	free_split(char **arr)
{
	int	i;

	if (!arr)
		return ;
	i = 0;
	while (arr[i])
		free(arr[i++]);
	free(arr);
}

static void	check_split(const char *label,
	char **got, const char **expected, int expected_count)
{
	int	i;

	if (!got)
	{
		DT_FAILF("%s → got NULL array", label);
		return ;
	}
	i = 0;
	while (i < expected_count)
	{
		if (!got[i])
		{
			DT_FAILF("%s[%d]: expected \"%s\", got NULL", label, i, expected[i]);
			free_split(got);
			return ;
		}
		if (!(strcmp(got[i], expected[i]) == 0))
		{
			DT_FAILF("%s[%d]: expected \"%s\", got \"%s\"", label, i, expected[i], got[i]);
		}
		i++;
	}
	/* NULL sentinel at end */
	if (!(got[expected_count] == NULL))
	{
		DT_FAILF("%s: missing NULL terminator", label);
	}
	free_split(got);
}

static void	check_split_empty(const char *label, char **got)
{
	if (got && got[0] == NULL)
	{
		free(got);
	}
	else
	{
		DT_FAILF("%s → expected empty array", label);
		free_split(got);
	}
}

DT_TEST(ft_split, empty_string_to_empty_array_with, "empty string → empty array with just NULL")
{
	check_split_empty("split(\"\",' ')", ft_split("", ' '));
}

DT_TEST(ft_split, all_separators_to_empty_array, "all separators → empty array")
{
	check_split_empty("split(\"   \",' ')", ft_split("   ", ' '));
}

DT_TEST(ft_split, single_word_no_sep, "single word, no sep")
{
	const char	*exp1[] = {"hello"};

	check_split("split(\"hello\",' ')", ft_split("hello", ' '), exp1, 1);
}

DT_TEST(ft_split, non_space_separator, "non-space separator")
{
	const char	*exp_abc[] = {"a", "b", "c"};

	check_split("split(\"a:b:c\",':')", ft_split("a:b:c", ':'), exp_abc, 3);
}

DT_TEST(ft_split, leading_separator, "leading separator")
{
	const char	*exp2[] = {"one", "two"};

	check_split("split(\" one two\",' ')", ft_split(" one two", ' '), exp2, 2);
}

DT_TEST(ft_split, trailing_separator, "trailing separator")
{
	const char	*exp2[] = {"one", "two"};

	check_split("split(\"one two \",' ')", ft_split("one two ", ' '), exp2, 2);
}

DT_TEST(ft_split, multiple_consecutive_separators, "multiple consecutive separators")
{
	const char	*exp2[] = {"one", "two"};

	check_split("split(\"one   two\",' ')", ft_split("one   two", ' '), exp2, 2);
}

DT_TEST(ft_split, nul_as_separator, "'\\0' as separator")
{
	/*
	** '\0' as separator: '\0' is the string terminator, so it is never
	** encountered inside a valid C string. No separator is found and the
	** whole string is returned as a single word.
	** Buggy inner scan loops written as:
	**   while (s[i] != c)          <- no null-guard
	** exit at the NUL terminator (since '\0' == c), but then the outer
	** loop increments i past the end of the string and reads garbage
	** memory, causing a segfault.
	** The correct form is: while (s[i] && s[i] != c)
	*/
	{
		const char	*exp_nul[] = {"hello"};

		check_split("split(\"hello\",'\\0') nul-sep → single word",
			ft_split("hello", '\0'), exp_nul, 1);
	}
	{
		const char	*exp_nul2[] = {"a b c"};

		check_split("split(\"a b c\",'\\0') nul-sep → single word",
			ft_split("a b c", '\0'), exp_nul2, 1);
	}
	check_split_empty("split(\"\", '\\0') nul-sep", ft_split("", '\0'));
}

DT_TEST(ft_split, null_string_to_must_return_null, "NULL string → must return NULL without crashing")
{
	{
		char	**r;

		r = ft_split(NULL, ' ');
		if (!(r == NULL))
		{
			DT_FAILF("split(NULL,' ') → expected NULL");
			free_split(r);
		}
	}
}
