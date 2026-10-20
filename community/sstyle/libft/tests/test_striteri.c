#include "sstyle.h"
#include <string.h>

/* ---- helper state ---- */
static unsigned int	g_indices[32];
static int			g_call_count;

static void	record(unsigned int i, char *c)
{
	if (g_call_count < 32)
		g_indices[g_call_count] = i;
	g_call_count++;
	(void)c;
}

static void	to_upper_cb(unsigned int i, char *c)
{
	(void)i;
	if (*c >= 'a' && *c <= 'z')
		*c -= 32;
}

DT_TEST(ft_striteri, in_place_edit, "in-place edit: only letters should change")
{
	char		buf[64];

	strcpy(buf, "a1b2c3");
	ft_striteri(buf, to_upper_cb);
	DT_CHECK_STR("striteri mixed(\"a1b2c3\")", buf, "A1B2C3");
}

DT_TEST(ft_striteri, all_indices_0_based, "all indices 0-based: 0,1,2,3,4 for \"hello\"")
{
	char		buf[64];

	strcpy(buf, "hello");
	g_call_count = 0;
	ft_striteri(buf, record);
	if (g_call_count == 5)
	{
		int	ok;
		int	j;

		ok = 1;
		j = 0;
		while (j < 5)
		{
			if (g_indices[j] != (unsigned int)j)
			{
				ok = 0;
				break ;
			}
			j++;
		}
		if (!(ok))
		{
			DT_FAILF("striteri: indices out of order");
		}
	}
	else
	{
		DT_FAILF("striteri: expected 5 calls, got %d", g_call_count);
	}
}

DT_TEST(ft_striteri, null_empty_string_must_not_crash, "NULL / empty string — must not crash")
{
	char		buf[64];

	ft_striteri(NULL, to_upper_cb);

	strcpy(buf, "");
	ft_striteri(buf, to_upper_cb);
	DT_CHECK_STR("striteri(\"\") unchanged", buf, "");
}
