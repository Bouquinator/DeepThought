#include "sstyle.h"
#include <string.h>

/* BSD strnstr is not always in standard headers; provide a reference impl */
static char	*ref_strnstr(const char *big, const char *little, size_t len)
{
	size_t	llen;
	size_t	i;

	if (!*little)
		return ((char *)big);
	llen = strlen(little);
	i = 0;
	while (i + llen <= len)
	{
		if (big[i] == '\0')
			return (NULL);
		if (strncmp(big + i, little, llen) == 0)
			return ((char *)(big + i));
		i++;
	}
	return (NULL);
}

static void	t_strnstr(const char *label,
	const char *big, const char *little, size_t len)
{
	const char	*ref;
	const char	*got;

	ref = ref_strnstr(big, little, len);
	got = ft_strnstr(big, little, len);
	if (ref == NULL && got == NULL)
	{
	}
	else if (ref == NULL || got == NULL)
	{
		DT_FAILF("%s: expected %s, got %s", label, ref ? "ptr" : "NULL", got ? "ptr" : "NULL");
	}
	else if ((ref - big) == (got - big))
	{
	}
	else
	{
		DT_FAILF("%s: expected offset %ld, got %ld", label, (long)(ref - big), (long)(got - big));
	}
}

DT_TEST(ft_strnstr, found_at_start, "found at start")
{
	t_strnstr("found at start", "hello world", "hello", 11);
}

DT_TEST(ft_strnstr, found_in_middle, "found in middle")
{
	t_strnstr("found in middle", "hello world", "world", 11);
}

DT_TEST(ft_strnstr, not_found, "not found")
{
	t_strnstr("not found", "hello world", "xyz", 11);
}

DT_TEST(ft_strnstr, empty_needle_to_big, "empty needle → big")
{
	t_strnstr("empty needle → big", "hello", "", 5);
}

DT_TEST(ft_strnstr, len_0_to_null, "len=0 → NULL")
{
	t_strnstr("len=0 → NULL", "hello", "hello", 0);
}

DT_TEST(ft_strnstr, needle_found_exactly_at_the_boundary, "needle found exactly at the boundary of len")
{
	t_strnstr("needle at exact end of len", "abcdef", "ef", 6);
}

DT_TEST(ft_strnstr, needle_crosses_len_by_one_byte, "needle crosses len by one byte: not enough room")
{
	t_strnstr("needle crosses len", "abcdef", "ef", 5);
}

DT_TEST(ft_strnstr, needle_longer_than_haystack_but_within, "needle longer than haystack but within len")
{
	t_strnstr("needle longer than haystack", "hi", "hello", 5);
}
