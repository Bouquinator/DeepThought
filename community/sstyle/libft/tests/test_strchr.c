#include "sstyle.h"
#include <string.h>

static void	t_strchr(const char *label, const char *s, int c)
{
	const char	*ref;
	const char	*got;

	ref = strchr(s, c);
	got = ft_strchr(s, c);
	if (ref == NULL && got == NULL)
	{
	}
	else if (ref == NULL || got == NULL)
	{
		DT_FAILF("%s: expected %s, got %s", label, ref ? "ptr" : "NULL", got ? "ptr" : "NULL");
	}
	else if ((ref - s) == (got - s))
	{
	}
	else
	{
		DT_FAILF("%s: expected offset %ld, got %ld", label, (long)(ref - s), (long)(got - s));
	}
}

DT_TEST(ft_strchr, first_l_in_hello, "first 'l' in \"Hello\"")
{
	t_strchr("first 'l' in \"Hello\"", "Hello", 'l');
}

DT_TEST(ft_strchr, first_h_at_offset_0, "first 'H' at offset 0")
{
	t_strchr("first 'H' at offset 0", "Hello", 'H');
}

DT_TEST(ft_strchr, char_at_end_of_string, "char at end of string")
{
	t_strchr("char at end of string", "abcdef", 'f');
}

DT_TEST(ft_strchr, not_found, "not found")
{
	t_strchr("not found", "Hello", 'x');
}

DT_TEST(ft_strchr, find_nul_end_pointer, "find NUL (end pointer)")
{
	t_strchr("find NUL (end pointer)", "Hello", '\0');
}

DT_TEST(ft_strchr, empty_string_find_nul, "empty string, find NUL")
{
	t_strchr("empty string, find NUL", "", '\0');
}

DT_TEST(ft_strchr, c_gt_255, "c > 255: masked to unsigned char — (uchar)('l' + 256) == 'l'")
{
	t_strchr("c=l+256 masked to 'l'", "Hello", 'l' + 256);
}
