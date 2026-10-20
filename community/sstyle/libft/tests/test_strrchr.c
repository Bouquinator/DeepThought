#include "sstyle.h"
#include <string.h>

static void	t_strrchr(const char *label, const char *s, int c)
{
	const char	*ref;
	const char	*got;

	ref = strrchr(s, c);
	got = ft_strrchr(s, c);
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

DT_TEST(ft_strrchr, last_l_in_hello_world, "last 'l' in \"Hello, World!\"")
{
	t_strrchr("last 'l' in \"Hello, World!\"", "Hello, World!", 'l');
}

DT_TEST(ft_strrchr, only_occurrence_at_pos_0, "only occurrence at pos 0")
{
	t_strrchr("only occurrence at pos 0", "Hello", 'H');
}

DT_TEST(ft_strrchr, only_at_last_pos, "only at last pos")
{
	t_strrchr("only at last pos", "xxxb", 'b');
}

DT_TEST(ft_strrchr, not_found, "not found")
{
	t_strrchr("not found", "Hello", 'x');
}

DT_TEST(ft_strrchr, find_nul, "find NUL")
{
	t_strrchr("find NUL", "Hello", '\0');
}

DT_TEST(ft_strrchr, empty_string, "empty string")
{
	t_strrchr("empty string", "", 'a');
}
